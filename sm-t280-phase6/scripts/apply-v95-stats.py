#!/usr/bin/env python3
# V95_STATS (test APK only, temporary instrumentation): counters aggregated every 2 s in logcat.
#   V95_STATS (libGLESv2): draws, blocking waits in sw::Resource::lock and their time, Renderer::synchronize
#                          and their time, Surface::clearDepth and their time.
#   V95_EGL   (libEGL):    frames (swap), eglGetSyncAttrib(STATUS) queries that block and their time,
#                          blocking eglClientWaitSync.
# Idempotent. Removed with git checkout / not included in Odin packages.
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")
MARK = "V95_STATS"

def patch(path, fn):
    s = path.read_text(encoding="utf-8", errors="surrogateescape")
    if MARK in s:
        print(f"{path.name}: already patched"); return
    s2 = fn(s)
    if s2 is None:
        print(f"V95_ERROR: {path.name}"); sys.exit(1)
    path.write_text(s2, encoding="utf-8", errors="surrogateescape")
    print(f"{path.name}: patched")

hdr = SW / "Common/V95Stats.hpp"
hdr.write_text("""// V95_STATS: contadores temporales de sincronizacion (solo APK de prueba)
#ifndef V95_STATS_HPP
#define V95_STATS_HPP
#include <time.h>
namespace sw {
extern long v95_draws, v95_waits, v95_wait_us, v95_syncs, v95_sync_us, v95_clears, v95_clear_us;
inline long v95_now_us() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000000L + t.tv_nsec / 1000; }
struct V95Timer { long t0; long *acc; V95Timer(long *a) : t0(v95_now_us()), acc(a) {} ~V95Timer() { *acc += v95_now_us() - t0; } };
}
#endif
""")

def resource(s):
    old_inc = '#include "Debug.hpp"\n'
    new_inc = old_inc + '#include "V95Stats.hpp"   // V95_STATS\n'
    old_ns = "namespace sw\n{\n"
    new_ns = old_ns + "\tlong v95_draws = 0, v95_waits = 0, v95_wait_us = 0, v95_syncs = 0, v95_sync_us = 0, v95_clears = 0, v95_clear_us = 0;\n"
    old_w = "\t\t\tunblock.wait();\n"
    new_w = "\t\t\t{ V95Timer v95t(&v95_wait_us); v95_waits++; unblock.wait(); }\n"
    if s.count(old_inc) != 1 or s.count(old_ns) != 1 or s.count(old_w) != 2:
        return None
    return s.replace(old_inc, new_inc, 1).replace(old_ns, new_ns, 1).replace(old_w, new_w)

def renderer(s):
    old_inc = '#include "Common/Debug.hpp"\n'
    new_inc = old_inc + '#include "Common/V95Stats.hpp"   // V95_STATS\n#if defined(__ANDROID__) && defined(__BIONIC__)\n#include <android/log.h>\n#else\n#define __android_log_print(...) ((void)0)\n#endif\n'
    old_draw = "\tvoid Renderer::draw(DrawType drawType, unsigned int indexOffset, unsigned int count, bool update)\n\t{\n"
    new_draw = old_draw + """\t\t{   // V95_STATS: volcado cada 2 s
\t\t\tstatic long v95_last = 0;
\t\t\tv95_draws++;
\t\t\tlong now = v95_now_us();
\t\t\tif(v95_last == 0) v95_last = now;
\t\t\tif(now - v95_last >= 2000000L)
\t\t\t{
\t\t\t\t__android_log_print(ANDROID_LOG_INFO, "V95_STATS", "per %ld ms: draws=%ld waits=%ld wait_ms=%ld syncs=%ld sync_ms=%ld clears=%ld clear_ms=%ld",
\t\t\t\t                    (now - v95_last) / 1000, v95_draws, v95_waits, v95_wait_us / 1000, v95_syncs, v95_sync_us / 1000, v95_clears, v95_clear_us / 1000);
\t\t\t\tv95_draws = v95_waits = v95_wait_us = v95_syncs = v95_sync_us = v95_clears = v95_clear_us = 0;
\t\t\t\tv95_last = now;
\t\t\t}
\t\t}
"""
    old_sync = "\tvoid Renderer::synchronize()\n\t{\n\t\tsync->lock(sw::PUBLIC);\n"
    new_sync = "\tvoid Renderer::synchronize()\n\t{\n\t\tV95Timer v95t(&v95_sync_us); v95_syncs++;   // V95_STATS\n\t\tsync->lock(sw::PUBLIC);\n"
    if s.count(old_inc) != 1 or s.count(old_draw) != 1 or s.count(old_sync) != 1:
        return None
    return s.replace(old_inc, new_inc, 1).replace(old_draw, new_draw, 1).replace(old_sync, new_sync, 1)

def surface(s):
    old_inc = '#include "Common/Debug.hpp"\n'
    new_inc = old_inc + '#include "Common/V95Stats.hpp"   // V95_STATS\n'
    old_cd = "\tvoid Surface::clearDepth(float depth, int x0, int y0, int width, int height)\n\t{\n"
    new_cd = old_cd + "\t\tV95Timer v95t(&v95_clear_us); v95_clears++;   // V95_STATS\n"
    if s.count(old_inc) != 1 or s.count(old_cd) != 1:
        return None
    return s.replace(old_inc, new_inc, 1).replace(old_cd, new_cd, 1)

def libegl(s):
    old_inc = '#include "Common/Version.h"\n'
    new_inc = old_inc + """#include <time.h>   // V95_STATS
#if defined(__ANDROID__) && defined(__BIONIC__)
#include <android/log.h>
#else
#define __android_log_print(...) ((void)0)
#endif
long v95e_polls = 0, v95e_poll_us = 0, v95e_cwaits = 0;
static inline long v95e_now_us() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000000L + t.tv_nsec / 1000; }
"""
    old_cw = "\tif(!eglSync->isSignaled())\n\t{\n\t\teglSync->wait();\n\t}\n\n\treturn success(EGL_CONDITION_SATISFIED_KHR);\n"
    new_cw = "\tif(!eglSync->isSignaled())\n\t{\n\t\tv95e_cwaits++;   // V95_STATS\n\t\teglSync->wait();\n\t}\n\n\treturn success(EGL_CONDITION_SATISFIED_KHR);\n"
    old_ga = "\t\teglSync->wait();   // TODO: Don't block. Just poll based on sw::Query.\n"
    new_ga = "\t\t{ long t0 = v95e_now_us(); if(!eglSync->isSignaled()) v95e_polls++; eglSync->wait(); v95e_poll_us += v95e_now_us() - t0; }   // V95_STATS (TODO: Don't block)\n"
    if s.count(old_inc) != 1 or s.count(old_cw) != 1 or s.count(old_ga) != 1:
        return None
    return s.replace(old_inc, new_inc, 1).replace(old_cw, new_cw, 1).replace(old_ga, new_ga, 1)

def eglsurface(s):
    old_inc = '#include "Main/FrameBuffer.hpp"\n'
    new_inc = old_inc + """#include <time.h>   // V95_STATS
#if defined(__ANDROID__) && defined(__BIONIC__)
#include <android/log.h>
#else
#define __android_log_print(...) ((void)0)
#endif
extern long v95e_polls, v95e_poll_us, v95e_cwaits;
static inline long v95s_now_us() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000000L + t.tv_nsec / 1000; }
"""
    old_sw = "void WindowSurface::swap()\n{\n"
    new_sw = old_sw + """\t{   // V95_STATS
\t\tstatic long v95_last = 0, v95_frames = 0;
\t\tv95_frames++;
\t\tlong now = v95s_now_us();
\t\tif(v95_last == 0) v95_last = now;
\t\tif(now - v95_last >= 2000000L)
\t\t{
\t\t\t__android_log_print(ANDROID_LOG_INFO, "V95_EGL", "per %ld ms: frames=%ld fence_polls_blocking=%ld fence_poll_ms=%ld clientwaits=%ld",
\t\t\t                    (now - v95_last) / 1000, v95_frames, v95e_polls, v95e_poll_us / 1000, v95e_cwaits);
\t\t\tv95_frames = v95e_polls = v95e_poll_us = v95e_cwaits = 0;
\t\t\tv95_last = now;
\t\t}
\t}
"""
    if s.count(old_inc) != 1 or s.count(old_sw) != 1:
        return None
    return s.replace(old_inc, new_inc, 1).replace(old_sw, new_sw, 1)

patch(SW / "Common/Resource.cpp", resource)
patch(SW / "Renderer/Renderer.cpp", renderer)
patch(SW / "Renderer/Surface.cpp", surface)
patch(SW / "OpenGL/libEGL/libEGL.cpp", libegl)
patch(SW / "OpenGL/libEGL/Surface.cpp", eglsurface)
print("V95_DONE")
