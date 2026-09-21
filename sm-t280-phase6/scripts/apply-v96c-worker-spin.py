#!/usr/bin/env python3
# V96c (experiment, off by default): the SwiftShader workers spin-wait for a short time
# before sleeping (futex) when the task queue empties. With small draws (UI) each draw
# generates 1 primitives task + N tiny pixel ones and the dominant cost is the latency of
# sleeping/waking threads (~0.5-1 ms per draw on this A7). persist.swiftangle.spin = microseconds of
# giro (0 = comportamiento original). Requiere V96. Idempotente.
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")

def rep(s, old, new, count=1):
    if s.count(old) != count:
        raise RuntimeError(f"anchor x{s.count(old)} != {count}: {old[:70]!r}")
    return s.replace(old, new)

c = SW / "Renderer/Renderer.cpp"
s = c.read_text(encoding="utf-8", errors="surrogateescape")
if "V96c" in s:
    print("Renderer.cpp: already patched"); print("V96C_DONE"); sys.exit(0)

old = ("\tvoid Renderer::scheduleTask(int threadIndex)\n\t{\n\t\tschedulerMutex.lock();\n\n"
       "\t\tint curThreadsAwake = threadsAwake;\n\n"
       "\t\tif((int)qSize < threadCount - curThreadsAwake + 1)\n\t\t{\n\t\t\tfindAvailableTasks();\n\t\t}\n\n"
       "\t\tif(qSize != 0)\n")
new = ("\tstatic long v96c_spinUs()   // V96c: persist.swiftangle.spin (us), 0 = sin giro\n"
       "\t{\n"
       "\t\tstatic long cached = -1;\n"
       "\t\tif(cached < 0)\n"
       "\t\t{\n"
       "\t\t\tcached = 0;\n"
       "\t\t\t#if defined(__ANDROID__) && defined(__BIONIC__)\n"
       "\t\t\tchar v[PROPERTY_VALUE_MAX] = {};\n"
       "\t\t\tif(property_get(\"persist.swiftangle.spin\", v, \"0\") > 0) cached = atol(v);\n"
       "\t\t\t#endif\n"
       "\t\t}\n"
       "\t\treturn cached;\n"
       "\t}\n\n"
       "\tvoid Renderer::scheduleTask(int threadIndex)\n\t{\n"
       "\t\tlong spinUntil = 0;   // V96c\n"
       "\t\tfor(;;)\n\t\t{\n"
       "\t\tschedulerMutex.lock();\n\n"
       "\t\tint curThreadsAwake = threadsAwake;\n\n"
       "\t\tif((int)qSize < threadCount - curThreadsAwake + 1)\n\t\t{\n\t\t\tfindAvailableTasks();\n\t\t}\n\n"
       "\t\tif(qSize == 0 && v96c_spinUs() > 0)   // V96c: girar antes de dormir\n"
       "\t\t{\n"
       "\t\t\tlong now = v95_now_us();\n"
       "\t\t\tif(spinUntil == 0) spinUntil = now + v96c_spinUs();\n"
       "\t\t\tif(now < spinUntil)\n"
       "\t\t\t{\n"
       "\t\t\t\tschedulerMutex.unlock();\n"
       "\t\t\t\tfor(volatile int i = 0; i < 200; i++) {}\n"
       "\t\t\t\tcontinue;\n"
       "\t\t\t}\n"
       "\t\t}\n\n"
       "\t\tif(qSize != 0)\n")
s = rep(s, old, new)
old2 = ("\t\telse\n\t\t{\n\t\t\ttask[threadIndex].type = Task::SUSPEND;\n\n\t\t\t--threadsAwake; // Atomic\n\t\t}\n\n\t\tschedulerMutex.unlock();\n\t}\n")
new2 = ("\t\telse\n\t\t{\n\t\t\ttask[threadIndex].type = Task::SUSPEND;\n\n\t\t\t--threadsAwake; // Atomic\n\t\t}\n\n\t\tschedulerMutex.unlock();\n\t\treturn;   // V96c\n\t\t}\n\t}\n")
s = rep(s, old2, new2)
c.write_text(s, encoding="utf-8", errors="surrogateescape")
print("Renderer.cpp: patched")
print("V96C_DONE")
