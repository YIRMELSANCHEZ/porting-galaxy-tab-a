#!/usr/bin/env bash
# Phase 5.3 — diagnostic capture of the system first boot.
# Runs from Windows (Git Bash) after flashing boot+system and booting.
# Reads from the device only: no reboot, no write, no restore.
set -uo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ADB="$REPO/sm-t280-phase1/tools/platform-tools/adb.exe"
OUT="$REPO/results/phase-5/first-boot-runtime"
mkdir -p "$OUT"
WAIT=${1:-120}

echo "== esperando ADB hasta ${WAIT}s (device o recovery) =="
end=$((SECONDS + WAIT)); state=""
while [[ $SECONDS -lt $end ]]; do
  state="$("$ADB" get-state 2>/dev/null || true)"
  [[ -n "$state" && "$state" != "unknown" ]] && break
  sleep 3
done
echo "adb_state=${state:-none}"
"$ADB" devices -l | tee "$OUT/adb-devices.txt"

if [[ -z "${state:-}" || "$state" == "unknown" ]]; then
  echo "ADB not available. The device did not expose ADB in ${WAIT}s."
  echo "Provisional classification: pre-ADB (bootloader/kernel/init early)."
  echo "BOOT_STAGE=NO_ADB" | tee "$OUT/CLASSIFICATION.txt"
  exit 0
fi

echo "== capturando evidencia =="
"$ADB" shell getprop            > "$OUT/getprop.txt" 2>&1
"$ADB" shell dmesg             > "$OUT/dmesg.txt" 2>&1
"$ADB" logcat -d               > "$OUT/logcat.txt" 2>&1
"$ADB" shell 'cat /proc/last_kmsg' > "$OUT/last_kmsg.txt" 2>&1
"$ADB" shell 'ls /sys/fs/pstore; cat /sys/fs/pstore/console-ramoops* 2>/dev/null' > "$OUT/pstore.txt" 2>&1
"$ADB" shell 'cat /proc/mounts' > "$OUT/proc-mounts.txt" 2>&1
"$ADB" shell 'ls -l /dev/block/platform/sdio_emmc/by-name' > "$OUT/partitions-by-name.txt" 2>&1
"$ADB" shell ps -A             > "$OUT/ps.txt" 2>&1
"$ADB" shell 'getprop | grep -iE "boot_completed|sys.boot|init.svc.zygote|init.svc.surfaceflinger|dev.bootcomplete"' > "$OUT/boot-markers.txt" 2>&1
"$ADB" shell uname -a          > "$OUT/uname.txt" 2>&1

echo "== stage classification =="
{
  bc="$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')"
  zy="$("$ADB" shell getprop init.svc.zygote 2>/dev/null | tr -d '\r')"
  sf="$("$ADB" shell getprop init.svc.surfaceflinger 2>/dev/null | tr -d '\r')"
  echo "sys.boot_completed=$bc"
  echo "init.svc.zygote=$zy"
  echo "init.svc.surfaceflinger=$sf"
  if [[ "$bc" == "1" ]]; then echo "BOOT_STAGE=FRAMEWORK_BOOT_COMPLETED"
  elif [[ "$zy" == "running" ]]; then echo "BOOT_STAGE=FRAMEWORK_STARTING (zygote up, no boot_completed)"
  elif [[ "$state" == "recovery" ]]; then echo "BOOT_STAGE=RECOVERY (system did not boot)"
  else echo "BOOT_STAGE=INIT_OR_EARLY (ADB via init's adbd, framework did not boot)"; fi
} | tee "$OUT/CLASSIFICATION.txt"

echo "== evidencia en $OUT =="
ls -la "$OUT"
