#!/usr/bin/env python3
# V69: corrective for the V68 bootloop. Removes ONLY the two HIDL services that regress:
#   - GNSS (android.hardware.gnss@1.0-service/-impl): hangs system_server in
#     GnssLocationProvider.class_init_native() -> Watchdog mata system_server (~100s) -> bucle.
#   - Camera (android.hardware.camera.provider@2.4-service/-impl): crashes in a loop over a symbol
#     that is old and absent in the 5.1 blob.
# Keeps the rest of V68 (BT, sensors, power, light, memtrack, DRM clearkey) that on HW
# appear REGISTERED and OK. Change only in device.mk (PRODUCT_PACKAGES) and manifest.xml (VINTF).
# Rebuild: systemimage (V68 boot.img unchanged). Idempotent.
from pathlib import Path
import sys

DEVICE = Path("/home/lineage/android/lineage-17.1/device/samsung/gtexswifi")

def patch(path, removals, marker_absent_ok=True):
    s = path.read_text(encoding="utf-8", errors="surrogateescape")
    changed = 0
    for chunk in removals:
        if chunk in s:
            s = s.replace(chunk, "", 1)
            changed += 1
    path.write_text(s, encoding="utf-8", errors="surrogateescape")
    return changed

def main():
    device_mk = DEVICE / "device.mk"
    manifest = DEVICE / "manifest.xml"

    mk_removals = [
        "    android.hardware.camera.provider@2.4-service \\\n",
        "    android.hardware.camera.provider@2.4-impl \\\n",
        "    android.hardware.gnss@1.0-service \\\n",
        "    android.hardware.gnss@1.0-impl \\\n",
    ]
    man_removals = [
        ("    <hal format=\"hidl\">\n"
         "        <name>android.hardware.camera.provider</name>\n"
         "        <transport>hwbinder</transport>\n"
         "        <version>2.4</version>\n"
         "        <interface><name>ICameraProvider</name><instance>legacy/0</instance></interface>\n"
         "    </hal>\n"),
        ("    <hal format=\"hidl\">\n"
         "        <name>android.hardware.gnss</name>\n"
         "        <transport>hwbinder</transport>\n"
         "        <version>1.0</version>\n"
         "        <interface><name>IGnss</name><instance>default</instance></interface>\n"
         "    </hal>\n"),
    ]

    mk_changed = patch(device_mk, mk_removals)
    man_changed = patch(manifest, man_removals)

    # Sanity: there must be no references left to the gnss/camera provider
    left = []
    for p in (device_mk, manifest):
        d = p.read_text(encoding="utf-8", errors="surrogateescape")
        if "gnss@1.0" in d or "camera.provider@2.4" in d or "android.hardware.gnss" in d or "android.hardware.camera.provider" in d:
            left.append(p.name)
    print(f"V69: device.mk quitadas {mk_changed}/4 lineas; manifest quitados {man_changed}/2 blocks")
    if left:
        print(f"V69_WARN: quedan referencias en {left}"); return 1
    if mk_changed == 0 and man_changed == 0:
        print("V69_ALREADY (nothing to remove)"); return 0
    print("V69_APPLIED -> GNSS and Camera removed; rest of V68 kept")
    return 0

if __name__ == "__main__":
    sys.exit(main())
