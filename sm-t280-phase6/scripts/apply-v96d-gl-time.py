#!/usr/bin/env python3
# V96d (stats): total time inside each labeled GL entry (including waits) and inside
# eglSwapBuffers, to separate CPU of the render thread in SwiftShader vs in Unity. Gated by
# persist.swiftangle.stats=1 like the rest. Requires V96. Idempotent.
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")

def rep(s, old, new, count=1):
    if s.count(old) != count:
        raise RuntimeError(f"anchor x{s.count(old)} != {count}: {old[:70]!r}")
    return s.replace(old, new)

h = SW / "Common/V95Stats.hpp"
s = h.read_text(encoding="utf-8", errors="surrogateescape")
if "V96d" not in s:
    s = rep(s, "struct V95TagEntry { const char *tag; long n; long us; };\n",
            "struct V95TagEntry { const char *tag; long n; long us; long calls; long tot_us; };   // V96d\n")
    s = rep(s, "void v95_account_wait(long us);\n", "void v95_account_wait(long us);\nvoid v95_account_call(const char *tag, long us);\n")
    s = rep(s, "struct V95Tag { const char *old; V95Tag(const char *t) { old = v95_tag; v95_tag = t; } ~V95Tag() { v95_tag = old; } };\n",
            "struct V95Tag { const char *old; const char *tag; long t0; V95Tag(const char *t) { old = v95_tag; v95_tag = t; tag = t; t0 = v95_now_us(); } ~V95Tag() { v95_account_call(tag, v95_now_us() - t0); v95_tag = old; } };\n")
    h.write_text(s, encoding="utf-8", errors="surrogateescape"); print("V95Stats.hpp: patched")

r = SW / "Common/Resource.cpp"
s = r.read_text(encoding="utf-8", errors="surrogateescape")
if "V96d" not in s:
    s = rep(s, "\tvoid v95_account_wait(long us)\n",
            "\tvoid v95_account_call(const char *tag, long us)   // V96d\n"
            "\t{\n"
            "\t\tfor(int i = 0; i < 12; i++)\n"
            "\t\t{\n"
            "\t\t\tif(v95_tags[i].tag == tag || v95_tags[i].tag == nullptr)\n"
            "\t\t\t{\n"
            "\t\t\t\tv95_tags[i].tag = tag; v95_tags[i].calls++; v95_tags[i].tot_us += us;\n"
            "\t\t\t\treturn;\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n\n"
            "\tvoid v95_account_wait(long us)\n")
    r.write_text(s, encoding="utf-8", errors="surrogateescape"); print("Resource.cpp: patched")

c = SW / "Renderer/Renderer.cpp"
s = c.read_text(encoding="utf-8", errors="surrogateescape")
if "V96d" not in s:
    old = "p += snprintf(tags + p, sizeof(tags) - p, \" %s=%ld/%ldms\", v95_tags[i].tag, v95_tags[i].n, v95_tags[i].us / 1000); v95_tags[i].n = 0; v95_tags[i].us = 0; }\n"
    new = "p += snprintf(tags + p, sizeof(tags) - p, \" %s=%ld/%ldms(calls %ld, in %ldms)\", v95_tags[i].tag, v95_tags[i].n, v95_tags[i].us / 1000, v95_tags[i].calls, v95_tags[i].tot_us / 1000); v95_tags[i].n = 0; v95_tags[i].us = 0; v95_tags[i].calls = 0; v95_tags[i].tot_us = 0; }   // V96d\n"
    s = rep(s, old, new)
    c.write_text(s, encoding="utf-8", errors="surrogateescape"); print("Renderer.cpp: patched")

e = SW / "OpenGL/libEGL/Surface.cpp"
s = e.read_text(encoding="utf-8", errors="surrogateescape")
if "V96d" not in s:
    s = rep(s, "void WindowSurface::swap()\n{\n\t{   // V95_STATS\n\t\tstatic long v95_last = 0, v95_frames = 0;\n",
            "static long v96d_swap_us = 0, v96d_swap_t0 = 0;   // V96d\nvoid WindowSurface::swap()\n{\n\tv96d_swap_t0 = v95s_now_us();\n\t{   // V95_STATS\n\t\tstatic long v95_last = 0, v95_frames = 0;\n")
    s = rep(s, "\"per %ld ms: frames=%ld fence_polls_blocking=%ld fence_poll_ms=%ld clientwaits=%ld\",\n\t\t\t                    (now - v95_last) / 1000, v95_frames, v95e_polls, v95e_poll_us / 1000, v95e_cwaits);\n\t\t\tv95_frames = v95e_polls = v95e_poll_us = v95e_cwaits = 0;\n",
            "\"per %ld ms: frames=%ld fence_polls_blocking=%ld fence_poll_ms=%ld clientwaits=%ld swap_ms=%ld\",\n\t\t\t                    (now - v95_last) / 1000, v95_frames, v95e_polls, v95e_poll_us / 1000, v95e_cwaits, v96d_swap_us / 1000);\n\t\t\tv95_frames = v95e_polls = v95e_poll_us = v95e_cwaits = 0; v96d_swap_us = 0;\n")
    # measure the swap body: appending at the end of the function (before the close) is fragile; use an RAII guard
    s = rep(s, "\tv96d_swap_t0 = v95s_now_us();\n", "\tstruct V96dGuard { ~V96dGuard() { v96d_swap_us += v95s_now_us() - v96d_swap_t0; } } v96dguard;\n\tv96d_swap_t0 = v95s_now_us();\n")
    e.write_text(s, encoding="utf-8", errors="surrogateescape"); print("libEGL/Surface.cpp: patched")
print("V96D_DONE")
