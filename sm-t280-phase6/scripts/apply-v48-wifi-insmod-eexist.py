#!/usr/bin/env python3
# V48 (WiFi bring-up, step 5 - EEXIST on reloading the driver): with V47 the HAL now has all
# the caps and LOADS the driver (sprdwl in lsmod, wlan0 created). But the HAL startup
# still fails with:
#   android.hardware.wifi@1.0-service: finit_module return: -1: File exists
#   Failed to load WiFi driver -> Failed to start vendor HAL
# Cause: the module is already loaded (wlan0 exists) and the HAL tries insmod AGAIN ->
# finit_module devuelve EEXIST. En libwifi_hal, is_wifi_driver_loaded() devuelve 0 aunque
# the module is in /proc/modules (depends on the wlan.driver.status prop / the static
# is_driver_loaded bool, which do not reflect the real state after an enable/disable cycle or an rmmod
# that does not unload cleanly on this kernel 3.10). Result: wifi_load_driver() retries the
# insmod on an already-present module -> EEXIST -> -1 -> "Failed to load WiFi driver".
#
# Fix: in insmod() of frameworks/opt/net/wifi/libwifi_hal/wifi_hal_common.cpp, treat
# EEXIST (module already loaded) as SUCCESS (ret=0). It is the correct state: the driver is already
# operational (wlan0 up). libwifi_hal is a system.img lib; boot = V45 (unchanged).
# Cumulative over V47. Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/frameworks/opt/net/wifi/libwifi_hal/wifi_hal_common.cpp"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "errno == EEXIST" in s:
    print("V48_ALREADY"); sys.exit(0)

# 1) asegurar #include <errno.h>
if "#include <errno.h>" not in s:
    inc_old = "#include <fcntl.h>\n"
    if inc_old not in s:
        print("V48_ERROR: no encuentro #include <fcntl.h>"); sys.exit(1)
    s = s.replace(inc_old, inc_old + "#include <errno.h>\n", 1)

# 2) treat EEXIST as success in insmod()
OLD = (
    "  ret = syscall(__NR_finit_module, fd, args, 0);\n"
    "\n"
    "  close(fd);\n"
    "  if (ret < 0) {\n"
    "    PLOG(ERROR) << \"finit_module return: \" << ret;\n"
    "  }\n"
    "\n"
    "  return ret;\n"
)
NEW = (
    "  ret = syscall(__NR_finit_module, fd, args, 0);\n"
    "\n"
    "  close(fd);\n"
    "  if (ret < 0) {\n"
    "    if (errno == EEXIST) {\n"
    "      // Modulo ya cargado (kernel 3.10 sin rmmod limpio / ciclo enable-disable).\n"
    "      // El driver ya esta operativo (wlan0 up): tratar como exito.\n"
    "      ret = 0;\n"
    "    } else {\n"
    "      PLOG(ERROR) << \"finit_module return: \" << ret;\n"
    "    }\n"
    "  }\n"
    "\n"
    "  return ret;\n"
)
if OLD not in s:
    print("V48_ERROR: cannot find the expected insmod() body"); sys.exit(1)
s = s.replace(OLD, NEW, 1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V48_APPLIED -> insmod() treats EEXIST as success")
