#!/usr/bin/env python3
# V94 (VID2, HW video): SwiftShader only accepts YV12 / YCbCr_420_888 as an EGLImage; the decoder
# HW de Spreadtrum (OMX.sprd.h264.decoder) entrega buffers gralloc 0x15 = HAL_PIXEL_FORMAT_YCbCr_420_SP
# (NV12: plano Y + plano CbCr entrelazado) -> "Unsupported EGL image format 21" y video en negro.
# Adds sw::FORMAT_NV12_BT601 (same YUV->RGB sampling as YV12 BT.601 studio swing; the chroma plane
# is addressed with horizontal stride 2 and Cb/Cr as buffer[2]/buffer[1]). Idempotent.
import re
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")
MARK = "V94_NV12"

def patch(path, fn):
    s = path.read_text(encoding="utf-8", errors="surrogateescape")
    if MARK in s:
        print(f"{path.name}: already patched"); return
    s2 = fn(s)
    if s2 is None:
        print(f"V94_ERROR: {path.name}"); sys.exit(1)
    path.write_text(s2, encoding="utf-8", errors="surrogateescape")
    print(f"{path.name}: patched")

# Adds 'case FORMAT_NV12_BT601:' after each 'case FORMAT_YV12_JFIF:' (same indentation, same suffix),
# except in the Kb/Kr block (full swing), where NV12 goes with the BT601 block.
JFIF_RE = re.compile(r"^([ \t]*)case FORMAT_YV12_JFIF:(.*)$(?!\n[ \t]*Kb = )", re.MULTILINE)
def add_cases(s):
    return JFIF_RE.sub(lambda m: m.group(0) + "\n" + m.group(1) + "case FORMAT_NV12_BT601:" +
                       m.group(2).replace("FORMAT_YV12_JFIF", "FORMAT_NV12_BT601"), s)

def surface_hpp(s):
    old = "\t\tFORMAT_YV12_JFIF,    // Full-swing BT.601\n\n\t\tFORMAT_LAST = FORMAT_YV12_JFIF\n"
    new = ("\t\tFORMAT_YV12_JFIF,    // Full-swing BT.601\n"
           "\t\tFORMAT_NV12_BT601,   // " + MARK + ": Y + CbCr entrelazado (HAL 0x15), BT.601 studio swing\n\n"
           "\t\tFORMAT_LAST = FORMAT_NV12_BT601\n")
    return s.replace(old, new, 1) if s.count(old) == 1 else None

def surface_cpp(s):
    n = len(JFIF_RE.findall(s))
    s = add_cases(s)
    print(f"  Surface.cpp: {n} sitios")
    return s + "\n// " + MARK + "\n" if n >= 6 else None

def samplercore_cpp(s):
    old = "\t\t\tcase FORMAT_YV12_BT601:\n\t\t\t\tKb = 0.114f;\n"
    if s.count(old) != 1:
        return None
    s = s.replace(old, "\t\t\tcase FORMAT_YV12_BT601:\n\t\t\tcase FORMAT_NV12_BT601:   // " + MARK + "\n\t\t\t\tKb = 0.114f;\n", 1)
    n = len(JFIF_RE.findall(s))
    s = add_cases(s)
    print(f"  SamplerCore.cpp: {n} sitios")
    return s if n >= 8 else None

def sampler_cpp(s):
    old = ("\t\t\t\t\ttexture.mipmap[1].onePitchP[2] = 1;\n"
           "\t\t\t\t\ttexture.mipmap[1].onePitchP[3] = CStride;\n"
           "\t\t\t\t}\n")
    new = old + ("\t\t\t\telse if(internalTextureFormat == FORMAT_NV12_BT601)   // " + MARK + "\n"
                 "\t\t\t\t{\n"
                 "\t\t\t\t\t// Plano Y (pitch = stride) seguido del plano CbCr entrelazado con el mismo pitch:\n"
                 "\t\t\t\t\t// Cb en bytes pares (U = buffer[2]), Cr en impares (V = buffer[1]); paso horizontal 2.\n"
                 "\t\t\t\t\tunsigned int YStride = pitchP;\n"
                 "\t\t\t\t\tunsigned int YSize = YStride * height;\n\n"
                 "\t\t\t\t\tmipmap.buffer[2] = (byte*)mipmap.buffer[0] + YSize;\n"
                 "\t\t\t\t\tmipmap.buffer[1] = (byte*)mipmap.buffer[2] + 1;\n\n"
                 "\t\t\t\t\ttexture.mipmap[1].width[0] = width / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].width[1] = width / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].width[2] = width / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].width[3] = width / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].height[0] = height / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].height[1] = height / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].height[2] = height / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].height[3] = height / 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].onePitchP[0] = 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].onePitchP[1] = YStride;\n"
                 "\t\t\t\t\ttexture.mipmap[1].onePitchP[2] = 2;\n"
                 "\t\t\t\t\ttexture.mipmap[1].onePitchP[3] = YStride;\n"
                 "\t\t\t\t}\n")
    return s.replace(old, new, 1) if s.count(old) == 1 else None

def image_hpp(s):
    old_def = "#define SW_YV12_JFIF  0x4A315659   // YCrCb 4:2:0 Planar, 16-byte aligned, BT.601 color space, full swing\n"
    new_def = old_def + "#define SW_NV12_BT601 0x3231564E   // " + MARK + ": YCbCr 4:2:0 Semi-Planar (HAL_PIXEL_FORMAT_YCbCr_420_SP 0x15), BT.601 studio swing\n"
    old_map = "\tcase HAL_PIXEL_FORMAT_YV12:      return SW_YV12_BT601;\n"
    new_map = old_map + "\tcase 0x15:                       return SW_NV12_BT601;   // HAL_PIXEL_FORMAT_YCbCr_420_SP (Spreadtrum VSP), " + MARK + "\n"
    if s.count(old_def) != 1 or s.count(old_map) != 1:
        return None
    return s.replace(old_def, new_def, 1).replace(old_map, new_map, 1)

def image_cpp(s):
    old = "\t\tcase SW_YV12_JFIF:  return sw::FORMAT_YV12_JFIF;\n"
    new = old + "\t\tcase SW_NV12_BT601: return sw::FORMAT_NV12_BT601;   // " + MARK + "\n"
    return s.replace(old, new, 1) if s.count(old) == 1 else None

patch(SW / "Renderer/Surface.hpp", surface_hpp)
patch(SW / "Renderer/Surface.cpp", surface_cpp)
patch(SW / "Shader/SamplerCore.cpp", samplercore_cpp)
patch(SW / "Renderer/Sampler.cpp", sampler_cpp)
patch(SW / "OpenGL/common/Image.hpp", image_hpp)
patch(SW / "OpenGL/common/Image.cpp", image_cpp)
print("V94_DONE")
