#!/usr/bin/env python3
# V96b: fixes the V96 deferred clear. The fill ran in the PRIMITIVES stage, which in
# SwiftShader overlaps with the PIXELS tasks of the previous draws (per-stage pipelining) -> a race
# on the framebuffer (leftovers from previous frames, e.g. the splash video over the app). Now the
# clear runs in the PIXELS stage, per cluster, filling only the rows that cluster owns
# (same split as the rasterizer: (y >> 1) % clusterCount == cluster), so it respects the order
# with the previous and following draws. Requires V96 applied. Idempotent.
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")

def rep(s, old, new, count=1):
    if s.count(old) != count:
        raise RuntimeError(f"anchor x{s.count(old)} != {count}: {old[:70]!r}")
    return s.replace(old, new)

h = SW / "Renderer/Renderer.hpp"
s = h.read_text(encoding="utf-8", errors="surrogateescape")
if "V96b" not in s:
    s = rep(s, "\t\tvoid performClear(DrawCall *draw);\n", "\t\tvoid performClear(DrawCall *draw, int cluster);   // V96b\n")
    h.write_text(s, encoding="utf-8", errors="surrogateescape"); print("Renderer.hpp: patched")
else:
    print("Renderer.hpp: already patched")

c = SW / "Renderer/Renderer.cpp"
s = c.read_text(encoding="utf-8", errors="surrogateescape")
if "V96b" not in s:
    # PRIMITIVES: do not fill here; mark visible so there are PIXELS tasks
    s = rep(s, ("\t\t\t\t\tif(clearDraw->isClear)\n\t\t\t\t\t{\n\t\t\t\t\t\tperformClear(clearDraw);\n"
                "\t\t\t\t\t\tprimitiveProgress[unit].visible = 0;\n"),
               ("\t\t\t\t\tif(clearDraw->isClear)\n\t\t\t\t\t{\n\t\t\t\t\t\t// V96b: el relleno se hace en PIXELS por cluster\n"
                "\t\t\t\t\t\tprimitiveProgress[unit].visible = 1;\n"))
    # PIXELS: per-cluster fill instead of the pixel routine
    s = rep(s, "\t\t\t\t\tpixelRoutine(primitive, visible, cluster, data);\n",
               "\t\t\t\t\tif(draw->isClear)   // V96b\n\t\t\t\t\t{\n\t\t\t\t\t\tperformClear(draw, cluster);\n\t\t\t\t\t}\n\t\t\t\t\telse\n\t\t\t\t\t{\n\t\t\t\t\t\tpixelRoutine(primitive, visible, cluster, data);\n\t\t\t\t\t}\n")
    s = rep(s, "\tvoid Renderer::performClear(DrawCall *draw)\n\t{\n",
               "\tvoid Renderer::performClear(DrawCall *draw, int cluster)   // V96b: solo las filas del cluster\n\t{\n\t\tconst int cc = clusterCount;\n")
    # color
    s = rep(s, ("\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t{\n\t\t\t\t\tif(draw->clearBytes == 2)\n"),
               ("\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t{\n\t\t\t\t\tif(((y >> 1) % cc) != cluster) { d += data->colorPitchB[0]; continue; }\n\t\t\t\t\tif(draw->clearBytes == 2)\n"))
    # depth without quad layout
    s = rep(s, ("\t\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t\t{\n\t\t\t\t\t\tv96_fill4(row, (int&)depth, width * sizeof(float));\n\t\t\t\t\t\trow += pitchP;\n"),
               ("\t\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t\t{\n\t\t\t\t\t\tif(((y >> 1) % cc) != cluster) { row += pitchP; continue; }\n\t\t\t\t\t\tv96_fill4(row, (int&)depth, width * sizeof(float));\n\t\t\t\t\t\trow += pitchP;\n"))
    # depth quad layout
    s = rep(s, ("\t\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t\t{\n\t\t\t\t\t\tfloat *target = buffer + (y & ~1) * pitchP + (y & 1) * 2;\n"),
               ("\t\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t\t{\n\t\t\t\t\t\tif(((y >> 1) % cc) != cluster) continue;\n\t\t\t\t\t\tfloat *target = buffer + (y & ~1) * pitchP + (y & 1) * 2;\n"))
    # stencil
    s = rep(s, ("\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t{\n\t\t\t\t\tchar *target = buffer + (y & ~1) * pitchP + (y & 1) * 2;\n"),
               ("\t\t\t\tfor(int y = y0; y < y1; y++)\n\t\t\t\t{\n\t\t\t\t\tif(((y >> 1) % cc) != cluster) continue;\n\t\t\t\t\tchar *target = buffer + (y & ~1) * pitchP + (y & 1) * 2;\n"))
    c.write_text(s, encoding="utf-8", errors="surrogateescape"); print("Renderer.cpp: patched")
else:
    print("Renderer.cpp: already patched")
print("V96B_DONE")
