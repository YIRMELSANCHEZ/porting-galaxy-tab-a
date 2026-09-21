# Bluetooth on gtexswifi (SM-T280) -- findings and resolution (V68 -> V73)

Final state (HW, 2026-09-20, V73): **Bluetooth working**. Adapter ON, MAC `00:45:DA:**:**:**`, `<redacted-bt-device>`
headphones paired and playing over A2DP (+HFP), persistent pairing in
`/data/misc/bluedroid/bt_config.conf`, WiFi coexisting on the same chip, `Bluetooth crashed 0 times`, no
BT wakelocks held (`/sys/power/wake_lock` only `gtex_power_wake`).

## Architecture (what you need to know to touch this)

- WiFi and BT are on the **same Marlin sc2331 combo chip** ("CP2"), a co-processor with its own firmware
  (`/system/etc/firmware/sc2331_fw.bin`). WiFi goes over SDIO; **BT HCI goes over UART `/dev/ttyS0`**.
- Two daemons from the 5.1 blob govern it:
  - `wcnd` (abstract socket `@wcnd`): CP2 state machine (STARTING/STARTED/ASSERT/STOPPED), loopcheck every
    5 s via `/proc/mdbg/loopcheck`, resets CP2 when it asserts. Powers CP2 only if BT or WiFi are open
    (`btwifi_state`).
  - `download` (socket `@external_wcn`): loads the firmware into CP2 via `/dev/download` when wcnd requests
    it.
- `libbt-vendor.so` (5.1 blob) on `BT_VND_OP_POWER_CTRL` sends `wcn BT-OPEN` to wcnd and **waits for a
  reply**; then it opens `/dev/ttyS0`, sends the pskey (`connectivity_configure.ini`) and waits for
  `Firmware Node: 5150`.
- The HIDL service is the generic `android.hardware.bluetooth@1.0-service` (hardware/interfaces) which
  loads `libbt-vendor.so` and bridges it to the A10 stack (`libbluetooth.so`, `com.android.bluetooth`).
- `/proc/bluetooth/sleep/` only has `btwrite` (no `proto`/`lpm`). There is no BT rfkill: power is via wcnd.

## The 7 chained causes

Each only appeared once the previous was solved. Chronological order:

### 1. Missing HIDL service (V68)
`hwservicemanager: Cannot find entry android.hardware.bluetooth@1.0::IBluetoothHci/default` ->
`hci_layer_android.cc Check failed: btHci != nullptr`. Fix: `android.hardware.bluetooth@1.0-service` in
`PRODUCT_PACKAGES` + VINTF entry. (Systemic port pattern: the blob exists, the HIDL service is missing.)

### 2. Unreadable bdaddr (V70, `apply-v70-bt-bdaddr-group.py`)
The service rc had `group bluetooth net_bt_stack`; the AID `net_bt_stack` **does not exist on A10**
(`host_init_verifier: Unable to decode GID`). Fix: numeric GID `3008`.

### 3. Crash in `vnd_load_conf` (V70, `apply-v70-bt-ini-filter.py`)
The stock `connectivity_configure.ini` has 169 keys; the blob only knows 32 and overflows its table when
parsing the unknown ones. Fix: ini filtered to the 32 keys (backup `.ini.stock`). WiFi does not use it.

### 4. UART inaccessible (V70, `apply-v70-bt-uart-wakelock.py`)
`userial vendor open: unable to open /dev/ttyS0`. `init.board.rc` did `chown bluetooth net_bt_stack
/dev/ttyS0` -> init cannot resolve the group -> the chown **fails entirely** and the node stays
`system:system`. Fix: `chown bluetooth bluetooth`. Also `wakelock` group for the service. **Here the chip
responded for the first time** (`Bluetooth Firmware Node: 5150 Date: 2016-12-16`, `OnFirmwareConfigured
result: 0`).

### 5. The chip sleeps after configuring the firmware (V71, `apply-v71-bt-lpm-off.py`)
`vendor_interface.cc` after the firmware does `BT_VND_OP_LPM_SET_MODE(ENABLE)` and arms a 1.5 s watchdog
that de-asserts `BT_WAKE`; with this blob the re-assert does not wake the chip. Fix: `LPM_DISABLE`, no
watchdog, `lpm_wake_deasserted=false`. Trade-off: slightly more power with BT on (verified it leaves no
kernel wakelocks held).

### 6. `wcnd` with no capabilities -> CP2 unrecoverable (V72, `apply-v72-wcnd-root.py`) -- **the big one**
Intermittent symptom: sometimes `start_cp2: get -1 bytes` (wcnd does not reply) -> `bt_hci
startup_timer_expired` (3 s) -> SIGABRT; sometimes hung sending the pskey. logcat WCND: `Error downing
interface: Operation not permitted`, `Error Wifi driver cannot unloaded in 20 seconds`, `reboot CP2 Fail
!`; dmesg: `set_marlin_wakeup: marlin chn 0 ack timeout` (chip dead; WiFi did not scan either).
`/proc/<wcnd>/status`: `Uid 1000, CapEff 0`.

Cause: `wcnd.rc` inherited from cm14 has `user system`, but the binary does **setuid+capset itself** (it
is designed to start as root and drop to system keeping `CAP_NET_ADMIN`; the rc comment says so and in the
stock `init.sc8830.rc` `user system` is commented out). Without caps it cannot reset CP2 after the first
assert. Live test relaunching it as root: `Uid 1000, CapEff 0x3020`, CP2 starts and recovers (`loopcheck
OK`, `CP2_STARTED`). Fix: remove `user system`; `net_bt_stack` -> `3008`.

Gotcha: restarting `wcnd` live loses `btwifi_state` and **powers off CP2** (breaks WiFi until reboot).

### 7. VSC `0xFD53` not supported -> `BLE_START_TIMEOUT` (V73, `apply-v73-bt-skip-offload-probe.py`)
With 1-6 the HCI startup is healthy. btsnoop (`persist.bluetooth.btsnoopdefaultmode full`):
```
TX 01 03 0c 00   RX 04 0e 04 01 03 0c 00            HCI Reset OK
TX 01 09 10 00   RX 04 0e 0a 01 09 10 00 e2 07 c9 da 45 00   Read BD_ADDR OK
... Local Version / Features / Ext Features p1 / Simple Pairing / LE Host Support: all OK ...
TX 01 53 fd 00   RX 04 0f 04 01 01 53 fd            <- VSC 0xFD53: Command STATUS 0x01 (Unknown HCI Command)
```
`system/bt/device/src/controller.cc` (LineageOS addition "read BLE offload features support") sends
`HCI_BLE_VENDOR_CAP_OCF` with `AWAIT_COMMAND` (a future that only resolves with a Command *Complete*). The
SPRD chip replies Command *Status* -> `hci_layer` ignores it -> `controller_module` does not start ->
`AdapterState: BLE_TURNING_ON : BLE_START_TIMEOUT` after 4 s. (The AOSP send of the same VSC via
`BTM_VendorSpecificCommand` does handle the Command Status; only the extra probe fails.) Fix: guard via
property `ro.bluetooth.skip_offload_probe=1` (device.mk) which leaves `ble_offload_features_supported=false`.

## Benign noise in logcat (do not chase)
- `Unhandled event type 0F` / `command status event with no matching command. opcode: 0x0000` (x10 at
  startup): the chip replies Command Status to pskey bytes; harmless.
- `uipo_userial_debug_enable open /sys/devices/70000000.uart/uart_conf failed: Permission denied`: debug.
- `ThreadRoutine unable to set SCHED_FIFO`: kernel 3.10 without ambient caps (known across the whole port).
- `bta_dm_pm_btm_status hci_status=36`: the peer rejects a sniff mode change; normal.

## Useful tools
- Enable BT via adb: `svc bluetooth enable` (`cmd bluetooth_manager` does not exist in this build).
- Snoop: `setprop persist.bluetooth.btsnoopdefaultmode full` -> `/data/misc/bluetooth/logs/btsnoop_hci.log`
  (btsnoop v1 format; applies on the next enable). **Leave it at `disabled`** when done.
- CP2 state: `logcat | grep WCND` (filter `clients\[`), `cat /proc/mdbg/loopcheck`, dmesg `SDIOTRAN`.
- wcnd caps: `grep CapEff /proc/$(pidof wcnd)/status` -> must be `3020`.
