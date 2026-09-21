#!/usr/bin/env bash
# Read-only validation of the rebuilt legacy boot ramdisk.
set -euo pipefail

boot=${1:?Usage: verify-boot-ramdisk.sh BOOT_IMG}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

test "$(dd if="$boot" bs=1 count=4 status=none)" = DHTB
offset=$(grep -aob 'ANDROID!' "$boot" | head -1 | cut -d: -f1)
test "$offset" = 512
python3 - "$boot" "$work/ramdisk.meta" <<'PY'
import struct, sys
image, output = sys.argv[1:]
with open(image, 'rb') as f:
    f.seek(512)
    v = struct.unpack('<8s10I16s512s8I', f.read(608))
assert v[0] == b'ANDROID!'
page, kernel, ramdisk = v[8], v[1], v[3]
start = 512 + page + ((kernel + page - 1) // page) * page
open(output, 'w').write(f'{start} {ramdisk}\n')
PY
read -r start size < "$work/ramdisk.meta"
dd if="$boot" iflag=skip_bytes,count_bytes skip="$start" count="$size" status=none > "$work/ramdisk.gz"
gzip -t "$work/ramdisk.gz"
gzip -dc "$work/ramdisk.gz" | cpio -tv 2>/dev/null > "$work/ramdisk-list.txt"
# init must be a regular binary (not a symlink).
grep -q '^-.* init$' "$work/ramdisk-list.txt"
# V8: fstab.sc8830 must be at the ramdisk root for the first-stage mount.
grep -qE '^-.* fstab\.sc8830$' "$work/ramdisk-list.txt"
# V9: rootfs legacy completo -> init.rc + mountpoint /system.
grep -qE '^-.* init\.rc$' "$work/ramdisk-list.txt"
grep -qE '^d.* system$' "$work/ramdisk-list.txt"
printf 'boot_size=%s ramdisk_size=%s\n' "$(stat -c %s "$boot")" "$size"
printf 'ramdisk_init_entry=%s\n' "$(grep -E ' init$' "$work/ramdisk-list.txt" | head -1)"
printf 'ramdisk_fstab_entry=%s\n' "$(grep -E 'fstab\.sc8830$' "$work/ramdisk-list.txt" | head -1)"
printf 'ramdisk_initrc_entry=%s\n' "$(grep -E ' init\.rc$' "$work/ramdisk-list.txt" | head -1)"
printf 'ramdisk_system_mountpoint=%s\n' "$(grep -E ' system$' "$work/ramdisk-list.txt" | head -1)"
printf 'BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS\n'
