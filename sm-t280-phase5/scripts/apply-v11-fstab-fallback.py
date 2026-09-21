#!/usr/bin/env python3
# V11: fstab fallback in fs_mgr for gtexswifi.
# The Spreadtrum bootloader does not pass androidboot.hardware and the device does not expose
# /proc/device-tree, so neither ReadFstabFromDt() nor GetFstabPath() (which depends
# on ro.hardware) find the fstab in first-stage. A fallback is added that
# uses the device's known fstab (sc8830). Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/system/core/fs_mgr/fs_mgr_fstab.cpp"
MARK = "gtexswifi: fallback de fstab"

FALLBACK = (
    "\n"
    "    // " + MARK + " (bootloader ignora el cmdline; sin /proc/device-tree).\n"
    "    for (const char* prefix : {\"/odm/etc/fstab.\", \"/vendor/etc/fstab.\", \"/fstab.\"}) {\n"
    "        std::string fstab_path = std::string(prefix) + \"sc8830\";\n"
    "        if (access(fstab_path.c_str(), F_OK) == 0) {\n"
    "            return fstab_path;\n"
    "        }\n"
    "    }\n"
)

with open(SRC, "r", encoding="utf-8") as f:
    lines = f.readlines()

if any(MARK in l for l in lines):
    print("V11_PATCH_ALREADY_PRESENT")
    sys.exit(0)

# Locate GetFstabPath and its final 'return "";'.
start = None
for i, l in enumerate(lines):
    if "std::string GetFstabPath()" in l:
        start = i
        break
if start is None:
    print("ERROR: could not find GetFstabPath()", file=sys.stderr)
    sys.exit(2)

ret_idx = None
for j in range(start + 1, len(lines)):
    if lines[j].strip() == 'return "";':
        ret_idx = j
        break
if ret_idx is None:
    print("ERROR: could not find the final return of GetFstabPath()", file=sys.stderr)
    sys.exit(2)

lines.insert(ret_idx, FALLBACK)

with open(SRC, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("V11_PATCH_APPLIED")
