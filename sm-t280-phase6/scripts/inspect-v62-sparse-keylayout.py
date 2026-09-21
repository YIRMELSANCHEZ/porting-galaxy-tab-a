#!/usr/bin/env python3
"""Inspect POWER/HOME key-layout strings stored in Android sparse RAW chunks."""

from __future__ import annotations

import mmap
import struct
import sys


SPARSE_MAGIC = 0xED26FF3A
FILE_HEADER = struct.Struct("<IHHHHIIII")
CHUNK_HEADER = struct.Struct("<HHII")
CHUNK_RAW = 0xCAC1


def main(path: str) -> None:
    with open(path, "rb") as stream:
        header = FILE_HEADER.unpack(stream.read(FILE_HEADER.size))
        magic, major, _minor, file_hdr_sz, chunk_hdr_sz, block_sz, _blocks, chunks, _crc = header
        if (magic, major) != (SPARSE_MAGIC, 1):
            raise SystemExit("not an Android sparse v1 image")
        stream.seek(file_hdr_sz)

        hits = 0
        for chunk_index in range(chunks):
            chunk_start = stream.tell()
            kind, _reserved, out_blocks, total_sz = CHUNK_HEADER.unpack(stream.read(CHUNK_HEADER.size))
            stream.seek(chunk_start + chunk_hdr_sz)
            body_sz = total_sz - chunk_hdr_sz
            if kind == CHUNK_RAW:
                if body_sz != out_blocks * block_sz:
                    raise SystemExit(f"invalid RAW chunk {chunk_index}")
                body = stream.read(body_sz)
                needle = b"key 116"
                pos = 0
                while True:
                    pos = body.find(needle, pos)
                    if pos < 0:
                        break
                    lo = body.rfind(b"\n", max(0, pos - 300), pos)
                    hi = body.find(b"\x00", pos, min(len(body), pos + 2000))
                    if hi < 0:
                        hi = min(len(body), pos + 500)
                    snippet = body[lo + 1 : hi]
                    print(f"chunk={chunk_index} file_offset={chunk_start + chunk_hdr_sz + pos}")
                    print(snippet.decode("utf-8", "backslashreplace"))
                    print("---")
                    hits += 1
                    pos += len(needle)
            else:
                stream.seek(body_sz, 1)

        print(f"key_116_hits={hits}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect-v62-sparse-keylayout.py SYSTEM_IMG")
    main(sys.argv[1])
