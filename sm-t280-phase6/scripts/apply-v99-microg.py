#!/usr/bin/env python3
# V99: integrates microG (GmsCore + FakeStore) as a priv-app in the build.
# Requires that device/samsung/gtexswifi/microg/ already contains GmsCore.apk, FakeStore.apk, Android.mk and
# microg-permissions.xml (created separately). The APKs go via BUILD_PREBUILT (Android.mk) with PRESIGNED
# (the build rejects prebuilt APKs in PRODUCT_COPY_FILES); PRESIGNED keeps the microG signature on which
# the spoofing depends. This script adds the modules and copies the permissions xml. Idempotent.
import pathlib, sys

T = pathlib.Path("/home/lineage/android/lineage-17.1")
D = T / "device/samsung/gtexswifi"
DM = D / "device.mk"
M = D / "microg"

for f in ("GmsCore.apk", "FakeStore.apk", "Android.mk", "microg-permissions.xml"):
    if not (M / f).exists():
        sys.exit("ERROR: falta device/samsung/gtexswifi/microg/%s" % f)

s = DM.read_text()
if "V99: microG" in s:
    print("device.mk: already integrates microG")
else:
    s = s.rstrip() + (
        "\n\n# V99: microG (GmsCore = com.google.android.gms, FakeStore = com.android.vending) como\n"
        "# priv-app (BUILD_PREBUILT PRESIGNED en microg/Android.mk). APK oficiales firmados con la clave\n"
        "# microG que reconoce PackageManagerService (isMicrogSigned, solo ro.debuggable=1). Permisos\n"
        "# privilegiados exactos en microg-permissions.xml.\n"
        "PRODUCT_PACKAGES += \\\n"
        "    GmsCore \\\n"
        "    FakeStore\n\n"
        "PRODUCT_COPY_FILES += \\\n"
        "    device/samsung/gtexswifi/microg/microg-permissions.xml:system/etc/permissions/microg-permissions.xml\n"
    )
    DM.write_text(s)
    print("device.mk: microG added (BUILD_PREBUILT + permissions)")

print("V99_DONE")
