#!/usr/bin/env python3
# V45 (WiFi bring-up, step 2 - HIDL supplicant to be able to ASSOCIATE to a network): V44 left the
# driver OK (insmod manual -> wlan0/p2p0 creados, firmware sc2331 cargado, IWifi 1.0-1.3
# registered). But the framework loads the driver and UNLOADS it when the supplicant fails:
#   SupplicantStaIfaceHal: Starting supplicant using init
#   WifiNative: Failed to connect to supplicant -> wifi driver unloaded
# Cause: the device's init.wifi.rc defines wpa_supplicant in OLD style (pre-HIDL):
# it starts with -iwlan0 -c<conf> (fixed interface + config via command line) and does NOT declare
# the HIDL interface android.hardware.wifi.supplicant@1.1::ISupplicant. In Android 10 the
# framework speaks over HIDL (ISupplicant) and adds the interface dynamically (addInterface),
# not via -i/-c, so it cannot connect with the old supplicant.
#
# Fix: rewrite the wpa_supplicant service to the Android 10 HIDL style:
#   - without -iwlan0 -c<conf> (the framework adds wlan0 via HIDL);
#   - -O<socketdir> -dd -g@android:wpa_wlan0;
#   - declare the ISupplicant 1.0 and 1.1 interfaces;
#   - group system wifi inet.
# + VINTF manifest += wifi.supplicant@1.1 ISupplicant (hwbinder). The binary
# wpa_supplicant is already compiled with the HIDL supplicant@1.0/1.1/1.2 libs. Only system changes
# system.img; boot = V35. Cumulative over V44. Idempotent.
import sys, shutil

ROOT = "/home/lineage/android/lineage-17.1"
RC = ROOT + "/device/samsung/gtexswifi/rootdir/init.wifi.rc"
SRCMAN = "/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts/gtexswifi-manifest.xml"
DSTMAN = ROOT + "/device/samsung/gtexswifi/manifest.xml"

OLD = (
    "service wpa_supplicant /system/bin/wpa_supplicant -g@android:wpa_wlan0 \\\n"
    "    -iwlan0 -Dnl80211 -c/data/misc/wifi/wpa_supplicant.conf -e/data/misc/wifi/entropy.bin\n"
    "    class main\n"
    "    socket wpa_wlan0 dgram 660 wifi wifi\n"
    "    disabled\n"
    "    oneshot\n"
)
NEW = (
    "service wpa_supplicant /system/bin/wpa_supplicant \\\n"
    "    -O/data/misc/wifi/sockets -dd -g@android:wpa_wlan0\n"
    "    interface android.hardware.wifi.supplicant@1.0::ISupplicant default\n"
    "    interface android.hardware.wifi.supplicant@1.1::ISupplicant default\n"
    "    class main\n"
    "    socket wpa_wlan0 dgram 660 wifi wifi\n"
    "    group system wifi inet\n"
    "    disabled\n"
    "    oneshot\n"
)

r = open(RC, encoding="utf-8", errors="surrogateescape").read()
if "supplicant@1.1::ISupplicant" in r:
    print("V45_RC_ALREADY")
elif OLD not in r:
    print("V45_ERROR: cannot find the expected service wpa_supplicant block")
    sys.exit(1)
else:
    r = r.replace(OLD, NEW, 1)
    open(RC, "w", encoding="utf-8", errors="surrogateescape").write(r)
    print("V45_RC_APPLIED -> wpa_supplicant HIDL (ISupplicant 1.0/1.1)")

# manifiesto VINTF: wifi.supplicant@1.1 ISupplicant
m = open(SRCMAN, encoding="utf-8", errors="surrogateescape").read()
SUP_BLOCK = (
    "    <hal format=\"hidl\">\n"
    "        <name>android.hardware.wifi.supplicant</name>\n"
    "        <transport>hwbinder</transport>\n"
    "        <version>1.1</version>\n"
    "        <interface>\n"
    "            <name>ISupplicant</name>\n"
    "            <instance>default</instance>\n"
    "        </interface>\n"
    "    </hal>\n"
)
if "android.hardware.wifi.supplicant</name>" in m:
    print("V45_MANIFEST_ALREADY")
else:
    anchor = "    <sepolicy>"
    if anchor not in m:
        print("V45_ERROR: cannot find <sepolicy> in the manifest"); sys.exit(1)
    m = m.replace(anchor, SUP_BLOCK + anchor, 1)
    open(SRCMAN, "w", encoding="utf-8", errors="surrogateescape").write(m)
    print("V45_MANIFEST_SRC_APPLIED")

shutil.copyfile(SRCMAN, DSTMAN)
print("V45_MANIFEST_COPIED -> device/samsung/gtexswifi/manifest.xml")
