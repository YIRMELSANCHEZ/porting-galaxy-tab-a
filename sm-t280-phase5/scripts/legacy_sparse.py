#!/usr/bin/env python3
"""Convert an Android standard sparse file to Samsung's legacy padded headers.

The payload and chunk order remain byte-identical.  Only each sparse file/chunk
header gains its four-byte legacy padding, matching stock AQJ1 SYSTEM.
"""
import struct
import sys

MAGIC = 0xED26FF3A
FILE_HEADER = struct.Struct('<IHHHHIIII')
CHUNK_HEADER = struct.Struct('<HHII')


def main(src_name, dst_name):
    with open(src_name, 'rb') as src, open(dst_name, 'wb') as dst:
        raw = src.read(FILE_HEADER.size)
        if len(raw) != FILE_HEADER.size:
            raise SystemExit('truncated sparse file header')
        magic, major, minor, file_sz, chunk_sz, blk_sz, blocks, chunks, checksum = FILE_HEADER.unpack(raw)
        if magic != MAGIC or major != 1 or file_sz != FILE_HEADER.size or chunk_sz != CHUNK_HEADER.size:
            raise SystemExit('expected Android standard sparse v1 header (28/12)')
        dst.write(FILE_HEADER.pack(magic, major, minor, 32, 16, blk_sz, blocks, chunks, checksum))
        dst.write(b'\0' * 4)
        for index in range(chunks):
            raw = src.read(CHUNK_HEADER.size)
            if len(raw) != CHUNK_HEADER.size:
                raise SystemExit(f'truncated chunk header {index}')
            kind, reserved, out_blocks, total = CHUNK_HEADER.unpack(raw)
            if total < CHUNK_HEADER.size:
                raise SystemExit(f'invalid chunk size {index}')
            body_size = total - CHUNK_HEADER.size
            body = src.read(body_size)
            if len(body) != body_size:
                raise SystemExit(f'truncated chunk body {index}')
            dst.write(CHUNK_HEADER.pack(kind, reserved, out_blocks, total + 4))
            dst.write(b'\0' * 4)
            dst.write(body)
        if src.read(1):
            raise SystemExit('unexpected trailing bytes')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: legacy_sparse.py INPUT.img OUTPUT.img')
    main(sys.argv[1], sys.argv[2])
