#!/usr/bin/env python3
"""V42: restore the Android 10 libion ABI on the legacy Spreadtrum implementation."""

import sys

path = "/home/lineage/android/lineage-17.1/hardware/sprd/libion_sprd/sc8830/ion.c"
text = open(path, encoding="utf-8", errors="surrogateescape").read()

anchor = "int ion_open()\n{\n"
addition = (
    "/*\n"
    " * Android 10 Codec2 probes this symbol before using the handle-based ION ABI.\n"
    " * SC8830 runs the legacy 3.10 ION driver and this library implements exactly\n"
    " * that ABI, so report it explicitly. Keep this exported for libcodec2_vndk.\n"
    " */\n"
    "int ion_is_legacy(int fd)\n"
    "{\n"
    "    (void)fd;\n"
    "    return 1;\n"
    "}\n\n"
)

if "int ion_is_legacy(int fd)" in text:
    print("V42_ION_ALREADY")
elif anchor not in text:
    print("V42_ERROR: ion_open anchor not found")
    sys.exit(1)
else:
    text = text.replace(anchor, addition + anchor, 1)
    open(path, "w", encoding="utf-8", errors="surrogateescape").write(text)
    print("V42_ION_APPLIED: legacy ION ABI exported")

