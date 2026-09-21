#!/usr/bin/env python3
# V91b (APP, performance). The V88 scale (persist.swiftangle.scale=2) requests 640x400 buffers with
# native_window_set_buffers_dimensions but SurfaceFlinger rejects them: "rejecting buffer:
# bufWidth=640, bufHeight=400, front.active_legacy.{w=1280, h=800}" (measured with the V90 test APK).
# With the default scaling mode (FREEZE) the layer requires buffers of the window's size; you must
# set NATIVE_WINDOW_SCALING_MODE_SCALE_TO_WINDOW so SF enlarges the reduced buffer.
# Idempotent; requires V88 applied.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src/OpenGL/libEGL/Surface.cpp")
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V91b" in s:
    print("Surface.cpp: already patched (V91b)"); print("V91B_DONE"); sys.exit(0)
old = "\t\t\t(void)native_window_set_buffers_dimensions(window, windowWidth, windowHeight);\n"
new = old + ("\t\t\t// V91b: sin SCALE_TO_WINDOW SurfaceFlinger rechaza buffers menores que la capa\n"
             "\t\t\t(void)native_window_set_scaling_mode(window, NATIVE_WINDOW_SCALING_MODE_SCALE_TO_WINDOW);\n")
if s.count(old) != 1:
    print(f"V91B_ERROR: anchor V88 no unico ({s.count(old)})"); sys.exit(1)
p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
print("Surface.cpp: SCALE_TO_WINDOW tras set_buffers_dimensions")
print("V91B_DONE")
