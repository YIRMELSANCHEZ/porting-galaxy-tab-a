# Phase 4 -- Offline diagnosis and recovery v4

Date: September 16, 2026.

## v3 failure diagnosis

**ROOT_CAUSE_HIGH_CONFIDENCE: WRONG_KERNEL_ARTIFACT**

The v3 candidate contained `obj/KERNEL_OBJ/arch/arm/boot/zImage` (`5,267,712`
bytes). The device tree declares `BOARD_KERNEL_IMAGE_NAME := Image` and the
compiled `boot.img` contains `out/target/product/gtexswifi/kernel` (`11,883,332`
bytes). The stock recovery likewise contains an `11,142,424`-byte kernel. The v3
image was accepted by the bootloader and Odin, but did not advance past the
logo.

The DHTB header, Android header, offsets, page size and DT of v3 were
structurally valid. Replacing the full kernel with `zImage` is the difference
that best explains the early failure.

## Fix v4

V4 uses the same full `Image` kernel as `boot.img`, the same `dt.img` and a
recovery ramdisk recomposed with LZMA. To respect the 16 MiB physical partition
the following were removed:

- `lib/modules/sprdwl.ko` (not needed for USB diagnosis);
- multilingual graphical install, wipe and error text.

`init`, `recovery`, `adbd`, shell, linker, fonts, menu, icons and the
`no_command_text` image were kept.

## Verification

| Field | Value |
|---|---:|
| Image | `recovery-imagekernel-diagnostic-v4-DO-NOT-FLASH.img` |
| Size | `16,729,252` bytes |
| Limit | `16,777,216` bytes |
| Margin | `47,964` bytes |
| Kernel | `11,883,332` bytes |
| Ramdisk | `4,458,539` bytes |
| DT | `380,928` bytes |
| SHA-256 | `32217cc6ce717cf4c914cc27f3b4edb3dbecb080aafe027d0d975c7849eb31ec` |

The offline extraction confirmed kernel and DT are byte-by-byte identical to the
expected build artifacts; LZMA and CPIO were fully validated and the presence of
the essential executables was checked.

**RECOVERY_V4_OFFLINE_VERIFY_PASS**

This does not prove a functional boot. V4 remains **DO NOT FLASH** until a new
explicit authorization and a review of the rescue strategy.

## Later hardware result

The user authorized the test and Odin wrote v4 with a `PASS` result. The direct
manual entry into recovery hung at the `Samsung Galaxy Tab A6` logo; no UI or
ADB appeared:

**RECOVERY_V4_BOOT_FAIL**

Only the stock AQJ1 recovery was restored immediately with the v2 package. Odin
reported `PASS` and stock Android booted fully. Since recovery was requested via
keys and not via `adb reboot recovery`, there was no persistent command forcing
a pass through the stock menu.

**STOCK_RECOVERY_ROLLBACK_AFTER_V4_PASS**

The v4 failure shows that fixing the kernel format is not enough. Before another
test, the stock kernel/config, the real DT, the expected compression algorithm
and the ramdisk must be compared against a known-booting base. V4 must not be
flashed again.
