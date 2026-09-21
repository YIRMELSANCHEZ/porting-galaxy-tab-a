#!/usr/bin/env python3
# V79 (APP: SwiftAngle, 2 failures measured in V78 with the target app):
#  1) GraphicsEnvironment.setupAngleRulesApk: "Failed to get AssetFileDescriptor for a4a_rules.json:
#     This file can not be opened as a file descriptor; it is probably compressed" -> setAngleInfo no
#     was called and the ANGLE driver did not load. Fixed in swiftangle/Android.mk (LOCAL_AAPT_FLAGS
#     := -0 .json); this script only re-copies the package to the device tree (apply-v78 does it).
#  2) With the rules loaded by debug.angle.rules, the libs load but SIGSEGV in
#     es2::getContextLocked() from gl::GetString (onMakeCurrent): libGLESv2 locates its libEGL by the
#     fixed name "libEGL_swiftshader.so" (OpenGL/libEGL/libEGL.hpp, __ANDROID__ branch), which does not exist
#     in the package -> egl::getCurrentContext() null. "libEGL_angle.so" is prepended (the same instance
#     already loaded by the framework in the ANGLE namespace). Symmetric to V78 for libGLESv2/libGLES_CM.
# Idempotente.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")
p = T / "external/swiftshader/src/OpenGL/libEGL/libEGL.hpp"
old = 'const char *libEGL_lib[] = {"libEGL_swiftshader.so", "libEGL_swiftshader.so"};'
new = 'const char *libEGL_lib[] = {"libEGL_angle.so", "libEGL_swiftshader.so"};   /* V79 */'
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V79" in s:
    print("libEGL/libEGL.hpp: already patched")
elif s.count(old) != 1:
    print("V79_ERROR: unexpected libEGL/libEGL.hpp block"); sys.exit(1)
else:
    p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
    print("libEGL/libEGL.hpp: libEGL_angle.so antepuesto")

mk = T / "device/samsung/gtexswifi/swiftangle/Android.mk"
if "-0 .json" not in mk.read_text(encoding="utf-8"):
    print("V79_ERROR: device tree Android.mk without LOCAL_AAPT_FLAGS (run apply-v78 first)"); sys.exit(1)
print("Android.mk: LOCAL_AAPT_FLAGS -0 .json presente")
print("V79_DONE")
