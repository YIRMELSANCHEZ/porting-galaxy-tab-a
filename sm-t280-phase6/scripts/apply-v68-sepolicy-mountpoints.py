#!/usr/bin/env python3
"""Add the V68 system-as-root labels required by e2fsdroid."""

from pathlib import Path


path = Path("/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/sepolicy/file_contexts")
data = path.read_text(encoding="utf-8", errors="surrogateescape")
labels = """\n# V68 system-as-root additions\n/productinfo(/.*)?  u:object_r:efs_file:s0\n/file_contexts\\.bin  u:object_r:file_contexts_file:s0\n"""

if "/productinfo(/.*)?" not in data:
    path.write_text(data.rstrip() + labels, encoding="utf-8", errors="surrogateescape")
    print("V68_SEPOLICY_MOUNTPOINTS_PATCHED")
else:
    normalized = data.replace("\n+/efs(/.*)?", "\n/efs(/.*)?")
    normalized = normalized.replace("\n+/productinfo(/.*)?", "\n/productinfo(/.*)?")
    # /efs is already labelled by system/sepolicy/private/file_contexts.
    normalized = normalized.replace("\n/efs(/.*)?          u:object_r:efs_file:s0", "")
    normalized = "\n".join(line for line in normalized.splitlines() if line != "+") + "\n"
    if "/file_contexts\\.bin" not in normalized:
        normalized += "/file_contexts\\.bin  u:object_r:file_contexts_file:s0\n"
    if normalized != data:
        path.write_text(normalized, encoding="utf-8", errors="surrogateescape")
        print("V68_SEPOLICY_MOUNTPOINTS_NORMALIZED")
    else:
        print("V68_SEPOLICY_MOUNTPOINTS_ALREADY_PRESENT")
