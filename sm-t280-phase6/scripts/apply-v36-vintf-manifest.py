#!/usr/bin/env python3
# V36 (phase 6.2 - framework hang ROOT CAUSE): the device has NO VINTF manifest.
# hwservicemanager, querying the manifest (listManifestByInterface ->
# getInstances) to answer getService/getTransport, null-derefs in libvintf
# (HalManifest::getInstances) and CRASHES (SIGSEGV). Its onrestart restarts the main class
# (system_server) in cascade, and HIDL is broken -> system_server hangs calling
# a cualquier HAL (memtrack durante ActivityManager::<init>, audio, etc.).
#
# Fix: provide a device VINTF manifest (device/samsung/gtexswifi/manifest.xml,
# declaring the HALs that ARE provided: graphics allocator@2.0/composer@2.1/mapper@2.0,
# configstore@1.1, health@2.0, memtrack@1.0 passthrough) and wire it with
# DEVICE_MANIFEST_FILE in BoardConfig -> installed at /vendor/etc/vintf/manifest.xml.
# With a valid (non-null) manifest, getInstances does not crash. Change in system.img;
# boot = V35. Idempotente.
import sys, shutil, os

SCRIPTS = "/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts"
DEVDIR = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi"
SRC = SCRIPTS + "/gtexswifi-manifest.xml"
DST = DEVDIR + "/manifest.xml"
BC = DEVDIR + "/BoardConfig.mk"

# 1) copy the manifest to the device tree
if not os.path.exists(SRC):
    print("V36_ERROR: falta " + SRC); sys.exit(1)
shutil.copyfile(SRC, DST)
print("V36_MANIFEST_COPIED -> device/samsung/gtexswifi/manifest.xml")

# 2) cablear DEVICE_MANIFEST_FILE en BoardConfig.mk
s = open(BC, encoding="utf-8", errors="surrogateescape").read()
if "DEVICE_MANIFEST_FILE" in s:
    print("V36_BOARDCONFIG_ALREADY"); sys.exit(0)
block = (
    "\n# V36: manifiesto VINTF del device (sin el, hwservicemanager null-deref en\n"
    "# libvintf HalManifest::getInstances -> SIGSEGV -> cascada que cuelga el framework)\n"
    "DEVICE_MANIFEST_FILE := device/samsung/gtexswifi/manifest.xml\n"
)
s = s.rstrip("\n") + "\n" + block
open(BC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V36_BOARDCONFIG_APPLIED")
