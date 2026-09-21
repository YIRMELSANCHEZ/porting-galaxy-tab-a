#!/usr/bin/env python3
# V57 (power button: ROOT FIX of the wake). KERNEL CHANGE -> NEW boot.
# V56 added enable_irq_wake(gpio_to_irq(PB_INT)) in sci_keypad_suspend, but the button
# STILL does not wake. Definitive root cause: the power key is IRQ 422 "irq-a-eic
# powerkey" (analog EIC of the PMIC), and its irqchip `a_eic_irq_chip` in
# drivers/gpio/gpio-eic.c does NOT implement `.irq_set_wake` (only the *_gpio_* chips have it).
# Without .irq_set_wake, enable_irq_wake(422) returns -ENXIO and the IRQ is NOT armed as a
# wake source in suspend -> pressing POWER does not resume the CPU.
#
# Fix: add `.irq_set_wake = sci_gpio_irq_set_wake` to a_eic_irq_chip (power/volume/headset
# analog EIC) and to d_eic_irq_chip (digital EIC), as the *_gpio_* already have. The
# impl sci_gpio_irq_set_wake (return on?0:-EPERM) is enough: it marks the IRQ as wake-enabled and the
# core keeps it active in suspend; SPRD's PMIC/EIC resumes the AP by design.
# With V56 (enable_irq_wake in suspend) + V57 (irqchip supports set_wake) POWER wakes.
#
# gpio-eic.c is built-in -> recompiles the kernel (NEW boot). sprdwl.ko does not change (same
# source/vermagic) -> WiFi remains. Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/gpio/gpio-eic.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if ".name = \"irq-a-eic\",\n\t.irq_disable" in s and "a_eic_irq_chip = {\n\t.name = \"irq-a-eic\",\n\t.irq_disable = sci_gpio_irq_mask,\n\t.irq_ack = sci_gpio_irq_ack,\n\t.irq_mask = sci_gpio_irq_mask,\n\t.irq_unmask = sci_eic_irq_unmask,\n\t.irq_set_type = sci_eic_irq_set_type,\n\t.irq_set_wake" in s:
    print("V57_ALREADY"); sys.exit(0)

changed = 0
for name in ("a-eic", "d-eic"):
    OLD = (
        "\t.name = \"irq-" + name + "\",\n"
        "\t.irq_disable = sci_gpio_irq_mask,\n"
        "\t.irq_ack = sci_gpio_irq_ack,\n"
        "\t.irq_mask = sci_gpio_irq_mask,\n"
        "\t.irq_unmask = sci_eic_irq_unmask,\n"
        "\t.irq_set_type = sci_eic_irq_set_type,\n"
        "};\n"
    )
    NEW = (
        "\t.name = \"irq-" + name + "\",\n"
        "\t.irq_disable = sci_gpio_irq_mask,\n"
        "\t.irq_ack = sci_gpio_irq_ack,\n"
        "\t.irq_mask = sci_gpio_irq_mask,\n"
        "\t.irq_unmask = sci_eic_irq_unmask,\n"
        "\t.irq_set_type = sci_eic_irq_set_type,\n"
        "\t.irq_set_wake = sci_gpio_irq_set_wake,\n"
        "};\n"
    )
    if OLD in s:
        s = s.replace(OLD, NEW, 1); changed += 1
        print("V57_APPLIED -> .irq_set_wake en irq-" + name)
    else:
        print("V57_WARN: cannot find the struct irq-" + name + " esperado")

if changed == 0:
    print("V57_ERROR: no change was applied"); sys.exit(1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V57_DONE (" + str(changed) + " irqchips)")
