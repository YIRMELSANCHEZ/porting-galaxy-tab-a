#!/usr/bin/env python3
# V92 (CAM1). Camera: the HAL1 blob camera.sc8830.so (5.1) is in /system/lib/hw and its C++ imports
# resuelven contra libgui/libcamera_client/libbinder de A10 (readelf, 2026-09-21); solo falta
# `android_atomic_or` for libmemoryheapion.so (removed from libcutils in A8+). The service is missing
# HIDL android.hardware.camera.provider@2.4-service (variante legacy = CameraModule HAL1) + VINTF.
#  1) libcamera_shim.so with android_atomic_or (device/samsung/gtexswifi/libs/libshims)
#  2) PRODUCT_PACKAGES += android.hardware.camera.provider@2.4-service libcamera_shim
#  3) service rc `override` with LD_SHIM_LIBS for libmemoryheapion.so (in vendor/etc/init, name
#     alphabetically after the module's rc so the override takes effect)
#  4) manifest.xml: android.hardware.camera.provider 2.4 ICameraProvider legacy/0
# Idempotente.
import sys
from pathlib import Path

D = Path("/home/lineage/android/lineage-17.1/device/samsung/gtexswifi")

shim = D / "libs/libshims/camera_shim.cpp"
if not shim.exists():
    shim.write_text('''/* V92: simbolos que libmemoryheapion.so (blob camara 5.1) importa de la libcutils de 5.1 */
#include <stdint.h>
extern "C" int32_t android_atomic_or(int32_t value, volatile int32_t *addr) {
    return __atomic_fetch_or(addr, value, __ATOMIC_RELEASE);
}
extern "C" int32_t android_atomic_and(int32_t value, volatile int32_t *addr) {
    return __atomic_fetch_and(addr, value, __ATOMIC_RELEASE);
}
extern "C" int32_t android_atomic_add(int32_t increment, volatile int32_t *addr) {
    return __atomic_fetch_add(addr, increment, __ATOMIC_RELEASE);
}
extern "C" int32_t android_atomic_inc(volatile int32_t *addr) { return android_atomic_add(1, addr); }
extern "C" int32_t android_atomic_dec(volatile int32_t *addr) { return android_atomic_add(-1, addr); }
''', encoding="utf-8")
    print("camera_shim.cpp creado")
else:
    print("camera_shim.cpp already exists")

mk = D / "libs/libshims/Android.mk"
s = mk.read_text(encoding="utf-8")
if "libcamera_shim" not in s:
    s += '''
# V92: shim para libmemoryheapion.so (camara)
include $(CLEAR_VARS)
LOCAL_SRC_FILES := camera_shim.cpp
LOCAL_MODULE := libcamera_shim
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_CLASS := SHARED_LIBRARIES
include $(BUILD_SHARED_LIBRARY)
'''
    mk.write_text(s, encoding="utf-8"); print("libshims/Android.mk: libcamera_shim")
else:
    print("libshims/Android.mk: already has libcamera_shim")

rc = D / "system/etc/init/zz-camera-provider-shim.rc"
rc.parent.mkdir(parents=True, exist_ok=True)
rc.write_text('''# V92: mismo servicio que android.hardware.camera.provider@2.4-service.rc del modulo, con LD_SHIM_LIBS
# para el blob 5.1 libmemoryheapion.so (android_atomic_or). `override` sustituye la definicion previa.
service vendor.camera-provider-2-4 /vendor/bin/hw/android.hardware.camera.provider@2.4-service
    override
    interface android.hardware.camera.provider@2.4::ICameraProvider legacy/0
    class hal
    user cameraserver
    group audio camera input drmrpc system
    ioprio rt 4
    capabilities SYS_NICE
    setenv LD_SHIM_LIBS /system/lib/libmemoryheapion.so|libcamera_shim.so
    writepid /dev/cpuset/camera-daemon/tasks /dev/stune/top-app/tasks
''', encoding="utf-8")
print("zz-camera-provider-shim.rc escrito")

dm = D / "device.mk"
s = dm.read_text(encoding="utf-8", errors="surrogateescape")
if "android.hardware.camera.provider@2.4-service" not in s:
    s += ('''
# V92: camara (HAL1 blob camera.sc8830.so via provider@2.4 legacy + shim android_atomic_or)
PRODUCT_PACKAGES += \\
    android.hardware.camera.provider@2.4-service \\
    android.hardware.camera.provider@2.4-impl \\
    libcamera_shim
PRODUCT_COPY_FILES += \\
    $(LOCAL_PATH)/system/etc/init/zz-camera-provider-shim.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/zz-camera-provider-shim.rc
''')
    dm.write_text(s, encoding="utf-8", errors="surrogateescape"); print("device.mk: camera provider + shim")
elif "android.hardware.camera.provider@2.4-impl" not in s:
    s = s.replace("    android.hardware.camera.provider@2.4-service \\\n",
                  "    android.hardware.camera.provider@2.4-service \\\n    android.hardware.camera.provider@2.4-impl \\\n", 1)
    dm.write_text(s, encoding="utf-8", errors="surrogateescape"); print("device.mk: +camera.provider@2.4-impl")
else:
    print("device.mk: already has camera provider")

man = D / "manifest.xml"
s = man.read_text(encoding="utf-8")
if "android.hardware.camera.provider" not in s:
    entry = '''    <hal format="hidl">
        <name>android.hardware.camera.provider</name>
        <transport>hwbinder</transport>
        <version>2.4</version>
        <interface>
            <name>ICameraProvider</name>
            <instance>legacy/0</instance>
        </interface>
    </hal>
</manifest>'''
    if s.count("</manifest>") != 1:
        print("V92_ERROR: unexpected manifest.xml"); sys.exit(1)
    man.write_text(s.replace("</manifest>", entry, 1), encoding="utf-8"); print("manifest.xml: camera.provider 2.4 legacy/0")
else:
    print("manifest.xml: already has camera.provider")
print("V92_DONE")
