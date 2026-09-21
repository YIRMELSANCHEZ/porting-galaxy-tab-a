#!/usr/bin/env python3
# V10: declare the /system fstab in the device tree (firmware/android/fstab).
# The bootloader ignores the boot.img cmdline, so ro.hardware never reaches
# init and GetFstabPath() never finds /fstab.sc8830. The canonical Android 10
# path is ReadFstabFromDt(): an fstab node in the DTB. The bootloader does
# respect the DTB body (it only overwrites bootargs). Idempotent.
import sys

DTS = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/arch/arm/boot/dts/sprd-scx35_gtexswifi_rev05.dts"
MARK = "android,fstab"

NODE = """	firmware {
		android {
			compatible = "android,firmware";
			fstab {
				compatible = "android,fstab";
				system {
					compatible = "android,system";
					dev = "/dev/block/platform/sdio_emmc/by-name/SYSTEM";
					type = "ext4";
					mnt_flags = "ro,errors=panic";
					fsmgr_flags = "wait";
				};
			};
		};
	};
"""

with open(DTS, "r", encoding="utf-8") as f:
    lines = f.readlines()

if any(MARK in l for l in lines):
    print("V10_PATCH_ALREADY_PRESENT")
    sys.exit(0)

# Locate the chosen { ... }; block and insert the firmware node after its close.
chosen_idx = None
for i, l in enumerate(lines):
    if l.strip().startswith("chosen") and l.rstrip().endswith("{"):
        chosen_idx = i
        break
if chosen_idx is None:
    print("ERROR: could not find the chosen node", file=sys.stderr)
    sys.exit(2)

close_idx = None
for j in range(chosen_idx + 1, len(lines)):
    if lines[j].strip() == "};":
        close_idx = j
        break
if close_idx is None:
    print("ERROR: could not find the close of the chosen node", file=sys.stderr)
    sys.exit(2)

lines.insert(close_idx + 1, "\n" + NODE)

with open(DTS, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("V10_PATCH_APPLIED")
