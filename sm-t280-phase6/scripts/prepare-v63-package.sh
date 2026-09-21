#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: prepare-v63-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v63-package.sh ANDROID_ROOT WORKSPACE}
boot="$root/out/target/product/gtexswifi/boot.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-full-late-resume-PHASE6-v63-DO-NOT-FLASH.tar.md5"

grep -aFq 'V63 requesting full late_resume' "$root/out/target/product/gtexswifi/kernel"
bash "$workspace/sm-t280-phase6/scripts/package-boot-only-for-odin.sh" "$boot" "$package"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# tar accepts the Odin MD5 trailer; list and extract must expose exactly boot.img.
tar -tf "$package" > "$tmp/list"
[[ "$(cat "$tmp/list")" == "boot.img" ]]
tar -xf "$package" -C "$tmp" boot.img
cmp -s "$boot" "$tmp/boot.img"

printf 'boot_sha256=%s\n' "$(sha256sum "$boot" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V63_BOOT_ONLY_PACKAGE_VERIFY_PASS\n'
