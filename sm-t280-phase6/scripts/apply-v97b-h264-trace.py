#!/usr/bin/env python3
# V97b (TEMPORARY, diagnostic): traces in the OMX H.264 HW component: input/output pts, output-port
# flush and "no output buffers". Marker V97_TRACE. To remove: git checkout the file
# or do not apply in the final build. Idempotent.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/hardware/sprd/omx-components/video/avc_sprd/sc8830/dec/SPRDAVCDecoder.cpp")
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V97_TRACE" in s:
    print("SPRDAVCDecoder.cpp: already patched"); print("V97B_DONE"); sys.exit(0)

def rep(s, old, new):
    if s.count(old) != 1:
        print(f"V97B_ERROR: anchor x{s.count(old)}: {old[:60]!r}"); sys.exit(1)
    return s.replace(old, new, 1)

s = rep(s, "    outHeader->nTimeStamp = (OMX_TICKS)pts;\n",
        "    outHeader->nTimeStamp = (OMX_TICKS)pts;\n    ALOGI(\"V97_TRACE out pts=%lld picId=%d\", (long long)pts, picId);\n")
s = rep(s, "void SPRDAVCDecoder::onPortFlushPrepare(OMX_U32 portIndex) {\n",
        "void SPRDAVCDecoder::onPortFlushPrepare(OMX_U32 portIndex) {\n    ALOGI(\"V97_TRACE flush port %u\", (unsigned)portIndex);\n")
s = rep(s, "    List<BufferInfo *> &inQueue = getPortQueue(kInputPortIndex);\n    List<BufferInfo *> &outQueue = getPortQueue(kOutputPortIndex);\n\n    while (!mStopDecode && (mEOSStatus != INPUT_DATA_AVAILABLE || !inQueue.empty())\n            && outQueue.size() != 0) {\n",
        "    List<BufferInfo *> &inQueue = getPortQueue(kInputPortIndex);\n    List<BufferInfo *> &outQueue = getPortQueue(kOutputPortIndex);\n\n"
        "    if (outQueue.size() == 0 && !inQueue.empty()) {   // V97_TRACE\n"
        "        static int64_t lastLog = 0; int64_t now = systemTime() / 1000000;\n"
        "        if (now - lastLog > 500) { lastLog = now; ALOGI(\"V97_TRACE sin buffers de salida (in=%zu)\", inQueue.size()); }\n"
        "    }\n\n"
        "    while (!mStopDecode && (mEOSStatus != INPUT_DATA_AVAILABLE || !inQueue.empty())\n            && outQueue.size() != 0) {\n")
s = rep(s, "        dec_in.nTimeStamp = (uint64)(inHeader->nTimeStamp);\n",
        "        dec_in.nTimeStamp = (uint64)(inHeader->nTimeStamp);\n        ALOGI(\"V97_TRACE in pts=%lld len=%u flags=0x%x ivop=%d\", (long long)inHeader->nTimeStamp, (unsigned)inHeader->nFilledLen, (unsigned)inHeader->nFlags, (int)mNeedIVOP);\n")
p.write_text(s, encoding="utf-8", errors="surrogateescape")
print("SPRDAVCDecoder.cpp: traces added")
print("V97B_DONE")
