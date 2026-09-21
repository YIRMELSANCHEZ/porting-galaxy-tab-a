#!/usr/bin/env python3
# V92b (CAM1). The blob libynoise.so (chain of camera.sc8830.so) has text relocations (TEXTREL)
# and the A10 linker rejects them for target SDK >= 23 (native daemons use __ANDROID_API__=29):
# 'dlopen failed: "/system/lib/libynoise.so" has text relocations' (measured live with the provider
# launched from /data/local/tmp). Minimal patch in bionic/linker/linker.cpp: they are allowed (with a warning)
# only when the process's main executable is a vendor HAL service
# (/vendor/bin/hw/ or /system/vendor/bin/hw/), which is where the 5.1 blobs live. Idempotent.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/bionic/linker/linker.cpp")
s = p.read_text(encoding="utf-8")
if "V92_TEXTREL" in s:
    print("linker.cpp: already patched"); print("V92B_DONE"); sys.exit(0)
old = '''  if (has_text_relocations) {
    // Fail if app is targeting M or above.
    int app_target_api_level = get_application_target_sdk_version();
    if (app_target_api_level >= __ANDROID_API_M__) {
'''
new = '''  if (has_text_relocations) {
    // Fail if app is targeting M or above.
    int app_target_api_level = get_application_target_sdk_version();
    // V92_TEXTREL: blobs 5.1 (p. ej. libynoise.so de la camara SPRD) cargados por servicios HAL de
    // vendor: se toleran las relocaciones de texto (solo aviso) en esos procesos.
    bool v92_vendor_hal = false;
    {
      soinfo* v92_main = solist_get_somain();
      const char* v92_exe = (v92_main != nullptr) ? v92_main->get_realpath() : nullptr;
      if (v92_exe != nullptr &&
          (strncmp(v92_exe, "/vendor/bin/hw/", 15) == 0 ||
           strncmp(v92_exe, "/system/vendor/bin/hw/", 22) == 0)) {
        v92_vendor_hal = true;
      }
    }
    if (app_target_api_level >= __ANDROID_API_M__ && !v92_vendor_hal) {
'''
if s.count(old) != 1:
    print(f"V92B_ERROR: unique block not found ({s.count(old)})"); sys.exit(1)
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("linker.cpp: TEXTREL tolerado en servicios HAL de vendor")
print("V92B_DONE")
