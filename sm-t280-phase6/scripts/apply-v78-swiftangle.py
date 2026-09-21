#!/usr/bin/env python3
# V78 (APP: software GLES 3.0 only for the target app). On top of V77 (SwiftShader compiling on
# ARM32). Changes in system.img:
#  1) external/swiftshader: SwiftShader's libEGL loads its libGLESv2/libGLESv1_CM by a fixed name
#     ("libGLESv2_swiftshader.so"). In the ANGLE package the libs are named lib*_angle.so and the framework
#     libEGL already loads libGLESv2_angle.so: if SwiftShader loaded a COPY with another name
#     there would be two instances with separate state (broken contexts). The _angle names are prepended.
#  2) device/samsung/gtexswifi/swiftangle/: the SwiftAngle package (system APK with the activity
#     android.app.action.ANGLE_FOR_ANDROID and the prebuilt JNI libs) + PRODUCT_PACKAGES in device.mk.
# Idempotent. The prebuilt libs are copied by build-v78 from out/ after compiling SwiftShader.
import shutil, sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")
SS = T / "external/swiftshader/src/OpenGL"
DEV = T / "device/samsung/gtexswifi"
SRC_PKG = Path("/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/swiftangle")

changed = 0
for rel, old, new in (
    ("libGLESv2/libGLESv2.hpp",
     'const char *libGLESv2_lib[] = {"libGLESv2_swiftshader.so", "libGLESv2_swiftshader.so"};',
     'const char *libGLESv2_lib[] = {"libGLESv2_angle.so", "libGLESv2_swiftshader.so"};   /* V78 */'),
    ("libGLES_CM/libGLES_CM.hpp",
     'const char *libGLES_CM_lib[] = {"libGLESv1_CM_swiftshader.so", "libGLESv1_CM_swiftshader.so"};',
     'const char *libGLES_CM_lib[] = {"libGLESv1_CM_angle.so", "libGLESv1_CM_swiftshader.so"};   /* V78 */'),
):
    p = SS / rel
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "V78" in s:
        print(f"{rel}: already patched"); continue
    if s.count(old) != 1:
        print(f"V78_ERROR: {rel} unexpected block"); sys.exit(1)
    p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape"); changed += 1
    print(f"{rel}: nombres _angle antepuestos")

dst = DEV / "swiftangle"
for rel in ("AndroidManifest.xml", "Android.mk", "src/org/lineageos/gtexswifi/swiftangle/AngleActivity.java",
            "assets/a4a_rules.json"):
    d = dst / rel; d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC_PKG / rel, d)
(dst / "lib/armeabi-v7a").mkdir(parents=True, exist_ok=True)
print("swiftangle/: package copied to the device tree")

mk = DEV / "device.mk"
s = mk.read_text(encoding="utf-8", errors="surrogateescape")
if "SwiftAngle" not in s:
    s += ("\n# V78: paquete ANGLE de sistema con SwiftShader (GLES 3.0 por CPU) para apps que lo exigen\n"
          "# (activar por app: settings put global angle_gl_driver_selection_pkgs <pkg> ; ..._values angle)\n"
          "PRODUCT_PACKAGES += SwiftAngle\n")
    mk.write_text(s, encoding="utf-8", errors="surrogateescape"); changed += 1
    print("device.mk: PRODUCT_PACKAGES += SwiftAngle")
else:
    print("device.mk: already has SwiftAngle")
print(f"V78_DONE ({changed} changes)")
