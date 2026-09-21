#!/usr/bin/env bash
# Offline-only rescue package: stock AQJ1 boot.img, and nothing else.
set -euo pipefail

workspace=${1:?Usage: prepare-stock-boot-restore.sh WORKSPACE}
stock_ap="$workspace/sm-t280-phase4/stock/extracted/AP_T280XXU0AQJ1_CL10429622_QB15394287_REV00_user_low_ship.tar.md5"
output="$workspace/sm-t280-phase5/packages/SM-T280-AQJ1-STOCK-BOOT-ONLY-RESTORE.tar.md5"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

test -f "$stock_ap"
tar --extract --file "$stock_ap" --directory "$work" boot.img
test -s "$work/boot.img"

archive=$(basename "${output%.md5}")
(
  cd "$work"
  tar --format=ustar -cf "$archive" boot.img
  md5=$(md5sum "$archive" | awk '{print $1}')
  cp "$archive" "$output"
  printf '%s  %s\n' "$md5" "$archive" >> "$output"
)

trailer_size=$((32 + 2 + ${#archive} + 1))
embedded=$(tail -c "$trailer_size" "$output" | awk '{print $1}')
calculated=$(head -c -"$trailer_size" "$output" | md5sum | awk '{print $1}')
test "$embedded" = "$calculated"
printf 'stock_boot_sha256=%s\n' "$(sha256sum "$work/boot.img" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'STOCK_BOOT_ONLY_RESCUE_PACKAGE_PASS\n'
