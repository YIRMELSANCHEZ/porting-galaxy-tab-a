# Phase 4 -- Recovery v8, base kernel 3.10.65

## Reason

V7 isolated the failure to the recompiled kernel. The comparison showed:

- functional stock: Linux `3.10.65`, GCC 4.8, `11,142,424` bytes;
- failed v7: Linux `3.10.108`, GCC 4.9, `11,891,524` bytes.

The history contains the merge `74c1b5f015f` (`v3.10.65`) immediately after
importing the Samsung T280XXU0AQL4 code. An isolated worktree was created and
that revision was compiled with GCC 4.9, keeping the toolchain constant to first
evaluate the 3.10.65->3.10.108 update.

## V8

- Kernel: revision `74c1b5f015fd39a8eb5a30e7ec3ac242ace51721`.
- Version: Linux `3.10.65`.
- Compiler: GCC 4.9.
- Kernel SHA-256: `a67c7a0d7f2630250218fa510661b12e4948d9c599e9fbdb0fd8ca05594fcfb2`.
- Ramdisk, DT, cmdline and offsets: stock byte-for-byte.
- Image: `15,801,508` bytes; margin `975,708` bytes.
- Image SHA-256: `a021d3e4ffc511cc36701d822b81f9cab4aa73d41cd8e92d596109930dccbd51`.

**KERNEL_3_10_65_V8_OFFLINE_VERIFY_PASS**

Odin package: `SM-T280-recovery-kernel-3.10.65-PHASE4-v8-DO-NOT-FLASH.tar.md5`,
internal MD5 `79069edeaa8d269ad5cfe595676d4b27`, SHA-256
`9c330c933ab8e38761dc71d09989aab07162a3b78ecd0b70a69c2906cc45bb13`.

Future interpretation:

- if v8 boots, there is a regression between 3.10.65 and 3.10.108;
- if v8 fails, the next isolation will be toolchain/config against the stock
  binary, keeping the 3.10.65 base.

## Hardware result

- Odin: `PASS`; only the `RECOVERY` partition was written.
- Direct boot to recovery: **FAIL**, Samsung Galaxy Tab A6 logo hung.
- Stock recovery v2 restored via Odin: `PASS`.
- Stock Android booted fully after the restore.

**KERNEL_3_10_65_V8_BOOT_FAIL**

The 3.10.65 base version does not fix the failure. This rules out the
3.10.65->3.10.108 regression as the sole explanation. The next isolation keeps
revision 3.10.65 and changes the compiler from GCC 4.9 to GCC 4.8, matching the
chain declared by the stock kernel.
