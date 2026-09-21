#!/usr/bin/env bash
# Offline integrity/content check for a boot+system Odin tar.md5.
set -euo pipefail
package=${1:?Usage: verify-odin-boot-system-package.sh PACKAGE.tar.md5}
contents=$(tar --list --file "$package" | sed '/^$/d')
test "$contents" = $'boot.img\nsystem.img'
archive=$(basename "${package%.md5}")
trailer_size=$((32 + 2 + ${#archive} + 1))
embedded=$(tail -c "$trailer_size" "$package" | awk '{print $1}')
calculated=$(head -c -"$trailer_size" "$package" | md5sum | awk '{print $1}')
test "$embedded" = "$calculated"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS\n'
