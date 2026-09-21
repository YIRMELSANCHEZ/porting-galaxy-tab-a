#!/usr/bin/env python3
"""Apply the single cumulative V68 bring-up batch.

V68 intentionally produces one test candidate, not a package per fix.  It:
* wires legacy Bluetooth, sensors, power, camera, GNSS and lights through HIDL;
* binderizes memtrack and adds ClearKey DRM (not Widevine);
* restores the native HWC1/GSP attempt with a gralloc/fb fallback;
* fixes ION cache invalidation on non-ION buffers and SystemUI HW bitmap saves;
* provides early /efs and /productinfo mountpoints and libiwnpi for wcnd;
* disables the pointless modem-monitor retry loop on the Wi-Fi-only SM-T280.

It deliberately does not add gatekeeper, thermal or vibrator services when no
usable legacy HAL exists. Android's software GateKeeper fallback is retained.
"""

from pathlib import Path
import sys


ROOT = Path("/home/lineage/android/lineage-17.1")
DEVICE = ROOT / "device/samsung/gtexswifi"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="surrogateescape")


def write(path: Path, data: str) -> None:
    path.write_text(data, encoding="utf-8", errors="surrogateescape")


def replace_once(path: Path, old: str, new: str, marker: str) -> None:
    data = read(path)
    if marker in data:
        print(f"V68_ALREADY {path}")
        return
    count = data.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor for {marker!r}, got {count}")
    write(path, data.replace(old, new, 1))
    print(f"V68_PATCHED {path}")


def main() -> int:
    device_mk = DEVICE / "device.mk"
    device_anchor = """PRODUCT_PACKAGES += \\
    android.hardware.wifi@1.0-service.legacy

# Usb accessory
"""
    device_new = """PRODUCT_PACKAGES += \\
    android.hardware.wifi@1.0-service.legacy

# V68 consolidated legacy-HAL bridge batch.  These binderized services wrap
# the 32-bit Android 5.1 HAL modules already shipped for this device.
PRODUCT_PACKAGES += \\
    android.hardware.bluetooth@1.0-service \\
    android.hardware.bluetooth@1.0-impl \\
    android.hardware.sensors@1.0-service \\
    android.hardware.sensors@1.0-impl \\
    android.hardware.power@1.0-service \\
    android.hardware.power@1.0-impl \\
    android.hardware.camera.provider@2.4-service \\
    android.hardware.camera.provider@2.4-impl \\
    android.hardware.gnss@1.0-service \\
    android.hardware.gnss@1.0-impl \\
    android.hardware.light@2.0-service \\
    android.hardware.light@2.0-impl \\
    android.hardware.memtrack@1.0-service \\
    android.hardware.memtrack@1.0-impl \\
    android.hardware.drm@1.2-service.clearkey \\
    libiwnpi

# Usb accessory
"""
    replace_once(device_mk, device_anchor, device_new, "V68 consolidated legacy-HAL bridge")

    root_anchor = """    $(LOCAL_PATH)/rootdir/init.wifi.rc:root/init.wifi.rc \\
    $(LOCAL_PATH)/rootdir/init.dhcp.rc:root/init.dhcp.rc
"""
    root_new = """    $(LOCAL_PATH)/rootdir/init.wifi.rc:root/init.wifi.rc \\
    $(LOCAL_PATH)/rootdir/init.dhcp.rc:root/init.dhcp.rc \\
    $(LOCAL_PATH)/rootdir/efs/.keep:root/efs/.keep \\
    $(LOCAL_PATH)/rootdir/productinfo/.keep:root/productinfo/.keep
"""
    replace_once(device_mk, root_anchor, root_new, "rootdir/efs/.keep")

    for rel, label in (("rootdir/efs/.keep", "V68 EFS mountpoint\n"),
                       ("rootdir/productinfo/.keep", "V68 productinfo mountpoint\n")):
        path = DEVICE / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            write(path, label)
            print(f"V68_CREATED {path}")

    # The mountpoint directories are included in the system-as-root image.
    # e2fsdroid requires an explicit label for every root entry even though
    # these directories are replaced by their ext4 partitions during boot.
    file_contexts = DEVICE / "sepolicy/file_contexts"
    data = read(file_contexts)
    labels = """\n# V68 system-as-root additions\n/productinfo(/.*)?  u:object_r:efs_file:s0\n/file_contexts\\.bin  u:object_r:file_contexts_file:s0\n"""
    if "/productinfo(/.*)?" not in data:
        write(file_contexts, data.rstrip() + labels)
        print(f"V68_PATCHED {file_contexts} (NV mountpoint labels)")

    # libiwnpi also has a buildable source module under hardware/sprd/iwnpi.
    # Package that module; a PRODUCT_COPY_FILES blob would duplicate its output.
    data = read(device_mk)
    if "+    libiwnpi\n" in data:
        data = data.replace("+    libiwnpi\n", "    libiwnpi\n", 1)
        write(device_mk, data)
        print(f"V68_PATCHED {device_mk} (normalized source libiwnpi)")
    if "    libiwnpi\n" not in data:
        anchor = "    android.hardware.drm@1.2-service.clearkey\n"
        if anchor not in data:
            raise RuntimeError("device.mk: V68 libiwnpi package anchor not found")
        data = data.replace(anchor,
                            "    android.hardware.drm@1.2-service.clearkey \\\n    libiwnpi\n", 1)
        write(device_mk, data)
        print(f"V68_PATCHED {device_mk} (source libiwnpi)")

    vendor_mk = ROOT / "vendor/samsung/gtexswifi/gtexswifi-vendor.mk"
    data = read(vendor_mk)
    duplicate = "    vendor/samsung/gtexswifi/proprietary/lib/libiwnpi.so:system/lib/libiwnpi.so \\\n"
    if duplicate in data:
        write(vendor_mk, data.replace(duplicate, "", 1))
        print(f"V68_PATCHED {vendor_mk} (removed duplicate blob copy)")

    # V68 correction: the old iwnpi source needs a private libnl header that
    # Android 10 no longer exports. Use the proven stock library for wcnd and
    # rename the unused source target so PRODUCT_COPY_FILES can own the path.
    data = read(device_mk)
    lines = data.splitlines(keepends=True)
    normalized = []
    for line in lines:
        if line.lstrip("+").strip() == "libiwnpi":
            if normalized and "android.hardware.drm@1.2-service.clearkey" in normalized[-1]:
                normalized[-1] = normalized[-1].rstrip("\n").rstrip().rstrip("\\").rstrip() + "\n"
            continue
        normalized.append(line)
    write(device_mk, "".join(normalized))

    iwnpi_mk = ROOT / "hardware/sprd/iwnpi/Android.mk"
    iwnpi_old = "LOCAL_MODULE := libiwnpi\n"
    iwnpi_new = """# V68: gtexswifi installs the compatible stock prebuilt.
ifeq ($(TARGET_DEVICE),gtexswifi)
LOCAL_MODULE := libiwnpi_source_unsupported
else
LOCAL_MODULE := libiwnpi
endif
"""
    replace_once(iwnpi_mk, iwnpi_old, iwnpi_new, "libiwnpi_source_unsupported")

    data = read(vendor_mk)
    if "libiwnpi.so:system/lib/libiwnpi.so" not in data:
        lines = data.splitlines(keepends=True)
        added = []
        for line in lines:
            added.append(line)
            if "proprietary/bin/wcnd:system/bin/wcnd" in line:
                added.append(
                    "    vendor/samsung/gtexswifi/proprietary/lib/libiwnpi.so:"
                    "system/lib/libiwnpi.so \\\n"
                )
        if len(added) == len(lines):
            raise RuntimeError("vendor mk: wcnd anchor missing")
        write(vendor_mk, "".join(added))
        print(f"V68_PATCHED {vendor_mk} (stock libiwnpi for wcnd)")

    data = read(vendor_mk)
    lines = data.splitlines(keepends=True)
    normalized = [line.lstrip("+") if line.lstrip("+").startswith("    vendor/") else line
                  for line in lines]
    if normalized != lines:
        write(vendor_mk, "".join(normalized))
        print(f"V68_PATCHED {vendor_mk} (normalized generated vendor line)")

    manifest = DEVICE / "manifest.xml"
    memtrack_old = """    <hal format="hidl">
        <name>android.hardware.memtrack</name>
        <transport arch="32">passthrough</transport>
        <version>1.0</version>
        <interface>
            <name>IMemtrack</name>
            <instance>default</instance>
        </interface>
    </hal>
"""
    memtrack_new = """    <hal format="hidl">
        <name>android.hardware.memtrack</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface>
            <name>IMemtrack</name>
            <instance>default</instance>
        </interface>
    </hal>
"""
    replace_once(manifest, memtrack_old, memtrack_new, "<transport>hwbinder</transport>\n        <version>1.0</version>\n        <interface>\n            <name>IMemtrack</name>")

    manifest_anchor = """    <sepolicy>
        <version>29.0</version>
    </sepolicy>
"""
    manifest_new = """    <!-- V68: binderized wrappers around the available legacy HALs. -->
    <hal format="hidl">
        <name>android.hardware.bluetooth</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface><name>IBluetoothHci</name><instance>default</instance></interface>
    </hal>
    <hal format="hidl">
        <name>android.hardware.sensors</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface><name>ISensors</name><instance>default</instance></interface>
    </hal>
    <hal format="hidl">
        <name>android.hardware.power</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface><name>IPower</name><instance>default</instance></interface>
    </hal>
    <hal format="hidl">
        <name>android.hardware.camera.provider</name>
        <transport>hwbinder</transport>
        <version>2.4</version>
        <interface><name>ICameraProvider</name><instance>legacy/0</instance></interface>
    </hal>
    <hal format="hidl">
        <name>android.hardware.gnss</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface><name>IGnss</name><instance>default</instance></interface>
    </hal>
    <hal format="hidl">
        <name>android.hardware.light</name>
        <transport>hwbinder</transport>
        <version>2.0</version>
        <interface><name>ILight</name><instance>default</instance></interface>
    </hal>
    <hal format="hidl">
        <name>android.hardware.drm</name>
        <transport>hwbinder</transport>
        <version>1.2</version>
        <interface><name>ICryptoFactory</name><instance>clearkey</instance></interface>
        <interface><name>IDrmFactory</name><instance>clearkey</instance></interface>
    </hal>
    <sepolicy>
        <version>29.0</version>
    </sepolicy>
"""
    replace_once(manifest, manifest_anchor, manifest_new, "V68: binderized wrappers")

    gralloc = ROOT / "hardware/sprd/gralloc/scx30g_v2/gralloc_module.cpp"
    ion_old = """\t\tion_invalidate_fd(m->ion_client, hnd->share_fd);
"""
    ion_new = """\t\t/* V68: framebuffer/UMP handles do not own an ION dma-buf fd.
\t\t\t * Passing their -1/stale share_fd to ION produced ERR_PTR(-EBADF)
\t\t\t * on every software lock and flooded the kernel log. */
\t\tif ((hnd->flags & private_handle_t::PRIV_FLAGS_USES_ION) &&
\t\t    hnd->share_fd >= 0) {
\t\t\tion_invalidate_fd(m->ion_client, hnd->share_fd);
\t\t}
"""
    replace_once(gralloc, ion_old, ion_new, "V68: framebuffer/UMP handles")

    screenshot = ROOT / "frameworks/base/packages/SystemUI/src/com/android/systemui/screenshot/GlobalScreenshot.java"
    shot_decl_old = """        Bitmap image = mParams.image;
        Resources r = context.getResources();

        try {
"""
    shot_decl_new = """        Bitmap image = mParams.image;
        Bitmap imageToSave = image;
        Resources r = context.getResources();

        try {
            // V68: Bitmap.compress() cannot encode a hardware-only bitmap on
            // this legacy Mali/gralloc stack. Keep the original for smart
            // actions, but encode an explicit software copy.
            if (image != null && image.getConfig() == Bitmap.Config.HARDWARE) {
                imageToSave = image.copy(Bitmap.Config.ARGB_8888, false);
                if (imageToSave == null) {
                    throw new IOException("Failed to copy hardware screenshot");
                }
            }
"""
    replace_once(screenshot, shot_decl_old, shot_decl_new, "V68: Bitmap.compress()")
    shot_compress_old = """                    if (!image.compress(Bitmap.CompressFormat.PNG, 100, out)) {
"""
    shot_compress_new = """                    if (!imageToSave.compress(Bitmap.CompressFormat.PNG, 100, out)) {
"""
    replace_once(screenshot, shot_compress_old, shot_compress_new, "imageToSave.compress")
    shot_recycle_old = """        // Recycle the bitmap data
        if (image != null) {
            image.recycle();
        }
"""
    shot_recycle_new = """        // Recycle both the optional software copy and the source bitmap.
        if (imageToSave != null && imageToSave != image) {
            imageToSave.recycle();
        }
        if (image != null) {
            image.recycle();
        }
"""
    replace_once(screenshot, shot_recycle_old, shot_recycle_new, "optional software copy")

    loader = ROOT / "hardware/interfaces/graphics/composer/2.1/utils/passthrough/include/composer-passthrough/2.1/HwcLoader.h"
    load_old = """    static IComposer* load() {
        const hw_module_t* module = loadModule();
        if (!module) {
            return nullptr;
        }

        auto hal = createHalWithAdapter(module);
        if (!hal) {
            return nullptr;
        }

        return createComposer(std::move(hal));
    }

    // load hwcomposer2 module
    static const hw_module_t* loadModule() {
        const hw_module_t* module;
        // V27: force framebuffer adapter. El HWC Spreadtrum (hwcomposer.sc8830)
        // falla al alocar su buffer de overlay en gralloc0; saltamos el modulo
        // HWC y usamos gralloc -> HWC2OnFbAdapter (SF compone por GLES a fb0).
        ALOGI("V27: skipping HWC module; forcing gralloc/framebuffer adapter");
        int error = hw_get_module(GRALLOC_HARDWARE_MODULE_ID, &module);

        if (error) {
            ALOGE("failed to get hwcomposer or gralloc module");
            return nullptr;
        }

        return module;
    }
"""
    load_new = """    static IComposer* load() {
        const hw_module_t* module = nullptr;

        // V68: retry the Spreadtrum HWC1/GSP path now that gralloc/ION has
        // received the later bring-up fixes. HWC2On1Adapter exposes it to SF.
        int error = hw_get_module(HWC_HARDWARE_MODULE_ID, &module);
        if (!error && module != nullptr) {
            auto hal = createHalWithAdapter(module);
            if (hal) {
                ALOGI("V68: using native Spreadtrum HWC through HWC2On1Adapter");
                return createComposer(std::move(hal));
            }
            ALOGE("V68: native HWC open/init failed; falling back to framebuffer");
        } else {
            ALOGE("V68: native HWC module unavailable (%d); falling back to framebuffer", error);
        }

        module = nullptr;
        error = hw_get_module(GRALLOC_HARDWARE_MODULE_ID, &module);
        if (error || module == nullptr) {
            ALOGE("V68: failed to get gralloc fallback module (%d)", error);
            return nullptr;
        }

        auto hal = createHalWithAdapter(module);
        if (!hal) {
            ALOGE("V68: framebuffer fallback open/init failed");
            return nullptr;
        }
        ALOGI("V68: using V67 gralloc/framebuffer fallback");
        return createComposer(std::move(hal));
    }
"""
    replace_once(loader, load_old, load_new, "V68: retry the Spreadtrum HWC1/GSP")

    audio = ROOT / "hardware/sprd/audio/sc8830/audio_hw.c"
    audio_old = """vb_ctl_modem_monitor_open (adev);

/*
this is used to loopback test.
*/
"""
    audio_new = """/* V68: SM-T280 is Wi-Fi-only. There is no modemd socket, so the legacy
 * monitor only wakes every two seconds and logs ECONNREFUSED forever. Voice-call
 * state is not applicable on this product; do not start that monitor thread. */
ALOGI("V68: modem monitor disabled on Wi-Fi-only gtexswifi");

/*
this is used to loopback test.
*/
"""
    replace_once(audio, audio_old, audio_new, "V68: modem monitor disabled")

    print("V68_CONSOLIDATED_PATCH_PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"V68_PATCH_ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
