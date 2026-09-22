#!/usr/bin/env bash
set -euo pipefail

root=/home/lineage/android/lineage-17.1
workspace=/mnt/c/Dev/Experiments/porting-galaxy-tab-a

strings -a "$root/out/target/product/gtexswifi/kernel" \
  | grep -iE 'Linux version|gcc version'

sed -n '150,175p' "$root/system/core/init/security.cpp"

cd "$workspace"
expected='998da11be181f9e7d90eee3c741fb18134b0f9eb30c4df2eb0a18343848b189d'
actual=$(sha256sum sm-t280-phase5/packages/SM-T280-system-android10-PHASE5-v1-DO-NOT-FLASH.tar.md5 | awk '{print $1}')
test "$actual" = "$expected"

grep 'tar.md5' results/phase-5/ARTIFACTS.sha256 | sha256sum -c -
tar --list --file sm-t280-phase5/packages/SM-T280-system-android10-PHASE5-v1-DO-NOT-FLASH.tar.md5 \
  | sed '/^$/d'

printf 'HANDOFF_REVALIDATION_PASS\n'
