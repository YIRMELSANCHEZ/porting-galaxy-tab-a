#!/usr/bin/env python3
# V30 (DIAGNOSTIC, not a fix). With V29 the gralloc takes the ION-copy path for HW_FB and
# APPEARS to succeed (no AERR), but SurfaceFlinger (228) reports
# "GraphicBufferAllocator: Failed to allocate 800x1280 usage 1a00: 5 (NO_RESOURCES)".
# The gralloc runs in the allocator@2.0-service (216) and logs no failure -> contradiction.
# V30 instruments 3 points to resolve it in one flash:
#  (1) gralloc: resultado de ion_alloc (heap/size/ret) SIEMPRE.
#  (2) gralloc: valor de retorno final de alloc_device_alloc.
#  (3) allocator@2.0 passthrough: the `result` of mDevice->alloc() and the Error returned.
# Change in system.img (gralloc.sc8830 + allocator@2.0-impl). boot unchanged. Idempotent.
import sys

GR = "/home/lineage/android/lineage-17.1/hardware/sprd/gralloc/scx30g_v2/alloc_device.cpp"
PT = ("/home/lineage/android/lineage-17.1/hardware/interfaces/graphics/allocator/"
      "2.0/utils/passthrough/include/allocator-passthrough/2.0/Gralloc0Hal.h")

# --- (1)+(2) gralloc ---
g = open(GR, encoding="utf-8", errors="surrogateescape").read()
if "V30" not in g:
    ion_old = "\t\tret = ion_alloc(m->ion_client, size, 0, ion_heap_mask, ion_flag, &(ion_hnd));\n"
    ion_new = (ion_old +
        "\t\tALOGE(\"V30 ion_alloc: heap=0x%x size=%zu flag=0x%x ret=%d client=%d\","
        " ion_heap_mask, size, ion_flag, ret, m->ion_client);\n")
    ret_old = "\t*pStride = stride;\n\treturn 0;\n}\n\nstatic int alloc_device_free"
    ret_new = ("\t*pStride = stride;\n"
        "\tALOGE(\"V30 alloc_device_alloc OK: w=%d h=%d fmt=0x%x usage=0x%x stride=%zu\","
        " w, h, format, usage, (size_t)stride);\n"
        "\treturn 0;\n}\n\nstatic int alloc_device_free")
    for old in (ion_old, ret_old):
        if g.count(old) != 1:
            print("V30_GR_ANCHOR_ERROR count=%d for %s" % (g.count(old), old.splitlines()[0])); sys.exit(1)
    g = g.replace(ion_old, ion_new).replace(ret_old, ret_new)
    open(GR, "w", encoding="utf-8", errors="surrogateescape").write(g)
    print("V30_GRALLOC_APPLIED")
else:
    print("V30_GRALLOC_ALREADY")

# --- (3) allocator passthrough ---
p = open(PT, encoding="utf-8", errors="surrogateescape").read()
if "V30" not in p:
    pt_old = (
        "        int result = mDevice->alloc(mDevice, info.width, info.height, static_cast<int>(info.format),\n"
        "                                    info.usage, &buffer, &stride);\n"
    )
    pt_new = (pt_old +
        "        ALOGE(\"V30 passthrough alloc: %ux%u fmt=%d usage=0x%llx result=%d\",\n"
        "              info.width, info.height, static_cast<int>(info.format),\n"
        "              (unsigned long long)info.usage, result);\n")
    if p.count(pt_old) != 1:
        print("V30_PT_ANCHOR_ERROR count=%d" % p.count(pt_old)); sys.exit(1)
    p = p.replace(pt_old, pt_new)
    open(PT, "w", encoding="utf-8", errors="surrogateescape").write(p)
    print("V30_PASSTHROUGH_APPLIED")
else:
    print("V30_PASSTHROUGH_ALREADY")
