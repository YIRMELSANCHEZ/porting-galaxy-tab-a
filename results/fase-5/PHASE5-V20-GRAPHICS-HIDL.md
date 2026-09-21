# Phase 5 -- V20: graphics HIDL services missing from the device tree

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V19 diagnosis)

After the pthread shim (V19), `surfaceflinger` still aborts with
`EX_TRANSACTION_FAILED` when requesting
`android.hardware.graphics.composer@2.1`. Build inspection:

- `system/lib/hw/` **DOES** have the blob modules: `gralloc.sc8830.so`,
  `hwcomposer.sc8830.so`, `libGLES_mali.so`, etc.
- `system/bin/hw/` does **NOT** have the graphics HIDL services: missing
  `composer@2.1-service`, `allocator@2.0-service`, `mapper@2.0-impl`.
- The VINTF compatibility matrix REQUIRES them, but nobody provides them -> the
  HIDL call fails -> surfaceflinger aborts.
- `device.mk` includes the MODULES (`gralloc.sc8830`, `hwcomposer.sc8830`,
  `libGLES_mali.so`) but NOT the services that wrap them.

It is a **device-tree omission**: in Android 10 the legacy modules need a HIDL
service to expose them (with hwc2on1adapter / Gralloc1On0 adapters).

## Change

`device/samsung/gtexswifi/device.mk`, "Graphics & HWC" section
(`apply-v20-graphics-services.py`): add the AOSP default services to
`PRODUCT_PACKAGES`:

```
android.hardware.graphics.allocator@2.0-service
android.hardware.graphics.mapper@2.0-impl
android.hardware.graphics.composer@2.1-service
```

These services load the blob modules and include the adapters for HWC1/
gralloc0-1. Goes in system.img -> full build; boot+system are repackaged.

## Offline validation

- Build: `build-full-rom.sh` OK. The services are `vendor:` modules -> installed
  in **`system/vendor/bin/hw/`** (composer/allocator) and `system/vendor/lib/hw/`
  (mapper impl), with their `.rc` in `system/vendor/etc/init/`. (NOT in `system/bin/hw`.)
  Verified present.
- Packaging: `prepare-v20-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-graphics-hidl-PHASE5-v20-DO-NOT-FLASH.tar.md5`
- package_sha256: `1c7e442f3fd2b70a77520dbd0059a78511d11056be189617f41a5a4614c7e753`
- boot_sha256: `75b50216b1124af9f8d23e159b8ba02b58632ee795b68eb15b3ca9dbcd6d4b18`
- system_sha256 (legacy sparse): `dda465534923571f284c2e769ea781adcd789ba780edde0796a3c10683a82694`

## Expected interpretation

- Success: the composer@2.1 service comes up and wraps `hwcomposer.sc8830.so`;
  surfaceflinger gets the composer and composes -> **boot animation** (big
  milestone).
- Possible next hurdles: the default composer@2.1-service may crash loading the
  old HWC1 (needing an explicit hwc2on1adapter), or the allocator may expect
  gralloc1 (Gralloc1On0Adapter). Isolate with the new `last_kmsg`.
- keymaster and audio remain pending as separate HALs.
