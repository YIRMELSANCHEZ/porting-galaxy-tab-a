#!/usr/bin/env python3
# V84 (VIDEO + APP). Two system.img changes:
#  1) mediaswcodec (software video decoders, Codec2) dies with SIGSEGV in
#     C2AllocatorGralloc::Impl::newGraphicAllocation when playing any video (the target app, browser
#     videos): it first logs "vndksupport: Could not load /vendor/lib/hw/
#     android.hardware.graphics.mapper@2.0-impl.so from sphal namespace: library
#     android.hardware.graphics.mapper@2.0.so not found". The APEX com.android.media.swcodec carries its
#     its own ld.config.txt (frameworks/av/apex/ld.config.txt) whose sphal namespace looks for the
#     VNDK-SP libs in /system/lib/vndk-sp29, which does not exist in this legacy build (ro.vndk.lite=true, libs in
#     /system/lib). /system/${LIB} is added to the sphal search path (the already-loaded LLNDK are reused
#     via the link to platform; the rest is loaded as a private copy of the namespace, same as
#     namespace vndk en dispositivos treble).
#  2) debug.angle.backend=1 in build.prop: the framework (Loader.cpp) assumes a Vulkan backend for an
#     ANGLE package and then does NOT connect the ANativeWindow or set the format in
#     eglCreateWindowSurface (the Vulkan swapchain would do it); with SwiftShader (GL) the dequeueBuffer
#     failed with "BufferQueue has no connected producer" and the app did not queue frames.
# Idempotente.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")

p = T / "frameworks/av/apex/ld.config.txt"
s = p.read_text(encoding="utf-8")
old = "namespace.sphal.search.paths += /system/${LIB}/vndk-sp${VNDK_VER}\n"
if "V84" in s:
    print("apex/ld.config.txt: already patched")
elif s.count(old) != 1:
    print("V84_ERROR: unexpected apex/ld.config.txt block"); sys.exit(1)
else:
    s = s.replace(old, old + "# V84 (gtexswifi, vndk-lite legacy): las libs VNDK-SP estan en /system/lib, no en vndk-sp29\n"
                  "namespace.sphal.search.paths += /system/${LIB}\n", 1)
    p.write_text(s, encoding="utf-8")
    print("apex/ld.config.txt: sphal also searches in /system/lib")

mk = T / "device/samsung/gtexswifi/device.mk"
s = mk.read_text(encoding="utf-8", errors="surrogateescape")
if "debug.angle.backend" not in s:
    s += ("\n# V84: backend GL para el paquete ANGLE (SwiftAngle); con el valor por defecto (Vulkan) el\n"
          "# framework no conecta la ventana en eglCreateWindowSurface y no se encolan frames\n"
          "PRODUCT_PROPERTY_OVERRIDES += debug.angle.backend=1\n")
    mk.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("device.mk: debug.angle.backend=1")
else:
    print("device.mk: already has debug.angle.backend")
print("V84_DONE")
