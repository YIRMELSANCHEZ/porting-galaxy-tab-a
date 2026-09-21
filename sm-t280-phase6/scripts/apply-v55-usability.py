#!/usr/bin/env python3
# V55 (usabilidad/estabilidad, solo system.img; boot = V53 dd2d8154):
#  1) POWER BUTTON (wake from sleep): keylayout/sci-keypad.kl had `key 116 POWER`
#     WITHOUT the WAKE flag (HOME 172 does have it). WAKE is added -> POWER wakes the tablet.
#     Instala en /system/usr/keylayout.
#  2) SOFTWARE VIDEO: the SPRD HW video codecs (OMX.sprd.* via SprdOMXPlugin) are
#     Android 5.1 blobs (GCC 4.9), ABI-incompatible with Android 10 stagefright -> crash
#     in makeComponentInstance (RefBase::decStrong) every time an app requests a HW codec. The
#     configs/media/media_codecs.xml is replaced with a SOFTWARE-ONLY version (Google/AOSP
#     includes; no OMX.sprd.*; without the nonexistent <Include media_codecs_ffmpeg.xml>).
#     Without OMX.sprd entries, the framework never invokes SprdOMXPlugin -> no crash; video/audio
#     via software (OMX.google.*/c2.android.*). Installs in /system/etc.
#  3) low_ram: system.prop had ro.config.low_ram=false (conflict with phase3.mk=true).
#     Set to true (correct for 1.5GB RAM).
# The GPU (Mali-400 GLES2) and audio already worked via HW. Idempotent.
import sys, shutil

ROOT = "/home/lineage/android/lineage-17.1"
KL = ROOT + "/device/samsung/gtexswifi/keylayout/sci-keypad.kl"
MC = ROOT + "/device/samsung/gtexswifi/configs/media/media_codecs.xml"
SP = ROOT + "/device/samsung/gtexswifi/system.prop"
MC_SRC = "/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts/media_codecs-software.xml"

# 1) POWER WAKE
k = open(KL, encoding="utf-8", errors="surrogateescape").read()
if "key 116   POWER          WAKE" in k or "key 116 POWER WAKE" in k.replace("   "," ").replace("  "," "):
    print("V55_KL_ALREADY")
elif "key 116   POWER" in k:
    k = k.replace("key 116   POWER\n", "key 116   POWER          WAKE\n", 1)
    open(KL, "w", encoding="utf-8", errors="surrogateescape").write(k)
    print("V55_KL_APPLIED -> POWER WAKE")
else:
    print("V55_KL_WARN: no encuentro 'key 116   POWER'")

# 2) media_codecs solo software
if "OMX.sprd" not in open(MC, encoding="utf-8", errors="surrogateescape").read().split("-->")[-1]:
    print("V55_MC_ALREADY")
else:
    shutil.copyfile(MC_SRC, MC)
    print("V55_MC_APPLIED -> media_codecs solo software")

# 3) low_ram
s = open(SP, encoding="utf-8", errors="surrogateescape").read()
if "ro.config.low_ram=false" in s:
    s = s.replace("ro.config.low_ram=false", "ro.config.low_ram=true", 1)
    open(SP, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("V55_SP_APPLIED -> low_ram=true")
else:
    print("V55_SP_ALREADY")
