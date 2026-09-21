#!/usr/bin/env python3
# V44 (WiFi bring-up, step 1 - FOUNDATION: get wlan0 to appear): the device boots fully
# (V43) but WiFi does not activate. Diagnosis:
#   - CONFIG_SC2331=m: the WiFi driver of the Marlin sc2331 chip is a MODULE (.ko); it was never
#     installed -> no wlan0 (does not appear in /sys/class/net).
#   - There is no WiFi vendor HAL (android.hardware.wifi@1.0-service / IWifi) -> nothing loads the
#     driver or creates the interface. On enabling WiFi: "WifiNative: Failed to connect to
#     supplicant" y "wifi driver unloaded".
#   - the device's init.wifi.rc is OLD style (pre-HIDL): the wpa_supplicant service uses
#     an old socket and does NOT declare the HIDL ISupplicant interface (addressed in V45).
# The chip firmware (sc2331_fw.bin, etc.) IS present in /system/etc/firmware.
#
# V44 lays the foundation (isolating the most uncertain part: loading the driver and creating wlan0):
#   1) Instalar sprdwl.ko (ya compilado en KERNEL_OBJ, vermagic 3.10.108-g95996f39350-dirty
#      = kernel de boot.img V35) en WIFI_DRIVER_MODULE_PATH (/lib/modules -> /system/lib/
#      modules/sprdwl.ko). Copied as a device prebuilt (kernel/boot do NOT change).
#   2) PRODUCT_PACKAGES += android.hardware.wifi@1.0-service (IWifi; class hal; capability
#      SYS_MODULE -> does insmod of the driver; creates wlan0). Installs in /system/vendor/bin/hw.
#   3) manifiesto VINTF += wifi@1.0 IWifi (hwbinder).
# Planned verification: after flashing, a manual `insmod /system/lib/modules/sprdwl.ko` must
# create wlan0 and download the firmware; IWifi registered in lshal. The HIDL supplicant (to
# associate to a network) goes in V45. Only system.img changes; boot = V35. Idempotent.
import sys, shutil

ROOT = "/home/lineage/android/lineage-17.1"
DEVMK = ROOT + "/device/samsung/gtexswifi/device.mk"
SRCMAN = "/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts/gtexswifi-manifest.xml"
DSTMAN = ROOT + "/device/samsung/gtexswifi/manifest.xml"

# --- 1+2) device.mk: install the .ko + IWifi HAL ---
s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()
OLD = (
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.keymaster@4.0-service\n"
)
NEW = (
    OLD
    + "\n"
    "# V44: WiFi paso 1 - driver sprdwl.ko (modulo Marlin sc2331, ya compilado contra el\n"
    "# kernel de boot.img V35) en WIFI_DRIVER_MODULE_PATH, + HAL vendor IWifi que hace insmod\n"
    "# del driver (SYS_MODULE) y crea wlan0. Sin esto no existe la interfaz wlan0.\n"
    "PRODUCT_COPY_FILES += \\\n"
    "    $(LOCAL_PATH)/prebuilt/modules/sprdwl.ko:system/lib/modules/sprdwl.ko\n"
    "\n"
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.wifi@1.0-service\n"
)
if "android.hardware.wifi@1.0-service" in s:
    print("V44_DEVMK_ALREADY")
elif OLD not in s:
    print("V44_ERROR: cannot find the expected keymaster@4.0-service (V41) block")
    sys.exit(1)
else:
    s = s.replace(OLD, NEW, 1)
    open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("V44_DEVMK_APPLIED -> sprdwl.ko + android.hardware.wifi@1.0-service")

# --- 3) manifiesto VINTF: wifi@1.0 IWifi ---
m = open(SRCMAN, encoding="utf-8", errors="surrogateescape").read()
WIFI_BLOCK = (
    "    <hal format=\"hidl\">\n"
    "        <name>android.hardware.wifi</name>\n"
    "        <transport>hwbinder</transport>\n"
    "        <version>1.0</version>\n"
    "        <interface>\n"
    "            <name>IWifi</name>\n"
    "            <instance>default</instance>\n"
    "        </interface>\n"
    "    </hal>\n"
)
if "<name>android.hardware.wifi</name>" in m:
    print("V44_MANIFEST_ALREADY")
else:
    anchor = "    <sepolicy>"
    if anchor not in m:
        print("V44_ERROR: cannot find <sepolicy> in the manifest"); sys.exit(1)
    m = m.replace(anchor, WIFI_BLOCK + anchor, 1)
    open(SRCMAN, "w", encoding="utf-8", errors="surrogateescape").write(m)
    print("V44_MANIFEST_SRC_APPLIED")

shutil.copyfile(SRCMAN, DSTMAN)
print("V44_MANIFEST_COPIED -> device/samsung/gtexswifi/manifest.xml")
