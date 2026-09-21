# Phase 2 -- Source inventory

## Scope

Research and static analysis on the PC. The tablet was not modified.

| Component | Located source | Usefulness | Status |
|---|---|---|---|
| SM-T280 device tree | `underscoremone/android_device_samsung_gtexswifi`, CM 14.1 | Most complete base of board, partitions, init and HAL | PARTIAL |
| Historical device tree | `gtexswifi/android_device_samsung_gtexswifi`, `cm-14.1-other` | Early reference; declares partial boot/framebuffer | PARTIAL |
| Community kernel | `underscoremone/android_kernel_samsung_gtexswifi`, CM 14.1 | Linux 3.10.65, defconfig and device drivers | PARTIAL |
| Approximate stock kernel | `T280XXU0AQA4` branch of the same mirror | Comparison with the earlier Samsung firmware | PARTIAL |
| Exact AQJ1 stock kernel | Not located | Exact baseline of the tablet | MISSING |
| Spreadtrum hardware | `underscoremone/android_hardware_sprd`, CM 14.1 | HWC, gralloc, ION, multimedia, Wi-Fi and power | PARTIAL |
| Vendor blobs | `underscoremone/proprietary_vendor_samsung_gtexswifi` | 113 files; 95 ARM32 ELFs | PARTIAL |
| Boot format | `osm0sis/dhtbsign` and device-tree tools | Confirms the 512-byte DHTB header | DETECTED |
| Official LineageOS 17.1 | Not located | No official device-specific baseline | MISSING |

## Assessment

The CM/Lineage 14.1 base reduces the hardware-identification work, but it cannot be reused without
adaptation. Its patches to `bionic`, `frameworks/av`, `frameworks/native`, Bluetooth and `system/core`
show that even Android 7.1 needed device-specific compatibility. The redistributed binaries do not include
clear license terms; they must be treated as proprietary artifacts and not published automatically.

The official Samsung Open Source portal remains the preferred source to look for the exact
`T280XXU0AQJ1` package. Until it is found, AQA4 is only an approximation and does not prove binary
correspondence.
