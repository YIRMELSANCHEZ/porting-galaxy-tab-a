#!/usr/bin/env bash
# Phase 5.2 — packages boot.img + system.img into an AP tar.md5 for Odin.
# Odin matches by .img file name: boot.img -> KERNEL, system.img -> SYSTEM.
# Does NOT include recovery, PIT, BL or CSC. Does not interact with the tablet.
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 BOOT_IMG SYSTEM_IMG OUTPUT_TAR_MD5" >&2
  exit 2
fi

boot_img="$(realpath "$1")"
system_img="$(realpath "$2")"
output="$(realpath -m "$3")"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
archive_name="$(basename "$output")"
archive_name="${archive_name%.md5}"

if [[ "$archive_name" != *.tar ]]; then
  echo "output must end in .tar.md5" >&2
  exit 2
fi

cp -- "$boot_img" "$workdir/boot.img"
cp -- "$system_img" "$workdir/system.img"
(
  cd "$workdir"
  # Order: boot before system.
  tar --format=ustar -cf "$archive_name" boot.img system.img
  md5="$(md5sum "$archive_name" | awk '{print $1}')"
  cp "$archive_name" "$output"
  printf '%s  %s\n' "$md5" "$archive_name" >> "$output"
)

trailer_size=$((32 + 2 + ${#archive_name} + 1))
embedded="$(tail -c "$trailer_size" "$output" | awk '{print $1}')"
calculated="$(head -c -"$trailer_size" "$output" | md5sum | awk '{print $1}')"
[[ "$embedded" == "$calculated" ]]

echo "file=$output"
echo "size=$(stat -c %s "$output")"
echo "boot_sha256=$(sha256sum "$boot_img" | awk '{print $1}')"
echo "system_sha256=$(sha256sum "$system_img" | awk '{print $1}')"
echo "embedded_md5=$embedded"
echo "package_sha256=$(sha256sum "$output" | awk '{print $1}')"
echo "ODIN_SYSTEM_PACKAGE_PASS"
