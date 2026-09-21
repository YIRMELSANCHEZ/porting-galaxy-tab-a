#!/usr/bin/env bash
# Packages ONLY boot.img into an AP tar.md5 for Odin (KERNEL). system is NOT touched.
# Odin matches by name: boot.img -> KERNEL. No recovery/PIT/BL/CSC. Does not touch the tablet.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 BOOT_IMG OUTPUT_TAR_MD5" >&2
  exit 2
fi

boot_img="$(realpath "$1")"
output="$(realpath -m "$2")"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
archive_name="$(basename "$output")"
archive_name="${archive_name%.md5}"

if [[ "$archive_name" != *.tar ]]; then
  echo "output must end in .tar.md5" >&2
  exit 2
fi

cp -- "$boot_img" "$workdir/boot.img"
(
  cd "$workdir"
  tar --format=ustar -cf "$archive_name" boot.img
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
echo "embedded_md5=$embedded"
echo "package_sha256=$(sha256sum "$output" | awk '{print $1}')"
echo "ODIN_BOOT_ONLY_PACKAGE_PASS"
