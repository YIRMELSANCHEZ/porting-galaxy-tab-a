#!/system/bin/sh
# fps measurement and frame breakdown for a given SwiftAngle scale.
# Usage (on the tablet):  sh /data/local/tmp/measure-scale.sh [seconds] [label]
# Requires persist.swiftangle.stats=1 (the script enables it if needed) and the app in the foreground,
# stopped on the screen to measure. Does not restart the app: the scale must already be applied.
S=${1:-40}
TAG=${2:-medicion}
L='SurfaceView - com.example.app/com.unity3d.player.UnityPlayerActivity#0'

P=""
i=0
while [ -z "$P" ] && [ $i -lt 30 ]; do
  P=$(ps -A -o PID,NAME | grep example.app | awk '{print $1}' | head -1)
  [ -z "$P" ] && sleep 1
  i=$((i+1))
done
if [ -z "$P" ]; then echo "MEASURE_FAIL: the app is not running"; exit 1; fi

[ "$(getprop persist.swiftangle.stats)" = "1" ] || setprop persist.swiftangle.stats 1
echo "=== $TAG  scale=$(getprop persist.swiftangle.scale)  threads=$(getprop persist.swiftangle.threads)  hwvideo=$(getprop persist.swiftangle.hwvideo)  pid=$P  ${S}s"

# CPU per thread at start
for t in /proc/$P/task/*; do echo "$(basename $t) $(cat $t/comm 2>/dev/null) $(awk '{print $14+$15}' $t/stat 2>/dev/null)"; done > /data/local/tmp/ms_stat0

logcat -c 2>/dev/null
sleep $S

for t in /proc/$P/task/*; do echo "$(basename $t) $(cat $t/comm 2>/dev/null) $(awk '{print $14+$15}' $t/stat 2>/dev/null)"; done > /data/local/tmp/ms_stat1

logcat -d -s V95_STATS:I V95_EGL:I > /data/local/tmp/ms_log 2>/dev/null

echo "--- frames (V95_EGL) ---"
grep V95_EGL /data/local/tmp/ms_log | awk '
  {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^per$/) ms += $(i+1);
      if ($i ~ /^frames=/)      { split($i, a, "="); f  += a[2] }
      if ($i ~ /^fence_poll_ms=/){ split($i, a, "="); fp += a[2] }
      if ($i ~ /^swap_ms=/)     { split($i, a, "="); sw += a[2] }
    }
    n++
  }
  END {
    if (n == 0 || f == 0) { print "  no data (persist.swiftangle.stats=1 and the app must be drawing)"; exit }
    printf "  ventanas=%d  tiempo=%.1f s  frames=%d  fps=%.2f  ms/frame=%.1f\n", n, ms/1000, f, f/(ms/1000), ms/f
    printf "  de cada frame: swap=%.1f ms  espera de fence=%.1f ms\n", sw/f, fp/f
  }'

echo "--- inside GL (V95_STATS) ---"
grep V95_STATS /data/local/tmp/ms_log | awk '
  {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^per$/) ms += $(i+1);
      if ($i ~ /^draws=/)   { split($i, a, "="); d  += a[2] }
      if ($i ~ /^waits=/)   { split($i, a, "="); w  += a[2] }
      if ($i ~ /^wait_ms=/) { split($i, a, "="); wm += a[2] }
      if ($i ~ /^clears=/)  { split($i, a, "="); c  += a[2] }
      if ($i ~ /^clear_ms=/){ split($i, a, "="); cm += a[2] }
      if ($i ~ /^jit=/)     { split($i, a, "="); j  += a[2] }
    }
    n++
  }
  END {
    if (n == 0) { print "  no data"; exit }
    printf "  draws=%d (%.1f/s)  resource waits=%d (%.0f ms)  clears=%d (%.0f ms)  JIT compilations=%d\n", d, d/(ms/1000), w, wm, c, cm, j
  }'

echo "--- independent fps (SurfaceFlinger) ---"
dumpsys SurfaceFlinger --latency "$L" 2>/dev/null | awk '
  NR > 1 && $2 > 0 { t[n++] = $2 }
  END {
    if (n < 3) { print "  no latency data" ; exit }
    span = (t[n-1] - t[0]) / 1000000000
    if (span > 0) printf "  last %d frames in %.2f s -> %.2f fps\n", n, span, (n-1)/span
  }'

echo "--- CPU per thread (% of one core) ---"
awk -v secs="$S" '
  NR == FNR { a[$1] = $3; c[$1] = $2; next }
  { d = ($3 - a[$1]) / secs; if (d > 3) printf "  %-18s %5.1f %%\n", c[$1], d }
' /data/local/tmp/ms_stat0 /data/local/tmp/ms_stat1 | sort -k2 -rn | head -12

echo "MEASURE_DONE $TAG"
