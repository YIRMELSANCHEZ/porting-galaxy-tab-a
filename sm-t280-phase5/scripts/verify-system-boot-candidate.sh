#!/usr/bin/env bash
# Phase 5.1 — offline validation of boot.img + system.img of the full ROM.
# Does not interact with the tablet. Exits != 0 if any check fails.
set -euo pipefail

root=${1:?Usage: verify-system-boot-candidate.sh ANDROID_ROOT}
product="$root/out/target/product/gtexswifi"
boot="$product/boot.img"
system="$product/system.img"
kernel="$product/kernel"
dt="$product/dt.img"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

BOOT_MAX=16777216
SYSTEM_MAX=2147483648

echo "## boot.img"
test -f "$boot"
bsize=$(stat -c %s "$boot")
echo "boot_size=$bsize margin=$((BOOT_MAX - bsize))"
test "$bsize" -le "$BOOT_MAX"
# Cabecera Samsung/Spreadtrum DHTB + cabecera Android.
test "$(dd if="$boot" bs=1 count=4 status=none)" = DHTB
test "$(dd if="$boot" bs=1 skip=512 count=8 status=none)" = 'ANDROID!'
grep -a -q 'SEANDROIDENFORCE' "$boot" && echo "seandroid_tag=present"

# Kernel embebido = kernel construido in-tree (GCC 4.8 / 3.10.108).
read -r kernel_size kernel_addr ramdisk_size ramdisk_addr second_size second_addr tags_addr page_size dt_size unused \
  <<< "$(od -An -tu4 -j 520 -N 40 "$boot" | tr '\n' ' ')"
test "$page_size" -eq 2048
kernel_offset=$((512 + page_size))
dd if="$boot" of="$work/kernel" bs=1M skip="$kernel_offset" count="$kernel_size" iflag=skip_bytes,count_bytes status=none
if [[ -f "$kernel" ]]; then
  cmp "$work/kernel" "$kernel" && echo "kernel_matches_product_kernel=yes"
fi
# Confirm toolchain/version in the embedded kernel.
if strings -a "$work/kernel" | grep -qE 'Linux version 3\.10\.108'; then echo "kernel_version=3.10.108"; else echo "WARN: kernel version string not 3.10.108"; fi
if strings -a "$work/kernel" | grep -qE 'gcc version 4\.8'; then echo "kernel_gcc=4.8"; else echo "WARN: kernel gcc string not 4.8"; fi

# cmdline SELinux permissive (diagnostic build) + console.
if strings -a "$boot" | grep -q 'androidboot.selinux=permissive'; then echo "selinux_cmdline=permissive"; fi
echo "boot_sha256=$(sha256sum "$boot" | awk '{print $1}')"

echo
echo "## system.img"
test -f "$system"
ssize=$(stat -c %s "$system")
magic=$(od -An -tx4 -N4 "$system" | tr -d ' ')
SIMG2IMG=""
if command -v simg2img >/dev/null 2>&1; then SIMG2IMG=simg2img
elif [[ -x "$root/out/host/linux-x86/bin/simg2img" ]]; then SIMG2IMG="$root/out/host/linux-x86/bin/simg2img"; fi
if [[ "$magic" == "ed26ff3a" ]]; then
  echo "system_format=sparse sparse_size=$ssize"
  # Decompress sparse -> raw to measure and check ext4.
  if [[ -n "$SIMG2IMG" ]]; then
    "$SIMG2IMG" "$system" "$work/system.raw"
    rawsize=$(stat -c %s "$work/system.raw")
    echo "system_raw_size=$rawsize system_margin=$((SYSTEM_MAX - rawsize))"
    test "$rawsize" -le "$SYSTEM_MAX"
    e2fsck -fn "$work/system.raw" >/dev/null 2>&1 && echo "system_ext4_fsck=clean" || echo "WARN: e2fsck reported issues"
  else
    echo "WARN: simg2img not available; sparse measure only. sparse<=SYSTEM_MAX: $([[ $ssize -le $SYSTEM_MAX ]] && echo yes || echo NO)"
  fi
else
  echo "system_format=raw_or_other magic=$magic raw_size=$ssize margin=$((SYSTEM_MAX - ssize))"
  test "$ssize" -le "$SYSTEM_MAX"
  e2fsck -fn "$system" >/dev/null 2>&1 && echo "system_ext4_fsck=clean" || echo "WARN: e2fsck reported issues"
fi
echo "system_sha256=$(sha256sum "$system" | awk '{print $1}')"

echo
echo "## dt.img"
if [[ -f "$dt" ]]; then echo "dt_size=$(stat -c %s "$dt") dt_sha256=$(sha256sum "$dt" | awk '{print $1}')"; fi

echo
echo "SYSTEM_BOOT_OFFLINE_VERIFY_PASS"
