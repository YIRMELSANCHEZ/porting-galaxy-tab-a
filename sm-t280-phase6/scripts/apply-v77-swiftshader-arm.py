#!/usr/bin/env python3
# V77 (APP: software GLES 3.0 layer for apps that require it). Step 1: compile SwiftShader
# (external/swiftshader, a CPU OpenGL ES 3.0 renderer that AOSP uses in the emulator) for
# armeabi-v7a. Without this patch it does not compile on ARM: it carries -msse2 (x86) in all cflags and its
# eglGetPlatformDisplay returns EGL_BAD_PARAMETER on Android (the framework libEGL uses it when
# it loads a driver via the "ANGLE" path).
#
# CONTEXT (results/phase-6/TODO-ANALYSIS.md, APP section): "an app that requires GLES 3.0" requires
# <uses-feature glEsVersion=0x30000> (demonstrated with spoof profiles in Aurora); the SM-T280's Mali-400 is
# GLES 2.0. Plan: an "ANGLE" system package with libEGL_angle.so/libGLESv2_angle.so
# = renamed SwiftShader, enabled ONLY for that app via Settings.Global
# angle_gl_driver_selection_pkgs/values (mecanismo estandar de Android 10, GraphicsEnvironment).
#
# Changes (idempotent):
#  1) -msse2 -> only if TARGET_ARCH is x86/x86_64 (Android.mk of src, compiler, libGLES_CM,
#     libGLESv2, llvm-7.0, LLVM) y en Android.bp (cc_defaults swiftshader_common -> arch x86).
#  2) libEGL.cpp GetPlatformDisplay: on Android, accept any platform with
#     native_display == EGL_DEFAULT_DISPLAY (devuelve PRIMARY_DISPLAY) en vez de EGL_BAD_PARAMETER.
import re, sys
from pathlib import Path

ROOT = Path("/home/lineage/android/lineage-17.1/external/swiftshader")
MK_FILES = ["src/Android.mk", "src/OpenGL/compiler/Android.mk", "src/OpenGL/libGLES_CM/Android.mk",
            "src/OpenGL/libGLESv2/Android.mk", "third_party/llvm-7.0/Android.mk", "third_party/LLVM/Android.mk"]
GUARD = "$(if $(filter x86 x86_64,$(TARGET_ARCH)),-msse2)"

changed = 0
for rel in MK_FILES:
    p = ROOT / rel
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "-msse2" not in s:
        print(f"{rel}: no -msse2 (already patched or not applicable)"); continue
    n = s.replace("-msse2", GUARD)
    p.write_text(n, encoding="utf-8", errors="surrogateescape"); changed += 1
    print(f"{rel}: -msse2 condicionado ({s.count('-msse2')} ocurrencias)")

bp = ROOT / "Android.bp"
s = bp.read_text(encoding="utf-8", errors="surrogateescape")
if '        "-msse2",\n' in s:
    s = s.replace('        "-msse2",\n', "", 1)
    s = s.replace("    target: {\n        host: {", "    arch: {\n        x86: { cflags: [\"-msse2\"] },\n        x86_64: { cflags: [\"-msse2\"] },\n    },\n\n    target: {\n        host: {", 1)
    bp.write_text(s, encoding="utf-8", errors="surrogateescape"); changed += 1
    print("Android.bp: -msse2 movido a arch x86/x86_64")
else:
    print("Android.bp: already patched")

egl = ROOT / "src/OpenGL/libEGL/libEGL.cpp"
s = egl.read_text(encoding="utf-8", errors="surrogateescape")
OLD = """		return success(PRIMARY_DISPLAY);   // We only support the default display
	#else
		return error(EGL_BAD_PARAMETER, EGL_NO_DISPLAY);
	#endif
}
"""
NEW = """		return success(PRIMARY_DISPLAY);   // We only support the default display
	#else
		/* V77 (gtexswifi): el libEGL del framework Android carga este driver por la ruta
		 * "ANGLE" y pide eglGetPlatformDisplay(EGL_PLATFORM_ANGLE_ANGLE, EGL_DEFAULT_DISPLAY, attrs).
		 * Solo hay un display: aceptarlo. */
		if(native_display == (void*)EGL_DEFAULT_DISPLAY)
		{
			return success(PRIMARY_DISPLAY);
		}
		return error(EGL_BAD_PARAMETER, EGL_NO_DISPLAY);
	#endif
}
"""
if "V77 (gtexswifi)" in s:
    print("libEGL.cpp: already patched")
elif s.count(OLD) == 1:
    egl.write_text(s.replace(OLD, NEW, 1), encoding="utf-8", errors="surrogateescape"); changed += 1
    print("libEGL.cpp: GetPlatformDisplay acepta EGL_DEFAULT_DISPLAY en Android")
else:
    print("V77_ERROR: unexpected GetPlatformDisplay block"); sys.exit(1)

print(f"V77_DONE ({changed} ficheros)")
