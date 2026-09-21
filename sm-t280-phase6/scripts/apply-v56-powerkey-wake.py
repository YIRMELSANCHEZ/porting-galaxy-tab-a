#!/usr/bin/env python3
# V56 (power button: wake from suspend). KERNEL CHANGE -> NEW boot + recompile
# sprdwl.ko.
# Symptom: with V55 (POWER WAKE keylayout) the button still does not wake the tablet from
# sleep. ROOT cause in the driver: kernel/.../drivers/input/keyboard/sc_keypad.c registers the
# power as an EIC key (PB_INT, own IRQ via gpio_to_irq(PB_INT), ISR sci_powerkey_isr) and
# calls device_init_wakeup(1), BUT sci_keypad_suspend() does NOTHING: it does not call
# enable_irq_wake() for the power IRQ -> on entering suspend, that IRQ is not armed
# as a wake source -> pressing POWER does not resume the CPU.
#
# Fix: en sci_keypad_suspend() -> enable_irq_wake(gpio_to_irq(PB_INT)); y en
# sci_keypad_resume() -> disable_irq_wake(gpio_to_irq(PB_INT)); this way the power IRQ arms the
# wake in suspend. (SPRD's EIC irqchip implements irq_set_wake.)
#
# IMPORTANT: recompiling the kernel changes the vermagic; sprdwl.ko must be rebuilt against
# the new kernel and the prebuilt updated (device/.../prebuilt/modules/sprdwl.ko), or
# WiFi stops loading. The V56 build flow does it. boot CHANGES. Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/input/keyboard/sc_keypad.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "enable_irq_wake(gpio_to_irq(PB_INT))" in s:
    print("V56_ALREADY"); sys.exit(0)

# 1) suspend: armar wake
OLD_SUS = (
    "static int sci_keypad_suspend(struct platform_device *dev, pm_message_t state)\n"
    "{\n"
    "\treturn 0;\n"
    "}\n"
)
NEW_SUS = (
    "static int sci_keypad_suspend(struct platform_device *dev, pm_message_t state)\n"
    "{\n"
    "\t/* V56: armar el IRQ del power (EIC) como fuente de wake para resumir desde suspend */\n"
    "\tenable_irq_wake(gpio_to_irq(PB_INT));\n"
    "\treturn 0;\n"
    "}\n"
)
if OLD_SUS not in s:
    print("V56_ERROR: no encuentro sci_keypad_suspend esperado"); sys.exit(1)
s = s.replace(OLD_SUS, NEW_SUS, 1)

# 2) resume: disarm wake (after the pdata declaration line)
OLD_RES = (
    "static int sci_keypad_resume(struct platform_device *dev)\n"
    "{\n"
    "       struct sci_keypad_platform_data *pdata = dev->dev.platform_data;\n"
    "\tunsigned long value;\n"
    "\n"
)
NEW_RES = (
    OLD_RES
    + "\tdisable_irq_wake(gpio_to_irq(PB_INT));\n"
)
if OLD_RES not in s:
    print("V56_ERROR: no encuentro sci_keypad_resume esperado"); sys.exit(1)
s = s.replace(OLD_RES, NEW_RES, 1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V56_APPLIED -> enable/disable_irq_wake(PB_INT) en suspend/resume")
