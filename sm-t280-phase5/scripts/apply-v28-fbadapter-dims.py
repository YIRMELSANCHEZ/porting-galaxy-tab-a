#!/usr/bin/env python3
# V28 (framebuffer dimensions). With V27 HWC2OnFbAdapter is forced and SF no longer
# depends on the SPRD HWC, but:
#   E BufferQueueProducer: [FramebufferSurface] allocateBuffers: failed to allocate
#     buffer (0 x 0, format 1, usage 0x200)
# The adapter copies mFbDevice->width/height from the framebuffer_device_t, and the fb HAL of
# gralloc.sc8830 returns them as 0 (and fps 0 -> int(1e9/fps) invalid). The kernel
# sprdfb SI conoce 800x1280 (panel adjunto).
#
# Fix: in the HWC2OnFbAdapter constructor, if width/height/fps come as 0, read
# FBIOGET_VSCREENINFO from /dev/graphics/fb0 (or /dev/fb0) and fill in with the kernel's.
# Change in composer@2.1-impl (system.img). boot unchanged. Idempotent.
import sys

F = ("/home/lineage/android/lineage-17.1/hardware/interfaces/graphics/composer/"
     "2.1/utils/hwc2onfbadapter/HWC2OnFbAdapter.cpp")
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "V28" in s:
    print("V28_PATCH_ALREADY_PRESENT"); sys.exit(0)

# 1) Includes for open/ioctl/fb_var_screeninfo.
inc_old = "#include <sync/sync.h>\n"
inc_new = (
    "#include <sync/sync.h>\n"
    "// V28: fallback de dimensiones via ioctl al kernel fb0\n"
    "#include <fcntl.h>\n"
    "#include <sys/ioctl.h>\n"
    "#include <linux/fb.h>\n"
)

# 2) Robust population of mFbInfo with a fallback to fb0.
blk_old = (
    "    mFbInfo.name = \"fbdev\";\n"
    "    mFbInfo.width = mFbDevice->width;\n"
    "    mFbInfo.height = mFbDevice->height;\n"
    "    mFbInfo.format = mFbDevice->format;\n"
    "    mFbInfo.vsync_period_ns = int(1e9 / mFbDevice->fps);\n"
    "    mFbInfo.xdpi_scaled = int(mFbDevice->xdpi * 1000.0f);\n"
    "    mFbInfo.ydpi_scaled = int(mFbDevice->ydpi * 1000.0f);\n"
)
blk_new = (
    "    mFbInfo.name = \"fbdev\";\n"
    "    mFbInfo.width = mFbDevice->width;\n"
    "    mFbInfo.height = mFbDevice->height;\n"
    "    mFbInfo.format = mFbDevice->format;\n"
    "    float fbFps = mFbDevice->fps;\n"
    "    mFbInfo.xdpi_scaled = int(mFbDevice->xdpi * 1000.0f);\n"
    "    mFbInfo.ydpi_scaled = int(mFbDevice->ydpi * 1000.0f);\n"
    "    // V28: gralloc.sc8830 framebuffer_open deja width/height/fps a 0 -> el\n"
    "    // FramebufferSurface aloca 0x0 y falla. Leer del kernel sprdfb via fb0.\n"
    "    if (mFbInfo.width == 0 || mFbInfo.height == 0 || fbFps <= 0.0f) {\n"
    "        int fbfd = ::open(\"/dev/graphics/fb0\", O_RDONLY);\n"
    "        if (fbfd < 0) fbfd = ::open(\"/dev/fb0\", O_RDONLY);\n"
    "        if (fbfd >= 0) {\n"
    "            struct fb_var_screeninfo vinfo;\n"
    "            if (ioctl(fbfd, FBIOGET_VSCREENINFO, &vinfo) == 0) {\n"
    "                if (mFbInfo.width == 0) mFbInfo.width = vinfo.xres;\n"
    "                if (mFbInfo.height == 0) mFbInfo.height = vinfo.yres;\n"
    "            }\n"
    "            ::close(fbfd);\n"
    "        }\n"
    "        if (fbFps <= 0.0f) fbFps = 60.0f;\n"
    "        if (mFbInfo.format == 0) mFbInfo.format = 1; // HAL_PIXEL_FORMAT_RGBA_8888\n"
    "        if (mFbInfo.xdpi_scaled == 0) mFbInfo.xdpi_scaled = 160000;\n"
    "        if (mFbInfo.ydpi_scaled == 0) mFbInfo.ydpi_scaled = 160000;\n"
    "        ALOGI(\"V28: fb0 fallback %dx%d fps %f\", int(mFbInfo.width), int(mFbInfo.height), fbFps);\n"
    "    }\n"
    "    mFbInfo.vsync_period_ns = int(1e9 / fbFps);\n"
)

for old in (inc_old, blk_old):
    if s.count(old) != 1:
        print("V28_ANCHOR_ERROR count=%d for: %s" % (s.count(old), old.splitlines()[0])); sys.exit(1)

s = s.replace(inc_old, inc_new).replace(blk_old, blk_new)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V28_PATCH_APPLIED")
