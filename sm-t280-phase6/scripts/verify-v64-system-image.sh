#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: verify-v64-system-image.sh ANDROID_ROOT SYSTEM_IMG}
image=${2:?Usage: verify-v64-system-image.sh ANDROID_ROOT SYSTEM_IMG}
simg2img="$root/out/host/linux-x86/bin/simg2img"
expected_service="$root/out/target/product/gtexswifi/system/bin/hw/android.system.suspend@1.0-service"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

"$simg2img" "$image" "$work/system.raw.img"
debugfs -R 'dump /system/bin/hw/android.system.suspend@1.0-service /tmp/v64-service.dump' \
  "$work/system.raw.img" >/dev/null 2>&1
debugfs -R 'dump /system/usr/keylayout/sci-keypad.kl /tmp/v64-keylayout.dump' \
  "$work/system.raw.img" >/dev/null 2>&1

cmp -s /tmp/v64-service.dump "$expected_service"
grep -Fq 'V64: userspace suspend counter enabled' /tmp/v64-service.dump
grep -Fq '# Android 10 accepts only VIRTUAL/FUNCTION/GESTURE key-layout flags.' \
  /tmp/v64-keylayout.dump
grep -Fq 'key 116   POWER' /tmp/v64-keylayout.dump
if grep -Fq 'WAKE' /tmp/v64-keylayout.dump; then
  echo 'V64_ERROR: invalid WAKE flag in extracted keylayout' >&2
  exit 1
fi

rm -f /tmp/v64-service.dump /tmp/v64-keylayout.dump
printf 'embedded_service_sha256=%s\n' "$(sha256sum "$expected_service" | awk '{print $1}')"
printf 'V64_SYSTEM_IMAGE_CONTENT_VERIFY_PASS\n'
