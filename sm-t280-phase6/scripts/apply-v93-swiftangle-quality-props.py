#!/usr/bin/env python3
# V93 (APP, performance/quality): (1) persist.swiftangle.scale accepts fractional values
# (e.g. 2.5 -> 512x320) to find a middle ground between scale 2 (sharp, 560 ms/frame)
# and 3 (smooth, 292 ms/frame); (2) the SwiftShader quality settings (SwiftShader.ini, which on
# Android is never read: cwd "/") become settable via properties:
#   persist.swiftangle.texq   0 point / 1 linear / 2 anisotropic (defecto)
#   persist.swiftangle.mipq   0 point / 1 linear (defecto)
#   persist.swiftangle.persp  0 without perspective correction / 1 (default)
#   persist.swiftangle.transc 0 approximate / 1 partial / 2 accurate (defecto) / 3 whql / 4 ieee
#   persist.swiftangle.threads number of render threads (default: the process affinity)
# Idempotent; requires V88 and V91b applied.
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")

h = SW / "OpenGL/libEGL/Surface.hpp"
s = h.read_text(encoding="utf-8", errors="surrogateescape")
if "V93_FRAC_SCALE" not in s:
    old = "\tint requestedBufferScale = 1;\n"
    if s.count(old) != 1:
        print("V93_ERROR: Surface.hpp without V88"); sys.exit(1)
    s = s.replace(old, "\tfloat requestedBufferScale = 1.0f;   // V93_FRAC_SCALE\n", 1)
    h.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("Surface.hpp: float scale")
else:
    print("Surface.hpp: already patched (V93)")

p = SW / "OpenGL/libEGL/Surface.cpp"
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V93" not in s:
    old_ctor = '''\tconst int scale = atoi(scaleValue);
\tif(scale >= 2 && scale <= 4 && nativeWindowWidth / scale >= 320 && nativeWindowHeight / scale >= 200)
\t{
\t\trequestedBufferScale = scale;
\t}
'''
    new_ctor = '''\t// V93: escala fraccionaria (1 < escala <= 4), p. ej. 2.5 -> 512x320
\tconst float scale = (float)atof(scaleValue);
\tif(scale > 1.0f && scale <= 4.0f && (int)(nativeWindowWidth / scale) >= 320 && (int)(nativeWindowHeight / scale) >= 200)
\t{
\t\trequestedBufferScale = scale;
\t}
'''
    if s.count(old_ctor) != 1:
        print("V93_ERROR: V88 constructor not found"); sys.exit(1)
    s = s.replace(old_ctor, new_ctor, 1)
    old_rs = '''\t\t\twindowWidth = nativeWindowWidth / requestedBufferScale;
\t\t\twindowHeight = nativeWindowHeight / requestedBufferScale;
'''
    new_rs = '''\t\t\twindowWidth = ((int)(nativeWindowWidth / requestedBufferScale)) & ~1;    // V93: par
\t\t\twindowHeight = ((int)(nativeWindowHeight / requestedBufferScale)) & ~1;
'''
    if s.count(old_rs) != 1:
        print("V93_ERROR: checkForResize V88 not found"); sys.exit(1)
    s = s.replace(old_rs, new_rs, 1)
    if "#include <stdlib.h>" not in s:
        s = s.replace("#include <cutils/properties.h>", "#include <cutils/properties.h>\n#include <stdlib.h>   // V93 atof", 1)
    p.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("Surface.cpp: fractional scale")
else:
    print("Surface.cpp: already patched (V93)")

c = SW / "Main/SwiftConfig.cpp"
s = c.read_text(encoding="utf-8", errors="surrogateescape")
if "V93_QUALITY_PROPS" not in s:
    old_inc = '#include "Common/Version.h"\n'
    new_inc = old_inc + '''#if defined(__ANDROID__) && defined(__BIONIC__)
#include <cutils/properties.h>   // V93_QUALITY_PROPS
#include <stdlib.h>
#endif
'''
    if s.count(old_inc) != 1:
        print("V93_ERROR: includes SwiftConfig.cpp"); sys.exit(1)
    s = s.replace(old_inc, new_inc, 1)
    old = '\t\tconfig.enableSSE4_1 = ini.getBoolean("Processor", "EnableSSE4_1", true);\n'
    new = old + '''
\t\t#if defined(__ANDROID__) && defined(__BIONIC__)
\t\t// V93_QUALITY_PROPS: en Android SwiftShader.ini no existe; las propiedades mandan.
\t\t{
\t\t\tchar v[PROPERTY_VALUE_MAX] = {};
\t\t\tif(property_get("persist.swiftangle.texq", v, "") > 0)    config.textureSampleQuality = atoi(v);
\t\t\tif(property_get("persist.swiftangle.mipq", v, "") > 0)    config.mipmapQuality = atoi(v);
\t\t\tif(property_get("persist.swiftangle.persp", v, "") > 0)   config.perspectiveCorrection = (atoi(v) != 0);
\t\t\tif(property_get("persist.swiftangle.transc", v, "") > 0)  config.transcendentalPrecision = atoi(v);
\t\t\tif(property_get("persist.swiftangle.threads", v, "") > 0) config.threadCount = atoi(v);
\t\t}
\t\t#endif
'''
    if s.count(old) != 1:
        print("V93_ERROR: readConfiguration"); sys.exit(1)
    s = s.replace(old, new, 1)
    c.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("SwiftConfig.cpp: quality via properties")
else:
    print("SwiftConfig.cpp: already patched (V93)")
print("V93_DONE")
