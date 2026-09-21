#!/usr/bin/env python3
# V41 (phase 6.4d - FINAL BLOCKER before boot_completed): with audio resolved (V40),
# system_server reaches the END of the boot -> StartSystemUI, PhaseThirdPartyApps
# CanStart, ActivityManagerService.systemReady... but DIES with a fatal exception:
#   FATAL EXCEPTION IN SYSTEM PROCESS: main
#   RuntimeException: Failed to boot service TrustManagerService: onBootPhase threw an
#     exception during phase 600
#   Caused by: NullPointerException: ...IKeystoreService.onKeyguardVisibilityChanged()
#     on a null object reference
# IKeystoreService is NULL because keystore CRASHES (SIGABRT) on every attempt:
#   F keystore: keystore_main.cpp:141] Check failed:
#     kmDevices[SecurityLevel::TRUSTED_ENVIRONMENT] Error no viable keymaster device found
# keystore requires a Keymaster HAL that reports TRUSTED_ENVIRONMENT (TEE). The device does NOT
# have keymaster wired (no Trusty/SPRD in the tree). Without keystore -> IKeystoreService
# null -> system_server muere en systemReady -> NO hay boot_completed.
#
# Bring-up fix (without a functional TEE): use android.hardware.keymaster@4.0-service (AOSP
# SOFTWARE impl) but making it present itself as TRUSTED_ENVIRONMENT, so that
# keystore accepts its CHECK. It is NOT a real TEE (reduced security: keys backed by
# software, not hardware); it is reversible if one day the Trusty keymaster is wired
# Spreadtrum. Changes:
#   1) hardware/interfaces/keymaster/4.0/default/service.cpp: CreateKeymasterDevice(
#      SecurityLevel::SOFTWARE) -> (SecurityLevel::TRUSTED_ENVIRONMENT).
#   2) PRODUCT_PACKAGES += android.hardware.keymaster@4.0-service (class early_hal;
#      registra IKeymasterDevice/default; instala en /system/vendor/bin/hw).
#   3) manifiesto VINTF += keymaster@4.0 IKeymasterDevice (hwbinder).
# Only system.img changes; boot = V35. Cumulative over V36..V40. Idempotent.
import sys, shutil

ROOT = "/home/lineage/android/lineage-17.1"
SVC = ROOT + "/hardware/interfaces/keymaster/4.0/default/service.cpp"
DEVMK = ROOT + "/device/samsung/gtexswifi/device.mk"
SRCMAN = "/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts/gtexswifi-manifest.xml"
DSTMAN = ROOT + "/device/samsung/gtexswifi/manifest.xml"

# --- 1) service.cpp: SOFTWARE -> TRUSTED_ENVIRONMENT ---
c = open(SVC, encoding="utf-8", errors="surrogateescape").read()
OLD_C = "CreateKeymasterDevice(SecurityLevel::SOFTWARE)"
NEW_C = "CreateKeymasterDevice(SecurityLevel::TRUSTED_ENVIRONMENT)"
if NEW_C in c:
    print("V41_SVC_ALREADY")
elif OLD_C not in c:
    print("V41_ERROR: no encuentro CreateKeymasterDevice(SecurityLevel::SOFTWARE)")
    sys.exit(1)
else:
    c = c.replace(OLD_C, NEW_C, 1)
    open(SVC, "w", encoding="utf-8", errors="surrogateescape").write(c)
    print("V41_SVC_APPLIED -> software keymaster presents itself as TRUSTED_ENVIRONMENT")

# --- 2) PRODUCT_PACKAGES += android.hardware.keymaster@4.0-service ---
s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()
OLD_MK = (
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.audio@2.0-service \\\n"
    "    android.hardware.audio@4.0-impl \\\n"
    "    android.hardware.audio.effect@4.0-impl\n"
)
NEW_MK = (
    OLD_MK
    + "\n"
    "# V41: HAL de keymaster (impl software presentada como TRUSTED_ENVIRONMENT). Sin un\n"
    "# keymaster que reporte TEE, keystore aborta (Check failed) -> IKeystoreService null\n"
    "# -> system_server muere en systemReady (TrustManagerService NPE). Instala en\n"
    "# /system/vendor/bin/hw.\n"
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.keymaster@4.0-service\n"
)
if "android.hardware.keymaster@4.0-service" in s:
    print("V41_DEVMK_ALREADY")
elif OLD_MK not in s:
    print("V41_ERROR: cannot find the expected audio@2.0-service (V39) block")
    sys.exit(1)
else:
    s = s.replace(OLD_MK, NEW_MK, 1)
    open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("V41_DEVMK_APPLIED -> android.hardware.keymaster@4.0-service")

# --- 3) manifiesto VINTF += keymaster@4.0 IKeymasterDevice ---
m = open(SRCMAN, encoding="utf-8", errors="surrogateescape").read()
KM_BLOCK = (
    "    <hal format=\"hidl\">\n"
    "        <name>android.hardware.keymaster</name>\n"
    "        <transport>hwbinder</transport>\n"
    "        <version>4.0</version>\n"
    "        <interface>\n"
    "            <name>IKeymasterDevice</name>\n"
    "            <instance>default</instance>\n"
    "        </interface>\n"
    "    </hal>\n"
)
if "android.hardware.keymaster</name>" in m:
    print("V41_MANIFEST_ALREADY")
else:
    anchor = "    <sepolicy>"
    if anchor not in m:
        print("V41_ERROR: cannot find <sepolicy> in the manifest"); sys.exit(1)
    m = m.replace(anchor, KM_BLOCK + anchor, 1)
    open(SRCMAN, "w", encoding="utf-8", errors="surrogateescape").write(m)
    print("V41_MANIFEST_SRC_APPLIED")

shutil.copyfile(SRCMAN, DSTMAN)
print("V41_MANIFEST_COPIED -> device/samsung/gtexswifi/manifest.xml")
