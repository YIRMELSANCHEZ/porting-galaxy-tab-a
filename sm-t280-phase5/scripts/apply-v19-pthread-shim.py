#!/usr/bin/env python3
# V19: pthread_t shim for proprietary blobs (Mali graphics) of the Android
# 5-7 era on Android 10's strict bionic. __pthread_internal_find aborts
# (async_safe_fatal) if the pthread_t is not in g_thread_list; the Mali HALs pass
# untracked pthread_t -> surfaceflinger aborts. The shim warns and returns the
# pointer instead of aborting (standard fix of Android 10 ports with old blobs).
# Va en bionic (libc) -> system.img. Idempotente.
import sys

F = "/home/lineage/android/lineage-17.1/bionic/libc/bionic/pthread_internal.cpp"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "V19: blobs propietarios" in s:
    print("V19_PATCH_ALREADY_PRESENT"); sys.exit(0)

old = ('    } else {\n'
       '      async_safe_fatal("invalid pthread_t %p passed to %s", thread, caller);\n'
       '    }\n')
new = ('    } else {\n'
       '      // V19: blobs propietarios (Mali) de era Android 5-7 pasan pthread_t que no\n'
       '      // están en g_thread_list; en vez de abortar, avisar y confiar en el puntero\n'
       '      // (fix estándar de ports Android 10 con blobs viejos).\n'
       '      async_safe_format_log(ANDROID_LOG_WARN, "libc",\n'
       '                            "invalid pthread_t %p passed to %s (tolerado)", thread, caller);\n'
       '      return thread;\n'
       '    }\n')

if old not in s:
    print("ERROR: could not find the async_safe_fatal of __pthread_internal_find", file=sys.stderr)
    sys.exit(2)
s = s.replace(old, new, 1)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V19_PATCH_APPLIED")
