#!/usr/bin/env python3
# V38 (phase 6.4 - boot blocker after breaking the JIT loop in V37): with the JIT
# disabled, system_server no longer crashes; it advances a lot (full PackageManager, 139
# apps, OverlayManager, sensors...) but stays HUNG in a loop:
#   W ServiceManagement: Waited one second for android.hardware.health@2.0::IHealth/default
#   I ServiceManagement: getService: Trying again ...
# system_server (BatteryService) and surfaceflinger wait FOREVER for the health HAL.
# dmesg: init: Could not find 'android.hardware.health@2.0::IHealth/default' for
# ctl.interface_start -> hwservicemanager asks init to start the HAL on demand, but
# NO init service declares it. The device only has the old 'healthd' (pid 214, reads
# the battery via sysfs OK) but Android 10 speaks over the binderized IHealth@2.0 HAL, not
# with healthd. Also the V36 manifest declares health@2.0/IHealth (hwbinder) but nothing
# provides it -> the clients wait for a service that does not exist.
#
# Fix: include the generic binderized service android.hardware.health@2.0-service
# (system/core/healthd, already compiled in the tree; class hal; overrides healthd). It uses
# libbatterymonitor, which autodetects /sys/class/power_supply (same sysfs as healthd
# current one reads fine) -> starts in 'on boot' (class_start hal), registers IHealth@2.0 ->
# system_server and surfaceflinger are unblocked. It has vendor:true -> installs in
# /system/vendor/bin/hw (on this device /vendor lives inside /system, without a partition
# its own vendor; that is why the V36 manifest went to system/vendor/etc/vintf). Goes in
# system.img; boot = V35. Idempotente.
import sys

DEVMK = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"

OLD = (
    "PRODUCT_PACKAGES += \\\n"
    "    libhealthd.sc8830 \\\n"
    "    power.sc8830\n"
)
NEW = (
    "PRODUCT_PACKAGES += \\\n"
    "    libhealthd.sc8830 \\\n"
    "    power.sc8830\n"
    "\n"
    "# V38: HAL binderizado de health (IHealth@2.0). Sin el, system_server (BatteryService)\n"
    "# y surfaceflinger se cuelgan esperando android.hardware.health@2.0::IHealth/default\n"
    "# (declarado en el manifiesto V36 pero no provisto). class hal -> arranca en boot y\n"
    "# registra IHealth; overrides el viejo healthd. Instala en /system/vendor/bin/hw.\n"
    "PRODUCT_PACKAGES += \\\n"
    "    android.hardware.health@2.0-service\n"
)

s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()

if "android.hardware.health@2.0-service" in s:
    print("V38_ALREADY"); sys.exit(0)

if OLD not in s:
    print("V38_ERROR: cannot find the expected libhealthd.sc8830/power.sc8830 block")
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V38_APPLIED -> android.hardware.health@2.0-service en PRODUCT_PACKAGES")
