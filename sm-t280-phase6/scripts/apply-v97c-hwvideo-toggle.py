#!/usr/bin/env python3
# V97c: (1) the V97b traces of the H.264 component become gated by persist.swiftangle.vtrace=1
# (silent by default); (2) switch persist.swiftangle.hwvideo (1 by default): with 0 the
# HW component fails initCheck and MediaCodec falls back to the next codec in the catalog (c2.android.avc,
# software), without reflashing. Requires V97b applied. Idempotent.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/hardware/sprd/omx-components/video/avc_sprd/sc8830/dec/SPRDAVCDecoder.cpp")
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V97c" in s:
    print("SPRDAVCDecoder.cpp: already patched"); print("V97C_DONE"); sys.exit(0)
if "V97_TRACE" not in s:
    print("V97C_ERROR: falta V97b"); sys.exit(1)

helper = """
// V97c: trazas y decodificador HW controlados por propiedades
static bool v97_trace() {
    static int c = -1;
    if (c < 0) { char v[PROPERTY_VALUE_MAX] = {}; c = (property_get("persist.swiftangle.vtrace", v, "0") > 0 && v[0] == '1') ? 1 : 0; }
    return c == 1;
}
static bool v97_hwEnabled() {
    char v[PROPERTY_VALUE_MAX] = {};
    return !(property_get("persist.swiftangle.hwvideo", v, "1") > 0 && v[0] == '0');
}
"""
# insert the helper before the component's first method definition
anchor = "SPRDAVCDecoder::SPRDAVCDecoder("
i = s.find(anchor)
if i < 0:
    print("V97C_ERROR: constructor"); sys.exit(1)
# go back to the start of the line
i = s.rfind("\n", 0, i) + 1
s = s[:i] + helper + "\n" + s[i:]

n = s.count('ALOGI("V97_TRACE')
s = s.replace('ALOGI("V97_TRACE', 'if (v97_trace()) ALOGI("V97_TRACE')
s = s.replace('{ lastLog = now; if (v97_trace()) ALOGI("V97_TRACE sin buffers', '{ lastLog = now; if (v97_trace()) ALOGI("V97_TRACE sin buffers')

old = "    uint8_t video_cfg = USE_HW_DECODER;\n"
new = "    uint8_t video_cfg = USE_HW_DECODER;\n    if (!v97_hwEnabled()) { ALOGI(\"V97c: decodificador HW desactivado por propiedad\"); mInitCheck = OMX_ErrorInsufficientResources; }\n"
if s.count(old) != 1:
    print("V97C_ERROR: video_cfg"); sys.exit(1)
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8", errors="surrogateescape")
print(f"SPRDAVCDecoder.cpp: {n} trazas condicionadas + interruptor hwvideo")
print("V97C_DONE")
