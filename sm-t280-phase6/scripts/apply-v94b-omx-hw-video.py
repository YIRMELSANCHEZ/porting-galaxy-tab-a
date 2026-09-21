#!/usr/bin/env python3
# V94b (VID2, hardware video):
#  1) media_codecs.xml with OMX.sprd.h264.decoder (see media_codecs-hwvideo.xml).
#  2) OMX service rc override (vendor.media.omx) with the audio group: /dev/sprd_vsp is 0660 system:audio
#     and the mediacodec user could not open it ("open SPRD_VSP_DRIVER ERR").
#  3) SprdOMXPlugin::makeComponentInstance: release the component's sp<> BEFORE dlclose when
#     initCheck fails (the virtual destructor lived in the unloaded lib -> SIGSEGV in RefBase::decStrong,
#     the "ABI crash" that motivated V55).
#  4) SwiftShader: priority (nice) of the render threads via property persist.swiftangle.nice.
# Idempotente.
import shutil
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")
D = T / "device/samsung/gtexswifi"
S = Path("/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts")

# 1) media_codecs.xml
mc = D / "configs/media/media_codecs.xml"
if "V94b" not in mc.read_text(encoding="utf-8", errors="surrogateescape"):
    shutil.copyfile(S / "media_codecs-hwvideo.xml", mc)
    print("media_codecs.xml: decodificador H.264 HW")
else:
    print("media_codecs.xml: already patched")

# 2) rc override
rc = D / "system/etc/init/zz-omx-vsp.rc"
rc.parent.mkdir(parents=True, exist_ok=True)
rc_text = """# V94b: mismo servicio que android.hardware.media.omx@1.0-service.rc mas el grupo audio, necesario para
# que el decodificador HW (libomx_avcdec_hw_sprd.so) abra /dev/sprd_vsp (0660 system:audio).
service vendor.media.omx /vendor/bin/hw/android.hardware.media.omx@1.0-service
    override
    class main
    user mediacodec
    group camera drmrpc mediadrm audio
    ioprio rt 4
    writepid /dev/cpuset/foreground/tasks
"""
if not rc.exists() or rc.read_text() != rc_text:
    rc.write_text(rc_text)
    print("zz-omx-vsp.rc: escrito")
dm = D / "device.mk"
s = dm.read_text(encoding="utf-8", errors="surrogateescape")
line = "PRODUCT_COPY_FILES += $(LOCAL_PATH)/system/etc/init/zz-omx-vsp.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/zz-omx-vsp.rc\n"
if "zz-omx-vsp.rc" not in s:
    s += "\n# V94b: servicio OMX con grupo audio (VSP)\n" + line
    dm.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("device.mk: rc override OMX")
else:
    print("device.mk: already has the OMX rc")

# 3) SprdOMXPlugin
p = T / "hardware/sprd/libstagefrighthw/SprdOMXPlugin.cpp"
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V94b" not in s:
    old = """        OMX_ERRORTYPE err = codec->initCheck();
        if (err != OMX_ErrorNone) {
            dlclose(libHandle);
            libHandle = NULL;

            return err;
        }
"""
    new = """        OMX_ERRORTYPE err = codec->initCheck();
        if (err != OMX_ErrorNone) {
            // V94b: destruir el componente (su destructor virtual vive en la lib) ANTES de dlclose;
            // el orden inverso provocaba SIGSEGV en RefBase::decStrong al salir de scope.
            ALOGE("V94b: initCheck failed for %s (0x%x)", name, err);
            codec.clear();
            dlclose(libHandle);
            libHandle = NULL;

            return err;
        }
"""
    if s.count(old) != 1:
        print("V94B_ERROR: SprdOMXPlugin.cpp"); sys.exit(1)
    p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
    print("SprdOMXPlugin.cpp: dlclose after releasing the component")
else:
    print("SprdOMXPlugin.cpp: already patched")

# 4) SwiftShader nice
r = T / "external/swiftshader/src/Renderer/Renderer.cpp"
s = r.read_text(encoding="utf-8", errors="surrogateescape")
if "V94b" not in s:
    old_inc = '#include "Common/Debug.hpp"\n'
    new_inc = old_inc + ('#if defined(__ANDROID__) && defined(__BIONIC__)\n'
                         '#include <cutils/properties.h>   // V94b_NICE\n'
                         '#include <sys/resource.h>\n#include <stdlib.h>\n#endif\n')
    old_fn = "\t\trenderer->threadLoop(threadIndex);\n\t}\n"
    new_fn = ("\t\t#if defined(__ANDROID__) && defined(__BIONIC__)\n"
              "\t\t// V94b: prioridad de los workers por propiedad (heredan el nice -2 del hilo de Unity y\n"
              "\t\t// dejan sin CPU al audio/decodificador/red en las pantallas de video).\n"
              "\t\t{\n"
              "\t\t\tchar v[PROPERTY_VALUE_MAX] = {};\n"
              "\t\t\tif(property_get(\"persist.swiftangle.nice\", v, \"\") > 0)\n"
              "\t\t\t{\n"
              "\t\t\t\tsetpriority(PRIO_PROCESS, 0, atoi(v));\n"
              "\t\t\t}\n"
              "\t\t}\n"
              "\t\t#endif\n\n"
              "\t\trenderer->threadLoop(threadIndex);\n\t}\n")
    if s.count(old_inc) != 1 or s.count(old_fn) != 1:
        print("V94B_ERROR: Renderer.cpp"); sys.exit(1)
    s = s.replace(old_inc, new_inc, 1).replace(old_fn, new_fn, 1)
    r.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("Renderer.cpp: nice via property")
else:
    print("Renderer.cpp: already patched")
print("V94B_DONE")
