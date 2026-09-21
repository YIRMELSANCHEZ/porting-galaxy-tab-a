#!/usr/bin/env bash
# Read-only capture for a V68 system that remains at the Lineage boot animation.
set -uo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

repo="$(cd "$(dirname "$0")/../.." && pwd)"
adb="$repo/sm-t280-phase1/tools/platform-tools/adb.exe"
stamp="$(date +%Y%m%d-%H%M%S)"
out="$repo/results/fase-6/v68-bootloop-$stamp"
mkdir -p "$out"

"$adb" devices -l >"$out/adb-devices.txt" 2>&1
"$adb" shell getprop >"$out/getprop.txt" 2>&1
"$adb" shell ps -A >"$out/ps.txt" 2>&1
"$adb" shell lshal >"$out/lshal.txt" 2>&1
"$adb" shell service list >"$out/service-list.txt" 2>&1
"$adb" shell dmesg >"$out/dmesg.txt" 2>&1
"$adb" logcat -b all -d -v threadtime >"$out/logcat-all.txt" 2>&1
"$adb" shell dumpsys activity processes >"$out/activity-processes.txt" 2>&1
"$adb" shell dumpsys SurfaceFlinger >"$out/surfaceflinger.txt" 2>&1
"$adb" shell dumpsys window >"$out/window.txt" 2>&1
"$adb" shell 'ls -l /data/tombstones /data/system/dropbox 2>&1' >"$out/crash-files.txt" 2>&1
"$adb" shell 'getprop sys.boot_completed; getprop dev.bootcomplete; getprop init.svc.zygote; getprop init.svc.surfaceflinger; getprop init.svc.bootanim' >"$out/boot-markers-1.txt" 2>&1
sleep 8
"$adb" shell ps -A >"$out/ps-2.txt" 2>&1
"$adb" logcat -b all -d -v threadtime >"$out/logcat-all-2.txt" 2>&1
"$adb" shell 'getprop sys.boot_completed; getprop dev.bootcomplete; getprop init.svc.zygote; getprop init.svc.surfaceflinger; getprop init.svc.bootanim' >"$out/boot-markers-2.txt" 2>&1

printf 'capture=%s\n' "$out"
printf 'V68_BOOTLOOP_CAPTURE_PASS\n'
