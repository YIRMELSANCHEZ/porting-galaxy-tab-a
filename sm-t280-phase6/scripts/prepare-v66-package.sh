#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: prepare-v66-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v66-package.sh ANDROID_ROOT WORKSPACE}
boot="$root/out/target/product/gtexswifi/boot.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-display-power-mode-PHASE6-v66-DO-NOT-FLASH.tar.md5"

grep -aFq 'V66 HWC power-mode request' "$root/out/target/product/gtexswifi/kernel"
grep -aFq 'V66 display power OFF complete' "$root/out/target/product/gtexswifi/kernel"
grep -aFq 'V66 display power ON complete' "$root/out/target/product/gtexswifi/kernel"

bash "$workspace/sm-t280-phase6/scripts/package-boot-only-for-odin.sh" "$boot" "$package"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
tar -tf "$package" > "$tmp/list"
[[ "$(cat "$tmp/list")" == "boot.img" ]]
tar -xf "$package" -C "$tmp" boot.img
cmp -s "$boot" "$tmp/boot.img"

printf 'boot_sha256=%s\n' "$(sha256sum "$boot" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V66_BOOT_ONLY_PACKAGE_VERIFY_PASS\n'
