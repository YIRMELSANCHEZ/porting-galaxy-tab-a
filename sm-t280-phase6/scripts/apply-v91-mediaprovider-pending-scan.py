#!/usr/bin/env python3
# V91 (MED1 + GAL1). MediaProvider.update(): the scan on publishing an item (IS_PENDING 1->0) is only
# scheduled inside the `if (!isCallingPackageSystem())` block, so the screenshots that
# SystemUI publishes (a system package) are never scanned: the row stays with _size=NULL and datetaken=NULL
# until a boot scan. Gallery2 sorts by datetaken DESC -> with no date, new screenshots
# fall to the end / by name (GAL1). Measured in V87: after `input keyevent 120` the row has
# is_pending=0, _size=NULL, datetaken=NULL and there is no MediaScanner trace.
# Patch: trigger the scan whenever the update includes IS_PENDING. Idempotent.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/packages/providers/MediaProvider/src/com/android/providers/media/MediaProvider.java")
s = p.read_text(encoding="utf-8")
if "V91_PENDING_SCAN" in s:
    print("MediaProvider.java: already patched"); print("V91_DONE"); sys.exit(0)
old = ("                Trace.traceEnd(TRACE_TAG_DATABASE);\n"
       "            }\n"
       "\n"
       "            genre = initialValues.getAsString(Audio.AudioColumns.GENRE);\n")
new = ("                Trace.traceEnd(TRACE_TAG_DATABASE);\n"
       "            }\n"
       "\n"
       "            // V91_PENDING_SCAN: publishing (IS_PENDING) from system callers (SystemUI\n"
       "            // screenshots) must also trigger the blocking metadata scan\n"
       "            if (initialValues.containsKey(MediaColumns.IS_PENDING)) {\n"
       "                triggerScan = true;\n"
       "            }\n"
       "            genre = initialValues.getAsString(Audio.AudioColumns.GENRE);\n")
if s.count(old) != 1:
    print(f"V91_ERROR: anchor no unico ({s.count(old)})"); sys.exit(1)
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("MediaProvider.java: scan on publish also for system callers")
print("V91_DONE")
