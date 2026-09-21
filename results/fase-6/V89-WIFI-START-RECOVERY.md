# V89 -- SC2331/Marlin Wi-Fi boot recovery

Status: **OFFLINE PASS -- HARDWARE PENDING**
Date: 2026-09-21

## Hardware evidence motivating the change

In V87 the `finit_module(sprdwl)` retry avoids the early failure when SDIO is not yet ready, but a second
race appeared. Bluetooth and Wi-Fi initialize the shared Marlin/SC2331 coprocessor almost simultaneously.
The module does load and creates `wlan0`, but during the first scans the following were observed:

- `set_marlin_wakeup ... ack timeout` (`-110`);
- `WIFI_CMD_SET_SCAN ... rsp timeout`;
- `wlan_scan_timeout` and `wificond: Scan aborted`;
- `CMD_STA_START_FAILURE` (`155664`), after which Android leaves Wi-Fi disabled even though the preference
  is still on;
- several transient Bluetooth restarts during the same interval.

A late manual enable confirmed the recoverable behavior: the first scan failed again, the next found seven
networks, associated via WPA and got a DHCP address. This shows there is no missing firmware, module,
supplicant or credentials; what fails is the timing coordination of the combined chip during boot.

## Fix

V89 modifies `WifiController` to turn `CMD_STA_START_FAILURE` into a bounded recovery:

1. It only acts if the user keeps Wi-Fi enabled.
2. It tears down client mode through Android's normal path; it does not kill `wcnd` or restart Marlin.
3. It waits 15 seconds and restarts the full stack.
4. It allows up to six consecutive failures (an additional maximum window of 90 seconds).
5. The counter resets after 60 seconds with client mode stable or when the user does a real off/on cycle.
6. It exhausts the retries safely and returns to the standard behavior if the hardware has a permanent
   failure.

The V87 `finit_module` retry is kept for the earlier `EPERM/SDIO not ready` case. V89 is cumulative over
V88, so it also includes the coherent SwiftAngle EGL scaling.

## Artifact and checks

Package:

`sm-t280-phase6/packages/SM-T280-android10-wifi-recovery-angle-PHASE6-v89-DO-NOT-FLASH.tar.md5`

Package SHA-256:

`163e79dc3cb032f2c35cea6bc35f968cce715adc5992d4ed3eee07603bedf426`

Results:

- `V89_STATIC_VERIFY_PASS`
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- `V89_BUILD_AND_PACKAGE_PASS`
- exact content: `boot.img` V75 + `system.img` V89;
- the V89 execution text was verified inside `wifi-service.jar`, not only in the source.

Main hashes:

- boot V75: `fe89ef3181bfecea8d4bb24ceaed026a38f4005a8891a447c045b82781033be8`
- system standard sparse: `b4944555545b8a9f51304fc657c2f8ed9e4720a52bb4fbd62c4b869f9c8bb383`
- system legacy sparse/Odin: `5dafbe5b76eb49141333622dce898c587aa6fc37b9f0cd2b68765fbd89a30a2d`
- `wifi-service.jar`: `f00ea57e182d71bac10877bf239c4a0c7c5b0c43746925c80d2bba83c7825f1b`
- `libEGL_swiftshader.so`: `d7ed7adc0f7e238fa584548da939a6d4f5c8d3c4e9dcf3aeac9e3449bc220ce0`
- `SwiftAngle.apk`: `ff5f1b6ee015ab6778b8d88d6295ad4fe9ce91070e7fef4b849d777d239d75e9`

## Hardware test

1. Confirm the physical state, display, touch, button and ADB first.
2. The user flashes V89 in Odin AP, Auto Reboot OFF, no PIT or Re-Partition.
3. Boot with the saved Wi-Fi preference ON and **do not intervene for three minutes**.
4. It must connect automatically; seeing one or more `V89 SC2331 client start failure; retry N/6` messages
   before success is acceptable.
5. Confirm `CONNECTED/COMPLETED`, DHCP, Internet and the target app without the black network wait.
6. Repeat several boots before closing the race as resolved.
7. Test SwiftAngle at scale 2 separately; since `/data` is not wiped, the tablet will initially keep the
   current persistent value `1`.
