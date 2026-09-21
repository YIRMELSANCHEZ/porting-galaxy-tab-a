#!/usr/bin/env python3
# V40 (phase 6.4c - boot blocker after V39): with the audio HAL now registered
# (audiohalservice: "Registration complete for android.hardware.audio@4.0::
# IDevicesFactory"), AudioFlinger constructs, but audioserver NOW crashes later on,
# en AudioPolicyService::onFirstRef -> AudioPolicyManager::initialize ->
# EngineBase::loadAudioPolicyEngineConfig -> VolumeGroup::addSupportedStream (null-deref,
# fault addr 0x68). Log clave:
#   E APM::Serializer: deserialize: libxml failed to resolve XIncludes on
#     /system/etc/audio_policy_configuration.xml document.
#   E APM::AudioPolicyEngine/Config: parseLegacyVolumeFile: libxml failed to resolve
#     XIncludes on document /system/etc/audio_policy_configuration.xml
# The audio_policy_configuration.xml uses <xi:include> to bring in 5 sub-files (tables of
# volume + a2dp/usb/r_submix configs), but NONE is installed (the device only
# I package the main file). libxml does not resolve the XInclude -> the volume groups
# end up EMPTY -> a stream references a null VolumeGroup -> null-deref -> audioserver
# dies -> does not publish media.audio_policy -> system_server hung on
# "Waiting for service 'media.audio_policy'". This is the last blocker before
# boot_completed.
#
# Fix: copy the 5 sub-files to /system/etc (same dir as the config; the XInclude are
# paths relative to the file that includes them). Only system.img changes; boot = V35.
# Cumulative over V36..V39. Idempotent.
import sys

DEVMK = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"

ANCHOR = (
    "    libeng-audio \\\n"
    "    libatchannel\n"
)
BLOCK = (
    "    libeng-audio \\\n"
    "    libatchannel\n"
    "\n"
    "# V40: sub-ficheros xi:include de audio_policy_configuration.xml (tablas de volumen y\n"
    "# configs a2dp/usb/r_submix). Sin ellos libxml no resuelve los XInclude -> volume\n"
    "# groups vacios -> AudioPolicyManager null-deref (VolumeGroup::addSupportedStream) ->\n"
    "# audioserver crashea -> no publica media.audio_policy -> system_server colgado.\n"
    "# Van a /system/etc (mismo dir que el config; los XInclude son rutas relativas).\n"
    "PRODUCT_COPY_FILES += \\\n"
    "    frameworks/av/services/audiopolicy/config/a2dp_audio_policy_configuration.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/a2dp_audio_policy_configuration.xml \\\n"
    "    frameworks/av/services/audiopolicy/config/usb_audio_policy_configuration.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/usb_audio_policy_configuration.xml \\\n"
    "    frameworks/av/services/audiopolicy/config/r_submix_audio_policy_configuration.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/r_submix_audio_policy_configuration.xml \\\n"
    "    frameworks/av/services/audiopolicy/config/audio_policy_volumes.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/audio_policy_volumes.xml \\\n"
    "    frameworks/av/services/audiopolicy/config/default_volume_tables.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/default_volume_tables.xml\n"
)

s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()

if "default_volume_tables.xml" in s:
    print("V40_ALREADY"); sys.exit(0)

if ANCHOR not in s:
    print("V40_ERROR: cannot find the libeng-audio/libatchannel anchor")
    sys.exit(1)

s = s.replace(ANCHOR, BLOCK, 1)
open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V40_APPLIED -> 5 xi:include de audio policy a /system/etc")
