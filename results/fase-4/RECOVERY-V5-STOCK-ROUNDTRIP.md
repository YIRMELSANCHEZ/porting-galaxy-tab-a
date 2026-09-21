# Phase 4 -- Recovery v5 stock round-trip

Date: September 16, 2026.

## Objective

Validate in isolation the `mkbootimg` + DHTB + Spreadtrum signing chain using
only components extracted from the stock AQJ1 recovery that does boot. V5
introduces no Android 10 kernel, DT, ramdisk or cmdline.

## Components

| Component | Value |
|---|---|
| Stock kernel | `11,142,424` bytes |
| Stock ramdisk | `3,662,533` bytes, gzip/CPIO |
| Stock DT | `380,928` bytes |
| Cmdline | `console=ttyS1,115200n8` |
| Page size | `2048` |
| Stock recovery | `15,191,208` bytes |
| Recovery v5 | `15,191,204` bytes |

An independent extraction confirmed v5's kernel, ramdisk, DT and cmdline are
byte-by-byte identical to the stock recovery's. The ramdisk passes `gzip -t` and
its CPIO correctly enumerates `init`, `sbin/recovery` and essential resources.

**STOCK_ROUNDTRIP_V5_OFFLINE_VERIFY_PASS**

## Artifacts

- Image: `recovery-stock-roundtrip-v5-DO-NOT-FLASH.img`
- SHA-256: `e54137c306e3e24823db388e13ddf5b37c29de753f8d13991009dd2280d9c6b2`
- Odin package: `SM-T280-recovery-stock-roundtrip-PHASE4-v5-DO-NOT-FLASH.tar.md5`
- Odin internal MD5: `1d6d812f5658e06e04ede48e664ba520`
- Package SHA-256: `14478cd53b97f9833f56e5486e3fb11f77ab344f97208863a698d05f2f549600`

## Interpretation of the future test

- If v5 boots: the repackaging/signing chain is valid and the v4 failure is in
  the Android 10 components.
- If v5 does not boot: the problem is in DHTB, signing or generated metadata; no
  other Android 10 component should be tested until it is resolved.

V5 remains **DO NOT FLASH** until the interaction gate.

## Hardware result

Odin wrote v5 with a `PASS` result. The direct manual entry showed the stock
recovery menu and the `reboot system now` option. After selecting it, stock
Android booted fully.

**STOCK_ROUNDTRIP_V5_HARDWARE_BOOT_PASS**

The v2 rollback was not needed because v5 contains stock components and stayed
functional. This shows that the `mkbootimg`, DHTB, Spreadtrum signing, Odin
packaging, offsets and cmdline used are accepted by the hardware.

The v3/v4 failures must be attributed to one or more Android 10 components, not
to the packaging chain.
