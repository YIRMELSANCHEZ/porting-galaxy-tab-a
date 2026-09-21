#!/usr/bin/env bash
set -eo pipefail

root=/home/lineage/android/lineage-17.1
source_file="$root/system/hardware/interfaces/suspend/1.0/default/main.cpp"
product="$root/out/target/product/gtexswifi"

grep -Fq 'V64: userspace suspend counter enabled' "$source_file"
grep -Fq 'true /* mUseSuspendCounter*/' "$source_file"

cd "$root"
export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/lineage/.ccache
ccache -M 50G >/dev/null 2>&1 || true

printf '=== V64 BUILD START %s ===\n' "$(date -Is)"
source build/envsetup.sh
lunch lineage_gtexswifi-userdebug
m -j8 android.system.suspend@1.0-service
m -j8 snod

service="$product/system/bin/hw/android.system.suspend@1.0-service"
test -f "$service"
strings -a "$service" | grep -F 'V64: userspace suspend counter enabled'
file "$product/system.img" | grep -F 'Android sparse image'

printf 'service_sha256=%s\n' "$(sha256sum "$service" | awk '{print $1}')"
printf 'system_img_sha256=%s\n' "$(sha256sum "$product/system.img" | awk '{print $1}')"
printf 'V64_SYSTEM_SUSPEND_BUILD_PASS\n'
