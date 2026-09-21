#!/usr/bin/env python3
"""Fix the Android 10 host checkvintf loop ignoring its compatibility result.

This changes only the host validation utility source. It is not installed in
the device image.
"""

from pathlib import Path


path = Path("/home/lineage/android/lineage-17.1/system/libvintf/check_vintf.cpp")
data = path.read_text(encoding="utf-8")
old = """            int compat = checkAllFiles(rootdir, properties, &error);
            std::cerr << "Debug: files under " << rootdir
                      << (compat == COMPATIBLE
                              ? " is compatible"
                              : compat == INCOMPATIBLE ? " are incompatible"
                                                       : (" has encountered an error: " + error))
                      << std::endl;
"""
new = """            int compat = checkAllFiles(rootdir, properties, &error);
            std::cerr << "Debug: files under " << rootdir
                      << (compat == COMPATIBLE
                              ? " is compatible"
                              : compat == INCOMPATIBLE ? (" are incompatible: " + error)
                                                       : (" has encountered an error: " + error))
                      << std::endl;
            if (compat != COMPATIBLE) ret = compat;
"""

if new in data:
    print("CHECKVINTF_HOST_RESULT_FIX_ALREADY_PRESENT")
elif old in data:
    path.write_text(data.replace(old, new, 1), encoding="utf-8")
    print("CHECKVINTF_HOST_RESULT_FIX_APPLIED")
else:
    raise SystemExit("CHECKVINTF_HOST_RESULT_FIX_ANCHOR_NOT_FOUND")
