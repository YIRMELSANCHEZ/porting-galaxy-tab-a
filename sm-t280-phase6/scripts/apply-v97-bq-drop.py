#!/usr/bin/env python3
# V97 (VID3, "frozen" video in the app): Unity plays the video in a SurfaceTexture. A SurfaceTexture's
# buffer queue is SYNCHRONOUS: the producer (MediaCodec, Unity's video thread) blocks
# when there is no free buffer, and the consumer (updateTexImage on the render thread) only frees one per
# rendered frame (6 fps). The decoder is throttled to 6 fps, the video timestamps
# lag behind the audio clock and Unity resyncs with a seek every ~1 s (measured: 162
# recreations of the AAC decoder and 162 flushes of the H.264 decoder in 170 s of video):
# imagen congelada y audio a saltos.
# Fix: in libgui, the buffers queued to a "SurfaceTexture*" consumer are droppable
# (async-mode behavior): queueBuffer replaces the pending frame instead of accumulating, the
# producer never blocks, the consumer always receives the latest frame and the video clock follows
# the audio one. Switch: persist.swiftangle.bqdrop (1 by default). Idempotent.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/frameworks/native/libs/gui/BufferQueueProducer.cpp")
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V97" in s:
    print("BufferQueueProducer.cpp: already patched"); print("V97_DONE"); sys.exit(0)

def rep(s, old, new):
    if s.count(old) != 1:
        print(f"V97_ERROR: anchor x{s.count(old)}: {old[:60]!r}"); sys.exit(1)
    return s.replace(old, new, 1)

s = rep(s, "#include <utils/Log.h>\n",
        "#include <utils/Log.h>\n#include <cutils/properties.h>   // V97\n#include <string.h>\n\n"
        "// V97: buffers descartables hacia consumidores SurfaceTexture (persist.swiftangle.bqdrop, 1 por defecto)\n"
        "static bool v97_surfaceTextureDrop(const android::String8 &consumerName) {\n"
        "    static int enabled = -1;\n"
        "    if (enabled < 0) {\n"
        "        char v[PROPERTY_VALUE_MAX] = {};\n"
        "        enabled = (property_get(\"persist.swiftangle.bqdrop\", v, \"1\") > 0 && v[0] != '0') ? 1 : 0;\n"
        "    }\n"
        "    return enabled == 1 && consumerName.size() >= 14 &&\n"
        "           strncmp(consumerName.string(), \"SurfaceTexture\", 14) == 0;\n"
        "}\n")
s = rep(s, "        item.mIsDroppable = mCore->mAsyncMode ||\n                (mConsumerIsSurfaceFlinger && mCore->mQueueBufferCanDrop) ||\n",
        "        item.mIsDroppable = mCore->mAsyncMode ||\n                v97_surfaceTextureDrop(mConsumerName) ||   // V97\n                (mConsumerIsSurfaceFlinger && mCore->mQueueBufferCanDrop) ||\n")
p.write_text(s, encoding="utf-8", errors="surrogateescape")
print("BufferQueueProducer.cpp: patched")
print("V97_DONE")
