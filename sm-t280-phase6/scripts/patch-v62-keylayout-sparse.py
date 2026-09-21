#!/usr/bin/env python3
"""Patch the invalid WAKE flags in sci-keypad.kl inside a sparse system image.

The replacement is byte-for-byte the same length, so the ext4 inode, SELinux
xattr, permissions, sparse layout and every unrelated byte stay unchanged.
"""

from __future__ import annotations

import argparse
import mmap
import shutil
import struct
import sys


SPARSE_MAGIC = 0xED26FF3A
FILE_HEADER = struct.Struct("<IHHHHIIII")
CHUNK_HEADER = struct.Struct("<HHII")
CHUNK_RAW = 0xCAC1

BAD = (
    b"key 116   POWER          WAKE\n"
    b"key 114   VOLUME_DOWN\n"
    b"key 115   VOLUME_UP\n"
    b"key 9     CAMERA\n"
    b"key 172   HOME          WAKE\n"
)
GOOD = (
    b"key 116   POWER              \n"
    b"key 114   VOLUME_DOWN\n"
    b"key 115   VOLUME_UP\n"
    b"key 9     CAMERA\n"
    b"key 172   HOME              \n"
)

if len(BAD) != len(GOOD):
    raise RuntimeError("V62 replacement must preserve the file length")


def raw_ranges(stream) -> list[tuple[int, int]]:
    header_data = stream.read(FILE_HEADER.size)
    if len(header_data) != FILE_HEADER.size:
        raise SystemExit("truncated sparse header")
    magic, major, _minor, file_hdr_sz, chunk_hdr_sz, block_sz, _blocks, chunks, _crc = FILE_HEADER.unpack(header_data)
    if (magic, major) != (SPARSE_MAGIC, 1):
        raise SystemExit("not an Android sparse v1 image")
    if file_hdr_sz < FILE_HEADER.size or chunk_hdr_sz < CHUNK_HEADER.size:
        raise SystemExit("invalid sparse header sizes")

    ranges: list[tuple[int, int]] = []
    stream.seek(file_hdr_sz)
    for index in range(chunks):
        start = stream.tell()
        chunk_data = stream.read(CHUNK_HEADER.size)
        if len(chunk_data) != CHUNK_HEADER.size:
            raise SystemExit(f"truncated sparse chunk {index}")
        kind, _reserved, out_blocks, total_sz = CHUNK_HEADER.unpack(chunk_data)
        body_start = start + chunk_hdr_sz
        body_size = total_sz - chunk_hdr_sz
        if body_size < 0:
            raise SystemExit(f"invalid sparse chunk size {index}")
        if kind == CHUNK_RAW:
            if body_size != out_blocks * block_sz:
                raise SystemExit(f"invalid RAW chunk body {index}")
            ranges.append((body_start, body_start + body_size))
        stream.seek(start + total_sz)
    return ranges


def find_all(data, needle: bytes) -> list[int]:
    hits: list[int] = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            return hits
        hits.append(pos)
        pos += len(needle)


def verify_or_patch(path: str, patch: bool) -> None:
    mode = "r+b" if patch else "rb"
    with open(path, mode) as stream:
        ranges = raw_ranges(stream)
        access = mmap.ACCESS_WRITE if patch else mmap.ACCESS_READ
        with mmap.mmap(stream.fileno(), 0, access=access) as data:
            bad_hits = find_all(data, BAD)
            good_hits = find_all(data, GOOD)

            if patch:
                if len(bad_hits) != 1 or good_hits:
                    raise SystemExit(
                        f"expected exactly one bad layout and no patched layout; "
                        f"bad={len(bad_hits)} good={len(good_hits)}"
                    )
                offset = bad_hits[0]
                if not any(start <= offset and offset + len(BAD) <= end for start, end in ranges):
                    raise SystemExit("key-layout bytes are not wholly inside a sparse RAW chunk")
                data[offset : offset + len(BAD)] = GOOD
                data.flush()
                print(f"patched_offset={offset}")
            else:
                if bad_hits or len(good_hits) != 1:
                    raise SystemExit(
                        f"V62 verification failed: bad={len(bad_hits)} good={len(good_hits)}"
                    )
                offset = good_hits[0]
                if not any(start <= offset and offset + len(GOOD) <= end for start, end in ranges):
                    raise SystemExit("patched key-layout bytes are not wholly inside a sparse RAW chunk")
                print(f"verified_offset={offset}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        if args.output:
            parser.error("--verify accepts only one image")
        verify_or_patch(args.source, patch=False)
        print("V62_SPARSE_KEYLAYOUT_VERIFY_PASS")
        return

    if not args.output:
        parser.error("patch mode requires SOURCE and OUTPUT")
    shutil.copyfile(args.source, args.output)
    verify_or_patch(args.output, patch=True)
    verify_or_patch(args.output, patch=False)
    print("V62_SPARSE_KEYLAYOUT_PATCH_PASS")


if __name__ == "__main__":
    main()
