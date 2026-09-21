#!/usr/bin/env python3
"""Add the early Android hardware identity required by first-stage init."""
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
old = 'androidboot.selinux=permissive'
new = old + ' androidboot.hardware=sc8830'
if new not in text:
    if old not in text:
        raise SystemExit('expected kernel cmdline token not found')
    path.write_text(text.replace(old, new, 1))
print('FSTAB_CMDLINE_FIX_APPLIED')
