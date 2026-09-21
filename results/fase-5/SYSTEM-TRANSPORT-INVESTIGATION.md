# SYSTEM transport investigation

## Restored baseline

The exact AQJ1 `boot.img` plus `system.img` subset was accepted by Odin and
Android 5.1.1 booted normally. This validates the cable/session, the SYSTEM
partition and the stock firmware recovery path.

## Controlled failed candidates

V1 (standard sparse), V2 (raw ext4), V3 (shrunk raw ext4) and V4 (DHTB-wrapped
raw ext4) all reached `system.img` and then failed in Odin. Therefore a generic
capacity or USB-transfer cause is not supported by the evidence.

## Stock format delta

The stock AQJ1 system is an Android sparse image with `file_hdr_sz=32` and
`chunk_hdr_sz=16`. The Android 10 build is valid standard sparse, but has
`file_hdr_sz=28` and `chunk_hdr_sz=12`. Stock's extra four bytes on the file and
each chunk header are legacy padding expected by this generation's downloader.

V5 converts only those sparse headers and their declared header sizes. It does
not alter the ext4 payload, chunk order, output block count (524288 x 4096), or
the tested boot image.

## Candidate

- Package: `SM-T280-system-android10-legacy-sparse-PHASE5-v5-DO-NOT-FLASH.tar.md5`
- Package SHA-256: `79e0399aa4b5f15a627723cb0918dd46bf215b2531c3aca579020f61999d2f67`
- Archive contents: exactly `boot.img`, then `system.img`.
- Status: offline validated; not flashed.
