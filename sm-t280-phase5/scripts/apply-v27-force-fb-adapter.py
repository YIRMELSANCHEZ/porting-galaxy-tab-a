#!/usr/bin/env python3
# V27 (unblock the display, strategic pivot). With V26, SurfaceFlinger composes
# and the graphics HIDL stack works, but the Spreadtrum HWC (via HWC2On1Adapter) does not present:
#   GraphicBufferAllocator: Failed to allocate 800x1280 fmt 1 usage 3000000: 5 (NO_RESOURCES)
#   SPRDHWComposer: SprdPrimaryPlane::open failed  (+ Init EGL ENV failed)
# The gralloc.sc8830 blob alloc() fails to reserve the overlay buffer (usage with
# private bits 0x1000000|0x2000000) -> the HWC does not start its internal GPU compositor.
# It is a failure INSIDE the blob (overlay ION heap) -> not patchable.
#
# Pivot: composer@2.1-impl (HwcLoader.h) chooses HWC2On1Adapter if it loads the HWC
# module, or HWC2OnFbAdapter (framebuffer) if there is only gralloc. We force the
# framebuffer path: SurfaceFlinger composes in its GLES RenderEngine (which ALREADY works: EGL
# 1.4 Mali initialized) and presents to fb0 (sprdfb, already open), avoiding the broken
# HWC overlay. It is the classic bring-up fallback (SW/GLES composition).
#
# Parche: HwcLoader::loadModule() salta hw_get_module(HWC) y usa gralloc directamente.
# Change in composer@2.1-impl (system.img). boot unchanged. Idempotent.
import sys

F = ("/home/lineage/android/lineage-17.1/hardware/interfaces/graphics/composer/"
     "2.1/utils/passthrough/include/composer-passthrough/2.1/HwcLoader.h")
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "V27: force framebuffer adapter" in s:
    print("V27_PATCH_ALREADY_PRESENT"); sys.exit(0)

old = (
    "    static const hw_module_t* loadModule() {\n"
    "        const hw_module_t* module;\n"
    "        int error = hw_get_module(HWC_HARDWARE_MODULE_ID, &module);\n"
    "        if (error) {\n"
    "            ALOGI(\"falling back to gralloc module\");\n"
    "            error = hw_get_module(GRALLOC_HARDWARE_MODULE_ID, &module);\n"
    "        }\n"
)
new = (
    "    static const hw_module_t* loadModule() {\n"
    "        const hw_module_t* module;\n"
    "        // V27: force framebuffer adapter. El HWC Spreadtrum (hwcomposer.sc8830)\n"
    "        // falla al alocar su buffer de overlay en gralloc0; saltamos el modulo\n"
    "        // HWC y usamos gralloc -> HWC2OnFbAdapter (SF compone por GLES a fb0).\n"
    "        ALOGI(\"V27: skipping HWC module; forcing gralloc/framebuffer adapter\");\n"
    "        int error = hw_get_module(GRALLOC_HARDWARE_MODULE_ID, &module);\n"
)

if s.count(old) != 1:
    print("V27_PATCH_ANCHOR_ERROR count=%d" % s.count(old)); sys.exit(1)

s = s.replace(old, new)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V27_PATCH_APPLIED")
