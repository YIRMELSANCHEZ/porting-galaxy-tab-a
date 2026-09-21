#!/usr/bin/env python3
# V37 (phase 6.3 - framework restart-loop ROOT CAUSE): with hwservicemanager
# now stable (V36), system_server starts and advances to scanning packages
# (PackageManager), but CRASHES reproducibly in the "Jit thread pool" thread:
#   F libc: Fatal signal 11 (SIGSEGV), code 2 (SEGV_ACCERR), fault addr 0xa749c014
#           in tid NNNN (Jit thread pool), pid MMMM (system_server)
#   Zygote: Exit zygote because system server has terminated
# -> the whole zygote restarts in a loop (~every 5 s) and boot_completed is never reached.
#
# ART's JIT (Android 10) uses a dual RW/RX mapping of the code cache backed by
# memfd_create (kernel >= 3.17). This SoC runs kernel 3.10.108 -> no memfd_create ->
# the dual mapping fails and on EXECUTING the JIT code the page is not executable ->
# SEGV_ACCERR (code 2). It is the classic JIT failure on an old kernel.
#
# Standard bring-up fix: disable the JIT (dalvik.vm.usejit=false). ART falls back to
# interpreter + AOT code (dex2oat, file-backed .odex with PROT_EXEC, which DOES work on
# 3.10) and does not create the JIT thread or the dual cache -> no SEGV. Cost: slightly less
# performance; recovered when/if memfd_create is backported to the kernel.
#
# Wired in PRODUCT_PROPERTY_OVERRIDES (device.mk), the override bucket that wins over
# the default dalvik.vm.usejit=true of build/make/target/product/runtime_libart.mk.
# Change only in system.img (build.prop); boot = V35 (27c04393). Idempotent.
import sys

DEVMK = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"

OLD = (
    "PRODUCT_PROPERTY_OVERRIDES += \\\n"
    "    ro.adb.nonblocking_ffs=false \\\n"
    "    sys.usb.ffs.aio_compat=true\n"
)
NEW = (
    "PRODUCT_PROPERTY_OVERRIDES += \\\n"
    "    ro.adb.nonblocking_ffs=false \\\n"
    "    sys.usb.ffs.aio_compat=true \\\n"
    "    dalvik.vm.usejit=false \\\n"
    "    dalvik.vm.usejitprofiles=false\n"
)

s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()

if "dalvik.vm.usejit=false" in s:
    print("V37_ALREADY"); sys.exit(0)

if OLD not in s:
    print("V37_ERROR: cannot find the expected PRODUCT_PROPERTY_OVERRIDES V21 block")
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V37_APPLIED -> dalvik.vm.usejit=false en device.mk")
