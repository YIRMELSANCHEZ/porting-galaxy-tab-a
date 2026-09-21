#!/usr/bin/env python3
"""Read-only ELF inventory using only the Python standard library."""

from __future__ import annotations

import csv
import hashlib
import struct
import sys
from pathlib import Path


MACHINES = {3: "x86", 8: "MIPS", 40: "ARM", 62: "x86_64", 183: "AArch64"}


def cstring(data: bytes, offset: int) -> str:
    if offset < 0 or offset >= len(data):
        return ""
    return data[offset : data.find(b"\0", offset) if b"\0" in data[offset:] else len(data)].decode(
        "utf-8", "replace"
    )


def inspect(path: Path) -> dict[str, str] | None:
    data = path.read_bytes()
    if len(data) < 52 or data[:4] != b"\x7fELF":
        return None
    elf_class, encoding = data[4], data[5]
    endian = "<" if encoding == 1 else ">"
    machine = struct.unpack_from(endian + "H", data, 18)[0]
    needed: list[str] = []
    soname = ""
    if elf_class == 1:
        shoff = struct.unpack_from(endian + "I", data, 32)[0]
        shentsize, shnum = struct.unpack_from(endian + "HH", data, 46)
        sections = []
        if shoff and shentsize >= 40 and shoff + shentsize * shnum <= len(data):
            for index in range(shnum):
                values = struct.unpack_from(endian + "IIIIIIIIII", data, shoff + index * shentsize)
                sections.append(values)
            for section in sections:
                _, sh_type, _, _, offset, size, link, _, _, entsize = section
                if sh_type != 6 or link >= len(sections):
                    continue
                strtab = sections[link]
                strings = data[strtab[4] : strtab[4] + strtab[5]]
                step = entsize or 8
                for pos in range(offset, min(offset + size, len(data)), step):
                    if pos + 8 > len(data):
                        break
                    tag, value = struct.unpack_from(endian + "II", data, pos)
                    if tag == 1:
                        needed.append(cstring(strings, value))
                    elif tag == 14:
                        soname = cstring(strings, value)
    return {
        "path": str(path),
        "class": {1: "ELF32", 2: "ELF64"}.get(elf_class, str(elf_class)),
        "machine": MACHINES.get(machine, str(machine)),
        "endian": {1: "little", 2: "big"}.get(encoding, str(encoding)),
        "soname": soname,
        "needed": ";".join(sorted(set(filter(None, needed)))),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": str(len(data)),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: inspect_elf.py ROOT OUTPUT.csv", file=sys.stderr)
        return 2
    root, output = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        row = inspect(path)
        if row:
            row["path"] = path.relative_to(root).as_posix()
            rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "class", "machine", "endian", "soname", "needed", "sha256", "size"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"ELF files: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
