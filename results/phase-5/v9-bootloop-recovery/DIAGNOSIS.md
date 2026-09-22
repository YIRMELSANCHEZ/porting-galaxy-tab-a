# Phase 5 -- V9 diagnosis (failed): the bootloader ignores the boot.img cmdline

Date: 2026-09-17. Source: `results/phase-5/v9-bootloop-recovery/last_kmsg.txt`.

## Result

V9 (legacy rootfs in the ramdisk) did **not** fix the loop. Same first-stage
failure, and now with evidence that init **crashes**:

```
init: [libfs_mgr]ReadFstabFromDt(): failed to read fstab from dt
init: [libfs_mgr]ReadDefaultFstab(): failed to find device default fstab
init: Failed to fstab for first stage mount
init: Using Android DT directory /proc/device-tree/firmware/android/
init: #01 pc 00000daa  [heap:0015e000]        <-- init crash
init: Reboot ending, jumping to kernel
```

That V7, V8 and V9 fail **identically** (with the fstab in different places)
rules out the fstab location as the variable.

## Definitive root cause

The `last_kmsg` includes the REAL cmdline the Spreadtrum bootloader passes to the
kernel (`[setKernelParam]Cmdline:`):

```
mem=1536M init=/init ram=1536M lcd_id=... bootmode=2 ... androidboot.debug_level=0x4f4c
console=null ... androidboot.bootloader=T280XXU0AQJ1 androidboot.emmc_checksum=3
androidboot.serialno=3100315d******** ...
```

**It does not contain `androidboot.hardware=sc8830`, `console=ttyS1`, or
`androidboot.selinux=permissive`.** That is, **the bootloader (sboot) completely
ignores the boot.img's `BOARD_KERNEL_CMDLINE`** and passes its own fixed cmdline
(`console=null`, `init=/init`, and a few `androidboot.*` it generates itself).

Chained consequences:

- `androidboot.hardware` never reaches init -> `ro.hardware` empty ->
  `GetFstabPath()` returns "" -> the file-based fstab (`/fstab.sc8830`) is **never
  searched**, no matter where it is (minimal ramdisk, ROOT_OUT, etc.).
- The V7 cmdline fix (`androidboot.hardware=sc8830`) **never had any effect**.
- `ReadFstabFromDt()` also fails: the `/firmware/android/` node exists but
  **has no `fstab` subnode** (there is no `fstab` in the kernel's DTS).
- With no fstab by any path, first-stage does not mount `/system` and init crashes/reboots.

## Implication for the fix (V10)

The only reliable path on this device is the **Android 10 canonical one: declare
the fstab in the device tree** (`/firmware/android/fstab/system` ...), because:

- it does not depend on the cmdline (which the bootloader ignores),
- `ReadFstabFromDt()` reads it in first-stage and mounts `/system`.

Device: `hw_revision=5` -> `kernel/samsung/gtexswifi/arch/arm/boot/dts/sprd-scx35_gtexswifi_rev05.dts`.
Target system entry (from `fstab.sc8830`):
`/dev/block/platform/sdio_emmc/by-name/SYSTEM /system ext4 ro,errors=panic wait`.

It requires adding the `firmware/android/fstab` node to the DTS, recompiling the
kernel dtbs and regenerating `dt.img` + boot. It is a kernel-DT change, deeper
than the previous ramdisk iterations.

## Note

The V5-V9 changes (legacy sparse, init binary, ROOT_OUT) remain correct and
necessary; V10 adds the missing piece (fstab in DT). It does not revert them.
