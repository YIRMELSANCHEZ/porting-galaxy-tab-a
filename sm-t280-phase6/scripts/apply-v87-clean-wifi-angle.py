#!/usr/bin/env python3
# V87: hardening iteration on top of V86.
#  1) Removes the V82/V83 diagnostic traces from SwiftShader.
#  2) Retries finit_module(sprdwl) only when the kernel returns EPERM because SDIO/CP2
#     is not ready yet (30 x 500 ms). EEXIST remains success.
#  3) Persists the target app's ANGLE opt-in via the APK's BOOT_COMPLETED receiver.
#  4) Allows halving (2x) the resolution of the ANativeWindow used by SwiftAngle; the property
#     persist.swiftangle.scale allows 1..4 without rebuilding (default 2).
# Idempotente. No incorpora camera ni GNSS.
import shutil
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")
SS = T / "external/swiftshader/src"
DEV = T / "device/samsung/gtexswifi"
SRC_PKG = Path("/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/swiftangle")


def replace_once(path, old, new, label):
    s = path.read_text(encoding="utf-8", errors="surrogateescape")
    if old not in s:
        print(f"V87_ERROR: {label}: block not found in {path}")
        sys.exit(1)
    if s.count(old) != 1:
        print(f"V87_ERROR: {label}: non-unique block ({s.count(old)}) en {path}")
        sys.exit(1)
    path.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")


def remove_v82():
    p = SS / "OpenGL/libEGL/libEGL.cpp"
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "/* V82 */" in s:
        edits = [
            ("#include <system/window.h>\n#include <android/log.h>   /* V82 */\n"
             '#define SSLOG(...) __android_log_print(ANDROID_LOG_INFO, "SwiftShader", __VA_ARGS__)\n',
             "#include <system/window.h>\n"),
            ("\tEGLSurface s = display->createWindowSurface((EGLNativeWindowType)native_window, config, attrib_list);   /* V82 */\n"
             '\tSSLOG("EGL: CreateWindowSurface window=%p config=%p -> surface=%p", native_window, config, s);\n'
             "\treturn s;\n",
             "\treturn display->createWindowSurface((EGLNativeWindowType)native_window, config, attrib_list);\n"),
            ('\tSSLOG("EGL: DestroySurface surface=%p", surface);   /* V82 */\n'
             "\tdisplay->destroySurface((egl::Surface*)surface);\n",
             "\tdisplay->destroySurface((egl::Surface*)surface);\n"),
        ]
        for old, new in edits:
            if s.count(old) != 1:
                print("V87_ERROR: cannot remove V82 from libEGL.cpp")
                sys.exit(1)
            s = s.replace(old, new, 1)
        p.write_text(s, encoding="utf-8", errors="surrogateescape")

    p = SS / "OpenGL/libEGL/Display.cpp"
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    marker = 'extern "C" int __android_log_print(int prio, const char *tag, const char *fmt, ...);\n'
    if "/* V82 */" in s or marker in s:
        if s.count(marker) != 1:
            print("V87_ERROR: declaracion V82 inesperada en Display.cpp")
            sys.exit(1)
        s = s.replace(marker, "", 1)
        old = ('\tif(hasExistingWindowSurface(window))\n\t{\n'
               '\t\t__android_log_print(6, "SwiftShader", "EGL: createWindowSurface: window %p ya tiene surface -> EGL_BAD_ALLOC", (void*)window);   /* V82 */\n'
               '\t\treturn error(EGL_BAD_ALLOC, EGL_NO_SURFACE);\n\t}\n')
        new = ('\tif(hasExistingWindowSurface(window))\n\t{\n'
               '\t\treturn error(EGL_BAD_ALLOC, EGL_NO_SURFACE);\n\t}\n')
        if s.count(old) != 1:
            print("V87_ERROR: unexpected V82 log in Display.cpp")
            sys.exit(1)
        p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")

    p = SS / "Main/FrameBufferAndroid.cpp"
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "/* V82 */" in s:
        edits = [
            ("#include <system/window.h>\n#include <android/log.h>   /* V82 */\n#include <errno.h>\n#include <string.h>\n"
             '#define SSLOG(...) __android_log_print(ANDROID_LOG_INFO, "SwiftShader", __VA_ARGS__)\n'
             '#define SSLOGE(...) __android_log_print(ANDROID_LOG_ERROR, "SwiftShader", __VA_ARGS__)\n',
             "#include <system/window.h>\n"),
            ('\t\tint rc = native_window_set_usage(nativeWindow, GRALLOC_USAGE_SW_READ_OFTEN | GRALLOC_USAGE_SW_WRITE_OFTEN);\n'
             '\t\tSSLOG("FrameBufferAndroid: window=%p %dx%d set_usage rc=%d", window, width, height, rc);   /* V82 */\n',
             "\t\tnative_window_set_usage(nativeWindow, GRALLOC_USAGE_SW_READ_OFTEN | GRALLOC_USAGE_SW_WRITE_OFTEN);\n"),
            ('\t\tSSLOG("~FrameBufferAndroid: window=%p", nativeWindow);   /* V82 */\n', ""),
            ('\t\t\tint rc = queueBuffer(nativeWindow, buffer, -1);\n'
             '\t\t\tstatic int nq = 0;   /* V82 */\n'
             '\t\t\tif(rc != 0 || nq < 3) { SSLOG("FrameBufferAndroid: queueBuffer window=%p buffer=%p rc=%d (%s)", nativeWindow, buffer, rc, strerror(-rc)); }\n'
             "\t\t\tnq++;\n",
             "\t\t\tqueueBuffer(nativeWindow, buffer, -1);\n"),
            ('\t\tint rc = dequeueBuffer(nativeWindow, &buffer);   /* V82 */\n'
             "\t\tif(rc != 0)\n\t\t{\n"
             '\t\t\tSSLOGE("FrameBufferAndroid: dequeueBuffer window=%p rc=%d (%s)", nativeWindow, rc, strerror(-rc));\n'
             "\t\t\treturn nullptr;\n\t\t}\n"
             "\t\t{\n\t\t\tstatic int nd = 0;\n"
             '\t\t\tif(nd < 3) { SSLOG("FrameBufferAndroid: dequeueBuffer window=%p buffer=%p %dx%d fmt=%d stride=%d", nativeWindow, buffer, buffer->width, buffer->height, buffer->format, buffer->stride); }\n'
             "\t\t\tnd++;\n\t\t}\n",
             "\t\tif(dequeueBuffer(nativeWindow, &buffer) != 0)\n\t\t{\n\t\t\treturn nullptr;\n\t\t}\n"),
            ('\t\t\tSSLOGE("FrameBufferAndroid: gralloc lock failed buffer=%p", buffer);   /* V82 */\n'
             "\t\t\treturn nullptr;",
             "\t\t\tTRACE(\"%s failed to lock buffer %p\", __FUNCTION__, buffer);\n\t\t\treturn nullptr;"),
        ]
        for old, new in edits:
            if s.count(old) != 1:
                print("V87_ERROR: cannot remove V82 from FrameBufferAndroid.cpp")
                sys.exit(1)
            s = s.replace(old, new, 1)
        p.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("V87: trazas V82 retiradas")


def remove_v83():
    p = SS / "OpenGL/libGLESv2/Context.cpp"
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "/* V83 */" not in s:
        print("V87: V83 traces already absent")
        return
    helper = '''#include "Sampler.h"
#include <android/log.h>   /* V83 */
#define SSLOG(...) __android_log_print(ANDROID_LOG_INFO, "SwiftShader", __VA_ARGS__)
namespace es2 {
static void ssLogDraw(const char *what, Context *ctx, Framebuffer *fb, GLuint fbName, GLuint prog, int vpW, int vpH, GLenum mode, int count, int inst)
{
\tstatic int n = 0;
\tn++;
\tif(n > 150 && (n % 500) != 0) return;
\tint w = 0, h = 0, fmt = 0, samples = 0;
\tGLenum status = fb ? fb->completeness(w, h, samples) : 0;
\tRenderbuffer *cb = fb ? fb->getColorbuffer(0) : nullptr;
\tif(cb) { fmt = cb->getFormat(); }
\tSSLOG("GL %s #%d fbo=%u status=0x%x rt=%dx%d fmt=0x%x prog=%u vp=%dx%d mode=%u count=%d inst=%d", what, n, fbName, status, w, h, fmt, prog, vpW, vpH, mode, count, inst);
}
}
'''
    edits = [
        (helper, '#include "Sampler.h"\n'),
        ('void Context::clear(GLbitfield mask)\n{\n\t{\n\t\tstatic int nc = 0;   /* V83 */\n'
         '\t\tif(nc < 60) { SSLOG("GL clear #%d fbo=%u mask=0x%x color=%.2f,%.2f,%.2f,%.2f", nc, mState.drawFramebuffer, mask, mState.colorClearValue.red, mState.colorClearValue.green, mState.colorClearValue.blue, mState.colorClearValue.alpha); }\n'
         '\t\tnc++;\n\t}\n',
         'void Context::clear(GLbitfield mask)\n{\n'),
        ('\tif(!applyRenderTarget())\n\t{\n\t\tSSLOG("GL drawArrays: applyRenderTarget FAILED fbo=%u", mState.drawFramebuffer);   /* V83 */\n\t\treturn;\n\t}\n',
         '\tif(!applyRenderTarget())\n\t{\n\t\treturn;\n\t}\n'),
        ('\tssLogDraw("drawArrays", this, getDrawFramebuffer(), mState.drawFramebuffer, mState.currentProgram, mState.viewportWidth, mState.viewportHeight, mode, count, instanceCount);   /* V83 */\n', ""),
        ('\tif(!applyRenderTarget())\n\t{\n\t\tSSLOG("GL drawElements: applyRenderTarget FAILED fbo=%u", mState.drawFramebuffer);   /* V83 */\n\t\treturn;\n\t}\n',
         '\tif(!applyRenderTarget())\n\t{\n\t\treturn;\n\t}\n'),
        ('\tssLogDraw("drawElements", this, getDrawFramebuffer(), mState.drawFramebuffer, mState.currentProgram, mState.viewportWidth, mState.viewportHeight, mode, count, instanceCount);   /* V83 */\n', ""),
        ('\tFramebuffer *readFramebuffer = getReadFramebuffer();\n\tFramebuffer *drawFramebuffer = getDrawFramebuffer();\n'
         '\t{\n\t\tstatic int nb = 0;   /* V83 */\n'
         '\t\tif(nb < 30) { SSLOG("GL blitFramebuffer #%d read=%u draw=%u src=%d,%d-%d,%d dst=%d,%d-%d,%d mask=0x%x", nb, mState.readFramebuffer, mState.drawFramebuffer, srcX0, srcY0, srcX1, srcY1, dstX0, dstY0, dstX1, dstY1, mask); }\n'
         '\t\tnb++;\n\t}\n',
         '\tFramebuffer *readFramebuffer = getReadFramebuffer();\n\tFramebuffer *drawFramebuffer = getDrawFramebuffer();\n'),
    ]
    for old, new in edits:
        if s.count(old) != 1:
            print("V87_ERROR: cannot remove V83 from Context.cpp")
            sys.exit(1)
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("V87: trazas V83 retiradas")


def patch_wifi_retry():
    p = T / "frameworks/opt/net/wifi/libwifi_hal/wifi_hal_common.cpp"
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "V87_WIFI_SDIO_RETRY" in s:
        print("V87: Wi-Fi retry already applied")
        return
    old = '''  ret = syscall(__NR_finit_module, fd, args, 0);

  close(fd);
  if (ret < 0) {
    if (errno == EEXIST) {
      // Modulo ya cargado (kernel 3.10 sin rmmod limpio / ciclo enable-disable).
      // El driver ya esta operativo (wlan0 up): tratar como exito.
      ret = 0;
    } else {
      PLOG(ERROR) << "finit_module return: " << ret;
    }
  }
'''
    new = '''  // V87_WIFI_SDIO_RETRY: sprdwl devuelve -EPERM mientras el firmware CP2 aun
  // esta preparando SDIO. Reintentar solo ese error evita la carrera de arranque sin
  // ocultar fallos reales del modulo. 30 x 500 ms = 15 s maximo.
  int retries = 30;
  while (true) {
    ret = syscall(__NR_finit_module, fd, args, 0);
    if (ret == 0) break;

    const int module_errno = errno;
    if (module_errno == EEXIST) {
      ret = 0;
      break;
    }
    if (module_errno != EPERM || retries-- == 0) {
      errno = module_errno;
      PLOG(ERROR) << "finit_module return: " << ret;
      break;
    }

    LOG(WARNING) << "sprdwl: SDIO/CP2 not ready (EPERM), retrying in 500 ms; "
                 << retries << " retries left";
    usleep(500000);
  }

  close(fd);
'''
    if s.count(old) != 1:
        print("V87_ERROR: unexpected V48 insmod body")
        sys.exit(1)
    p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
    print("V87: bounded sprdwl retry applied")


def patch_swiftangle_scale():
    p = SS / "OpenGL/libEGL/Surface.cpp"
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "V88_SCALE_EGL" in s:
        print("V87: scaling replaced by the V88 implementation")
        return
    if "V87_SWIFTANGLE_SCALE" in s:
        old_host_incompatible = ('#include <cutils/properties.h>\n'
                                 '#include <stdlib.h>\n'
                                 '#include <system/window.h>\n')
        host_compatible = ('#include <stdlib.h>\n'
                           '#include <system/window.h>\n'
                           '// La variante host de SwiftShader no dispone de sys/system_properties.h,\n'
                           '// pero ambos targets enlazan libcutils. Declarar solo la ABI necesaria.\n'
                           'extern "C" int property_get(const char *key, char *value, const char *default_value);\n'
                           '#ifndef PROPERTY_VALUE_MAX\n'
                           '#define PROPERTY_VALUE_MAX 92\n'
                           '#endif\n')
        if old_host_incompatible in s:
            p.write_text(s.replace(old_host_incompatible, host_compatible, 1),
                         encoding="utf-8", errors="surrogateescape")
            print("V87: SwiftAngle scaling adjusted for the host variant")
            s = p.read_text(encoding="utf-8", errors="surrogateescape")
        target_guard_old = "#if defined(__ANDROID__)\n#include <stdlib.h>\n#include <system/window.h>\n"
        target_guard_new = "#include <stdlib.h>\n#if defined(__ANDROID__) && defined(__BIONIC__)\n#include <system/window.h>\n"
        if target_guard_old in s:
            s = s.replace(target_guard_old, target_guard_new, 1)
        constructor_guard = "\t#if defined(__ANDROID__)\n\t// V87_SWIFTANGLE_SCALE:"
        if constructor_guard in s:
            s = s.replace(constructor_guard,
                          "\t#if defined(__ANDROID__) && defined(__BIONIC__)\n\t// V87_SWIFTANGLE_SCALE:", 1)
        p.write_text(s, encoding="utf-8", errors="surrogateescape")
        print("V87: SwiftAngle scaling already applied (Android/Bionic only)")
        return
    include_anchor = '#include "Main/FrameBuffer.hpp"\n'
    includes = (include_anchor +
                '\n#include <stdlib.h>\n'
                '#if defined(__ANDROID__) && defined(__BIONIC__)\n'
                '#include <system/window.h>\n'
                '// La variante host de SwiftShader no dispone de sys/system_properties.h,\n'
                '// pero ambos targets enlazan libcutils. Declarar solo la ABI necesaria.\n'
                'extern "C" int property_get(const char *key, char *value, const char *default_value);\n'
                '#ifndef PROPERTY_VALUE_MAX\n'
                '#define PROPERTY_VALUE_MAX 92\n'
                '#endif\n'
                '#endif\n')
    if s.count(include_anchor) != 1:
        print("V87_ERROR: unexpected Surface.cpp include anchor")
        sys.exit(1)
    s = s.replace(include_anchor, includes, 1)
    old = '''{
	pixelAspectRatio = (EGLint)(1.0 * EGL_DISPLAY_SCALING);   // FIXME: Determine actual pixel aspect ratio
}
'''
    new = '''{
	pixelAspectRatio = (EGLint)(1.0 * EGL_DISPLAY_SCALING);   // FIXME: Determine actual pixel aspect ratio

	#if defined(__ANDROID__) && defined(__BIONIC__)
	// V87_SWIFTANGLE_SCALE: SwiftShader rasteriza por CPU; reducir solo su buffer baja
	// el numero de pixeles sin alterar la resolucion del sistema/Mali. SurfaceFlinger
	// escala el buffer al tamano del SurfaceView. 1 desactiva; rango seguro 1..4.
	char scaleValue[PROPERTY_VALUE_MAX] = {};
	property_get("persist.swiftangle.scale", scaleValue, "2");
	const int scale = atoi(scaleValue);
	if(scale >= 2 && scale <= 4)
	{
		int nativeWidth = 0;
		int nativeHeight = 0;
		window->query(window, NATIVE_WINDOW_WIDTH, &nativeWidth);
		window->query(window, NATIVE_WINDOW_HEIGHT, &nativeHeight);
		const int scaledWidth = nativeWidth / scale;
		const int scaledHeight = nativeHeight / scale;
		if(scaledWidth >= 320 && scaledHeight >= 200)
		{
			(void)native_window_set_buffers_dimensions(window, scaledWidth, scaledHeight);
		}
	}
	#endif
}
'''
    if s.count(old) != 1:
        print("V87_ERROR: unexpected WindowSurface constructor")
        sys.exit(1)
    p.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
    print("V87: SwiftAngle scaling 1..4 applied (default 2)")


def install_swiftangle_receiver():
    dst = DEV / "swiftangle"
    files = (
        "AndroidManifest.xml",
        "Android.mk",
        "src/org/lineageos/gtexswifi/swiftangle/AngleActivity.java",
        "src/org/lineageos/gtexswifi/swiftangle/BootCompletedReceiver.java",
        "assets/a4a_rules.json",
    )
    for rel in files:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SRC_PKG / rel, target)
    print("V87: receptor BOOT_COMPLETED instalado en SwiftAngle")

    mk = DEV / "device.mk"
    s = mk.read_text(encoding="utf-8", errors="surrogateescape")
    if "persist.swiftangle.scale" not in s:
        s += ("\n# V87: la app objetivo usa SwiftShader por CPU; 2 reduce 1280x800 a 640x400 solo en SwiftAngle.\n"
              "# Se puede probar 1..4 por ADB sin reflashear y reiniciando la app.\n"
              "PRODUCT_PROPERTY_OVERRIDES += persist.swiftangle.scale=2\n")
        mk.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("V87: persist.swiftangle.scale=2")


remove_v82()
remove_v83()
patch_wifi_retry()
patch_swiftangle_scale()
install_swiftangle_receiver()
print("V87_DONE")
