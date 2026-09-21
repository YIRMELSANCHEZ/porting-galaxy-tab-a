#!/usr/bin/env python3
# V59 (power button: FINAL FIX VERIFIED ON HARDWARE). Ramdisk only -> boot.img.
#
# Decisive test on the device (V58, light_sleep_en=0): holding a partial wakelock
# ("mywake") with the screen off, pressing POWER WAKES the tablet:
#   baseline IRQ 422 = 56, Display OFF/Asleep  ->  tras 5 pulsaciones = 66 (+10), Display ON/Awake.
# Without the wakelock, the device does mem-suspend (autosleep) and the KEY_POWER event is lost in the
# suspend<->resume transition (getevent=0, no InputDispatcher/PowerManager logs). The IRQ
# arrived (V58 ungates it) but the event did not survive the resume.
#
# Definitive root cause: it was NOT event delivery or the ISR; it was mem-suspend swallowing the
# event. Preventing suspend (wakelock) -> the power key works reliably.
#
# Fix: hold a permanent partial wakelock from init (on boot) by writing to
# /sys/power/wake_lock. This way the system does NOT enter mem-suspend: the screen still turns off
# (the backlight, the biggest consumer, is saved) but the CPU stays in idle (WFI) and the power key
# wakes the display. The device's SELinux is Permissive -> init can write the node
# (sysfs_wake_lock label) without blocking. Idempotent.
# TRADE-OFF (accepted by the user, explicit priority "I don't care how smooth the video is
# if I cannot turn the tablet on once it is off"): worse standby (the CPU does not suspend).
# V58 (light_sleep_en=0) is kept: the V58 + wakelock combination is the verified one.
# Backlog: the "good" fix = keep mem-suspend and arm the EIC wake in the PMIC (SPRD ADI),
# hardware-profundo e incierto.
import sys

SRC = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/rootdir/init.board.rc"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

MARK = "gtex_power_wake"
ANCHOR = "on boot\n    chown system system /sys/class/switch/sprd_simdet/state\n"
BLOCK = (ANCHOR +
         "# V59: wakelock parcial permanente -> el sistema NO entra en mem-suspend, para que el\n"
         "# boton de encendido pueda despertar la pantalla apagada (evento KEY_POWER perdido en\n"
         "# el resume del suspend). Contrapartida: peor standby. Ver KNOWN-ISSUES P1.\n"
         "    write /sys/power/wake_lock \"gtex_power_wake\"\n")

if MARK in s:
    print("V59_ALREADY"); sys.exit(0)
if ANCHOR not in s:
    print("V59_ERROR: cannot find the 'on boot' + sprd_simdet anchor in init.board.rc"); sys.exit(1)

s = s.replace(ANCHOR, BLOCK, 1)
open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V59_APPLIED -> wakelock permanente 'gtex_power_wake' en on boot")
