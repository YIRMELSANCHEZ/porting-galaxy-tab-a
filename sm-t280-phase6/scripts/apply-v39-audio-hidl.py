#!/usr/bin/env python3
# V39 (phase 6.4b - boot blocker after resolving health in V38): with IHealth now
# provisto, system_server avanza hasta muy tarde en startOtherServices (Network, Wifi,
# Connectivity, Notification, Location, Wallpaper...) but stays HUNG in a loop:
#   system_server: Waiting for service 'media.audio_policy' on '/dev/binder'...
# media.audio_policy is published by audioserver, but audioserver CRASHES in the constructor
# AudioFlinger::AudioFlinger() (null-deref) because it finds NO audio HAL:
#   hwservicemanager: getTransport: Cannot find entry
#     android.hardware.audio@5.0::IDevicesFactory/default in either framework or device
#     manifest (idem 4.0/2.0 y audio.effect)
# The device has the legacy HAL audio.primary.sc8830.so (/system/lib/hw) and audio_policy,
# but NOT the HIDL service that wraps it and registers IDevicesFactory. Without audioserver,
# AudioService (in system_server) waits for media.audio_policy forever -> no
# boot_completed. Now audio IS on the critical boot path.
#
# Fix: include the audio HIDL service (android.hardware.audio@2.0-service, from
# hardware/interfaces/audio/common/all-versions/default/service; class hal; vndbinder)
# which does registerPassthroughServiceImplementation of IDevicesFactory (tries 5.0->4.0
# ->2.0) and IEffectsFactory, loading via passthrough the impl libs
# android.hardware.audio@4.0-impl / android.hardware.audio.effect@4.0-impl, which in turn
# wrap the legacy HAL audio.primary.sc8830 via hw_get_module. They are declared in the
# manifiesto VINTF (audio@4.0 IDevicesFactory + audio.effect@4.0 IEffectsFactory,
# hwbinder). The service .rc declares the 4.0 and 2.0 interfaces.
#
# Everything installs in /vendor (proprietary) which on this device lives inside /system ->
# system.img; boot = V35. Cumulative over V36+V37+V38. Idempotent.
import sys, shutil

DEVDIR = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi"
DEVMK = DEVDIR + "/device.mk"
SRCMAN = "/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts/gtexswifi-manifest.xml"
DSTMAN = DEVDIR + "/manifest.xml"

# --- 1) PRODUCT_PACKAGES: servicio HIDL de audio + impls passthrough (audio + effect) ---
OLD = (
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.health@2.0-service\n"
)
NEW = (
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.health@2.0-service\n"
    "\n"
    "# V39: servicio HIDL de audio (envuelve la HAL legacy audio.primary.sc8830 via\n"
    "# passthrough) + impls audio/effect. Sin el, audioserver null-deref en AudioFlinger()\n"
    "# (no encuentra IDevicesFactory) -> no publica media.audio_policy -> system_server se\n"
    "# cuelga esperandolo. Instala en /system/vendor (vendor vive en system).\n"
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.audio@2.0-service \\\n"
    "    android.hardware.audio@4.0-impl \\\n"
    "    android.hardware.audio.effect@4.0-impl\n"
)

s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()
if "android.hardware.audio@2.0-service" in s:
    print("V39_DEVMK_ALREADY")
else:
    if OLD not in s:
        print("V39_ERROR: cannot find the expected health@2.0-service (V38) block")
        sys.exit(1)
    s = s.replace(OLD, NEW, 1)
    open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("V39_DEVMK_APPLIED -> audio@2.0-service + audio/effect @4.0-impl")

# --- 2) manifiesto VINTF: audio@4.0 IDevicesFactory + audio.effect@4.0 IEffectsFactory ---
m = open(SRCMAN, encoding="utf-8", errors="surrogateescape").read()
AUDIO_BLOCK = (
    "    <hal format=\"hidl\">\n"
    "        <name>android.hardware.audio</name>\n"
    "        <transport>hwbinder</transport>\n"
    "        <version>4.0</version>\n"
    "        <interface>\n"
    "            <name>IDevicesFactory</name>\n"
    "            <instance>default</instance>\n"
    "        </interface>\n"
    "    </hal>\n"
    "    <hal format=\"hidl\">\n"
    "        <name>android.hardware.audio.effect</name>\n"
    "        <transport>hwbinder</transport>\n"
    "        <version>4.0</version>\n"
    "        <interface>\n"
    "            <name>IEffectsFactory</name>\n"
    "            <instance>default</instance>\n"
    "        </interface>\n"
    "    </hal>\n"
)
if "android.hardware.audio</name>" in m:
    print("V39_MANIFEST_ALREADY")
else:
    anchor = "    <sepolicy>"
    if anchor not in m:
        print("V39_ERROR: cannot find <sepolicy> in the manifest")
        sys.exit(1)
    m = m.replace(anchor, AUDIO_BLOCK + anchor, 1)
    open(SRCMAN, "w", encoding="utf-8", errors="surrogateescape").write(m)
    print("V39_MANIFEST_SRC_APPLIED")

# --- 3) copy the source manifest to the device tree (as V36 does) ---
shutil.copyfile(SRCMAN, DSTMAN)
print("V39_MANIFEST_COPIED -> device/samsung/gtexswifi/manifest.xml")
