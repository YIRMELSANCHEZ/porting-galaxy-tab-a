#!/usr/bin/env python3
# V58 (power button: FIX THAT WORKS - disable light-sleep). KERNEL CHANGE.
# Root cause confirmed empirically: the device does NOT do PM suspend; on turning the screen off
# it enters SPRD's LIGHT-SLEEP (cpuidle-scx35, light_sleep_en=1), which
# sci_glb_set(REG_AP_AHB_MCU_PAUSE, LIGHT_SLEEP_ENABLE | BIT_MCU_SYS_SLEEP_EN) -> pauses the
# subsystem of the AP, including the ADI clock (serial interface to the PMIC). With the ADI paused,
# the power-key interrupt (analog EIC via ANA) cannot be served/propagated -> the
# AP does not wake. VERIFIED: with light_sleep_en=0 (runtime), pressing POWER with the screen
# off increments IRQ 422 and WAKES the tablet (mWakefulness=Awake).
# The V56/V57 fixes (enable_irq_wake + irqchip set_wake) were for standard PM suspend, which
# this device does not use; that is why they were not enough.
#
# Fix: default light_sleep_en = 0 in drivers/platform/sprd/cpuidle-scx35.c. The AP no longer
# enters deep light-sleep -> the EIC/ADI stays clocked -> the power key wakes.
# TRADE-OFF: higher idle consumption (standby). The "good" fix (keep light-sleep and
# waking via a dedicated PMIC wake line) is deep-hardware and uncertain ->
# backlog. idle_deep_en was already 0. gpio-eic.c is built-in -> recompiles the kernel (NEW boot).
# sprdwl.ko unchanged (WiFi remains). Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/platform/sprd/cpuidle-scx35.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

OLD = "static int light_sleep_en = 1;"
NEW = ("/* V58: light-sleep OFF por defecto -> el power key (EIC/ADI del PMIC) puede despertar\n"
       " * la tablet desde pantalla apagada. Contrapartida: peor standby. Ver KNOWN-ISSUES P1. */\n"
       "static int light_sleep_en = 0;")

if "static int light_sleep_en = 0;" in s:
    print("V58_ALREADY"); sys.exit(0)
if OLD not in s:
    print("V58_ERROR: no encuentro 'static int light_sleep_en = 1;'"); sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V58_APPLIED -> light_sleep_en = 0 by default")
