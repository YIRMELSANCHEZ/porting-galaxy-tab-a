param([string]$Label = "diag")   # uso: .\diag-device.ps1 v44

$ADB  = "C:\Dev\Experiments\porting-galaxy-tab-a\sm-t280-phase1\tools\platform-tools\adb.exe"
$Root = "C:\Dev\Experiments\porting-galaxy-tab-a\results\fase-6"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out  = Join-Path $Root ("diag-{0}-{1}" -f $Label, $Stamp)
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Dump($name, $cmd) { & $ADB shell $cmd > (Join-Path $Out $name) 2>&1 }

& $ADB start-server | Out-Null
& $ADB wait-for-device

# ---- foto rapida a consola ----
"===== BOOT / uptime ====="
"boot_completed=" + (& $ADB shell getprop sys.boot_completed)
& $ADB shell "cat /proc/uptime"
"`n===== SERVICIOS QUE CRASHEAN / NO ARRANCAN ====="
& $ADB shell "getprop | grep init.svc | grep -viE 'running|stopped'"
"`n===== CRASHES EN dmesg ====="
& $ADB shell "dmesg | grep -iE 'signal (6|11)|panic|lowmemorykiller' | tail -20"

# ---- volcados completos a fichero ----
Dump "getprop-all.txt"        "getprop"
Dump "initsvc.txt"            "getprop | grep init.svc"
Dump "lshal.txt"              "lshal"
Dump "lshal-vintf.txt"        "lshal --init-vintf"
Dump "ps.txt"                 "ps -A"
Dump "dmesg.txt"              "dmesg"
Dump "logcat-main.txt"        "logcat -d"
Dump "logcat-crash.txt"       "logcat -b crash -d"
Dump "logcat-events.txt"      "logcat -b events -d"

# por subsistema (sensores, wifi, bt, audio, video, red, rendimiento)
$svc = @("sensorservice","wifi","bluetooth_manager","audio","media.audio_flinger",
         "media.player","media.codec","SurfaceFlinger","gpu","display","power",
         "input","connectivity","cpuinfo","meminfo","batterystats","package")
foreach ($s in $svc) { Dump ("dumpsys-{0}.txt" -f ($s -replace '\.','_')) ("dumpsys " + $s) }

# artefactos de crash + interfaces de red
Dump "tombstones-ls.txt"      "ls -l /data/tombstones/ /data/anr/ 2>/dev/null"
Dump "net-ifaces.txt"         "ls /sys/class/net/; echo '---'; ip addr 2>/dev/null"
Dump "wakeup-sources.txt"     "cat /sys/kernel/debug/wakeup_sources 2>/dev/null"

# bugreport completo (lento/grande) solo si pasas -Full
if ($args -contains "-Full") { & $ADB bugreport (Join-Path $Out "bugreport.zip") }

# ---- resumen final ----
"`n===== RESUMEN ($Out) ====="
"HALs declarados-no-servidos / caidos:"
Select-String -Path (Join-Path $Out "lshal.txt") -Pattern "^\s*\?|N/A\s+N/A" | Select-Object -First 15 -ExpandProperty Line
"`nServicios reiniciando:"
Select-String -Path (Join-Path $Out "initsvc.txt") -Pattern "restarting" -ErrorAction SilentlyContinue | ForEach-Object { $_.Line }
"`nTombstones:"
Get-Content (Join-Path $Out "tombstones-ls.txt")
"`nListo -> $Out"