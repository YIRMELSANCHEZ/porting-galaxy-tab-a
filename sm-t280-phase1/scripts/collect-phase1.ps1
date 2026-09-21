param(
    [string]$Adb = "C:\Dev\Experiments\porting-galaxy-tab-a\sm-t280-phase1\tools\platform-tools\adb.exe",
    [string]$Raw = "C:\Dev\Experiments\porting-galaxy-tab-a\sm-t280-phase1\raw",
    [switch]$ContinueOnly
)

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path $Raw | Out-Null

function Save-AdbOutput {
    param([string]$Name, [string[]]$Arguments)
    $path = Join-Path $Raw ($Name + '.txt')
    $started = Get-Date -Format o
    $output = & $Adb @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    @(
        "# command: adb $($Arguments -join ' ')"
        "# captured: $started"
        "# exit_code: $exitCode"
        $output
    ) | Set-Content -LiteralPath $path -Encoding utf8
    Write-Host ("[{0}] {1}" -f $exitCode, $Name)
}

if (-not $ContinueOnly) {
Save-AdbOutput '00-adb-version' @('version')
Save-AdbOutput '01-adb-devices-l' @('devices', '-l')

# Identity, Android build, ABI and security properties.
Save-AdbOutput '10-getprop-all' @('shell', 'getprop')
foreach ($prop in @(
    'ro.product.model','ro.product.manufacturer','ro.product.brand','ro.product.device',
    'ro.product.name','ro.product.board','ro.hardware','ro.board.platform',
    'ro.build.version.release','ro.build.version.sdk','ro.build.version.security_patch',
    'ro.build.id','ro.build.display.id','ro.build.fingerprint','ro.build.description',
    'ro.build.type','ro.build.tags','ro.product.cpu.abi','ro.product.cpu.abi2',
    'ro.product.cpu.abilist','ro.product.cpu.abilist32','ro.product.cpu.abilist64',
    'ro.treble.enabled','ro.build.ab_update','ro.boot.slot_suffix','ro.virtual_ab.enabled',
    'ro.secure','ro.debuggable','ro.adb.secure'
)) {
    Save-AdbOutput ("11-prop-" + ($prop -replace '[^A-Za-z0-9_-]','_')) @('shell','getprop',$prop)
}

# CPU, kernel, device tree and modules.
Save-AdbOutput '20-proc-cpuinfo' @('shell','cat','/proc/cpuinfo')
Save-AdbOutput '21-uname-a' @('shell','uname','-a')
Save-AdbOutput '22-proc-version' @('shell','cat','/proc/version')
Save-AdbOutput '23-proc-cmdline' @('shell','cat','/proc/cmdline')
Save-AdbOutput '24-proc-config-gz-list' @('shell','ls','-l','/proc/config.gz')
Save-AdbOutput '25-proc-config-gz-base64' @('exec-out','sh','-c','if [ -r /proc/config.gz ]; then base64 /proc/config.gz; else echo NOT_READABLE; fi')
Save-AdbOutput '26-proc-modules' @('shell','cat','/proc/modules')
Save-AdbOutput '27-sys-module' @('shell','ls','-l','/sys/module')
Save-AdbOutput '28-device-tree' @('shell','ls','-l','/proc/device-tree')

# Memory and storage.
Save-AdbOutput '30-proc-meminfo' @('shell','cat','/proc/meminfo')
Save-AdbOutput '31-dumpsys-meminfo' @('shell','dumpsys','meminfo')
}
Save-AdbOutput '31b-dumpsys-meminfo-compact' @('shell','dumpsys','meminfo','-c')
Save-AdbOutput '32-vmstat' @('shell','vmstat','1','2')
Save-AdbOutput '33-proc-swaps' @('shell','cat','/proc/swaps')
Save-AdbOutput '34-zram0' @('shell','ls','-l','/sys/block/zram0')
Save-AdbOutput '35-zram0-disksize' @('shell','cat','/sys/block/zram0/disksize')
Save-AdbOutput '40-df' @('shell','df')
Save-AdbOutput '41-mount' @('shell','mount')
Save-AdbOutput '42-proc-mounts' @('shell','cat','/proc/mounts')
Save-AdbOutput '43-proc-partitions' @('shell','cat','/proc/partitions')
Save-AdbOutput '44-dev-block' @('shell','ls','-la','/dev/block')
Save-AdbOutput '45-dev-block-platform' @('shell','ls','-laR','/dev/block/platform')

# Graphics, display and input.
Save-AdbOutput '50-surfaceflinger' @('shell','dumpsys','SurfaceFlinger')
Save-AdbOutput '51-display' @('shell','dumpsys','display')
Save-AdbOutput '52-window' @('shell','dumpsys','window')
Save-AdbOutput '53-input' @('shell','dumpsys','input')
Save-AdbOutput '54-graphics-sysfs' @('shell','ls','-laR','/sys/class/graphics')
Save-AdbOutput '55-mali-sysfs' @('shell','sh','-c','ls -laR /sys/class/misc/mali* /proc/mali* 2>&1')

# Multimedia, audio, camera and sensors.
Save-AdbOutput '60-media-player' @('shell','dumpsys','media.player')
Save-AdbOutput '61-media-codec' @('shell','dumpsys','media.codec')
Save-AdbOutput '62-media-audio-flinger' @('shell','dumpsys','media.audio_flinger')
Save-AdbOutput '63-media-audio-policy' @('shell','dumpsys','media.audio_policy')
Save-AdbOutput '64-audio' @('shell','dumpsys','audio')
Save-AdbOutput '65-media-camera' @('shell','dumpsys','media.camera')
Save-AdbOutput '66-sensorservice' @('shell','dumpsys','sensorservice')

# Connectivity.
Save-AdbOutput '70-wifi' @('shell','dumpsys','wifi')
Save-AdbOutput '71-ip-addr' @('shell','ip','addr')
Save-AdbOutput '72-ip-route' @('shell','ip','route')
Save-AdbOutput '73-ifconfig' @('shell','ifconfig')
Save-AdbOutput '74-proc-net-wireless' @('shell','cat','/proc/net/wireless')
Save-AdbOutput '75-bluetooth-manager' @('shell','dumpsys','bluetooth_manager')
Save-AdbOutput '76-bluetooth-manager-alt' @('shell','dumpsys','bluetooth')

# Power, thermal and USB.
Save-AdbOutput '80-battery' @('shell','dumpsys','battery')
Save-AdbOutput '81-power' @('shell','dumpsys','power')
Save-AdbOutput '82-power-supply' @('shell','ls','-laR','/sys/class/power_supply')
Save-AdbOutput '83-thermal' @('shell','ls','-laR','/sys/class/thermal')
Save-AdbOutput '84-thermal-values' @('shell','sh','-c','for f in /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp; do echo "$f=$(cat $f 2>/dev/null)"; done')

# Package inventory and declared hardware features.
Save-AdbOutput '90-pm-list-packages-f' @('shell','pm','list','packages','-f')
Save-AdbOutput '91-pm-list-features' @('shell','pm','list','features')
foreach ($package in @('com.android.vending','com.google.android.gms','com.google.android.gsf','com.google.android.webview','com.example.app')) {
    Save-AdbOutput ("92-package-" + $package) @('shell','dumpsys','package',$package)
}

# SELinux and finite log snapshots.
Save-AdbOutput '93-getenforce' @('shell','getenforce')
Save-AdbOutput '94-logcat-d' @('logcat','-d')
Save-AdbOutput '95-dmesg' @('shell','dmesg')

Write-Host 'Collection complete.'
