#!/usr/bin/env python3
# V98: camera. Two causes measured live on 2026-09-21 on top of V95 (see results/fase-6/CAMERA-V98.md):
#  1) Android 10's linker no longer understands LD_SHIM_LIBS, so the V92 shim was never loaded and
#     camera.sc8830.so failed on dlopen ("cannot locate symbol android_atomic_or"). LD_PRELOAD does work
#     (tested by hand): the rc switches to using it.
#  2) With the shim loaded, the Spreadtrum 5.1 HAL calls get_memory with user=NULL from its
#     preasignacion (pre_alloc_cap_mem_thread) y CameraDevice::sGetMemory desreferencia NULL (SIGSEGV en
#     camera.device@1.0-impl). The open instance is saved in a static pointer and used when the
#     HAL does not pass user. Idempotent.
import pathlib, re, sys

T = pathlib.Path("/home/lineage/android/lineage-17.1")
D = T / "device/samsung/gtexswifi"
SRC = T / "hardware/interfaces/camera/device/1.0/default/CameraDevice.cpp"
RC = D / "system/etc/init/zz-camera-provider-shim.rc"
MARK = "V98"

s = SRC.read_text()
if MARK in s:
    print("CameraDevice.cpp: already patched")
else:
    # static pointer to the last open instance
    anchor = "// shared memory methods\n"
    if anchor not in s:
        sys.exit("ERROR: 'shared memory methods' anchor not found")
    s = s.replace(anchor,
        "// V98: el HAL 5.1 de Spreadtrum llama a los callbacks con user=NULL (get_memory desde su hilo de\n"
        "// preasignacion). Solo hay una camara abierta a la vez en este dispositivo.\n"
        "static CameraDevice* sV98LastOpened = nullptr;\n"
        "static inline CameraDevice* v98_device(void* user) {\n"
        "    CameraDevice* d = static_cast<CameraDevice*>(user);\n"
        "    return d != nullptr ? d : sV98LastOpened;\n"
        "}\n\n" + anchor, 1)
    # the four static callbacks
    n = s.count("CameraDevice* object = static_cast<CameraDevice*>(user);")
    if n != 4:
        sys.exit("ERROR: expected 4 user casts, got %d" % n)
    s = s.replace("CameraDevice* object = static_cast<CameraDevice*>(user);",
                  "CameraDevice* object = v98_device(user);   // V98")
    # guard in sGetMemory: if it is still null, do not dereference
    old = ("    CameraDevice* object = v98_device(user);   // V98\n"
           "    if (object->mDeviceCallback == nullptr) {\n"
           "        ALOGE(\"%s: camera HAL request memory while camera is not opened!\", __FUNCTION__);")
    new = ("    CameraDevice* object = v98_device(user);   // V98\n"
           "    if (object == nullptr || object->mDeviceCallback == nullptr) {\n"
           "        ALOGE(\"%s: camera HAL request memory while camera is not opened!\", __FUNCTION__);")
    if old not in s:
        sys.exit("ERROR: sGetMemory block not found")
    s = s.replace(old, new, 1)
    # register the instance before opening the HAL (the pre-allocation thread starts inside open)
    old = "    int rc = OK;\n    if (mModule->getModuleApiVersion() >= CAMERA_MODULE_API_VERSION_2_3 &&"
    if old not in s:
        sys.exit("ERROR: open() block not found")
    s = s.replace(old, "    sV98LastOpened = this;   // V98\n" + old, 1)
    SRC.write_text(s)
    print("CameraDevice.cpp: V98 applied")

r = RC.read_text()
if "LD_PRELOAD" in r:
    print("zz-camera-provider-shim.rc: already uses LD_PRELOAD")
else:
    r2 = re.sub(r"^\s*setenv LD_SHIM_LIBS .*$",
                "    setenv LD_PRELOAD /system/lib/libcamera_shim.so   # V98: el linker de A10 no tiene LD_SHIM_LIBS",
                r, flags=re.M)
    if r2 == r:
        sys.exit("ERROR: LD_SHIM_LIBS line not found in the rc")
    RC.write_text(r2)
    print("zz-camera-provider-shim.rc: LD_PRELOAD")
print("V98_DONE")
