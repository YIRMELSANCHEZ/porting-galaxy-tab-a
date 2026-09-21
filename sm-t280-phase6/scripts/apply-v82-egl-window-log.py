#!/usr/bin/env python3
# V82 (APP: SwiftAngle, diagnostic). With V81 the app renders (4 threads at 100%) but SurfaceFlinger
# rejects every dequeueBuffer of the SurfaceView with "BufferQueue has no connected producer" and before that the
# framework warns "EGLNativeWindowType disconnect failed" (BufferQueue "[]" not connected). With the Mali
# the same SurfaceView (RGB_565) queues frames without errors. This patch only adds traces (liblog, tag
# SwiftShader) en libEGL de SwiftShader: creacion/destruccion de window surfaces (puntero de ventana),
# rejection due to an already-used window, and in FrameBufferAndroid the result of dequeue/queue per window.
# Idempotente.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")
LOGDECL = 'extern "C" int __android_log_print(int prio, const char *tag, const char *fmt, ...);\n'

def patch(rel, edits):
    p = T / rel
    s = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "V82" in s:
        print(f"{rel}: already patched"); return
    for old, new in edits:
        if s.count(old) != 1:
            print(f"V82_ERROR: {rel}: unique block not found: {old[:60]!r}"); sys.exit(1)
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8", errors="surrogateescape")
    print(f"{rel}: trazas V82")

patch("OpenGL/libEGL/libEGL.cpp", [
    ("#include <system/window.h>\n",
     "#include <system/window.h>\n#include <android/log.h>   /* V82 */\n"
     '#define SSLOG(...) __android_log_print(ANDROID_LOG_INFO, "SwiftShader", __VA_ARGS__)\n'),
    ('''	return display->createWindowSurface((EGLNativeWindowType)native_window, config, attrib_list);
}
''',
     '''	EGLSurface s = display->createWindowSurface((EGLNativeWindowType)native_window, config, attrib_list);   /* V82 */
	SSLOG("EGL: CreateWindowSurface window=%p config=%p -> surface=%p", native_window, config, s);
	return s;
}
'''),
    ('''	display->destroySurface((egl::Surface*)surface);

	return success(EGL_TRUE);''',
     '''	SSLOG("EGL: DestroySurface surface=%p", surface);   /* V82 */
	display->destroySurface((egl::Surface*)surface);

	return success(EGL_TRUE);'''),
])

patch("OpenGL/libEGL/Display.cpp", [
    ("EGLSurface Display::createWindowSurface(",
     LOGDECL + "EGLSurface Display::createWindowSurface("),
    ('''	if(hasExistingWindowSurface(window))
	{
		return error(EGL_BAD_ALLOC, EGL_NO_SURFACE);
	}
''',
     '''	if(hasExistingWindowSurface(window))
	{
		__android_log_print(6, "SwiftShader", "EGL: createWindowSurface: window %p ya tiene surface -> EGL_BAD_ALLOC", (void*)window);   /* V82 */
		return error(EGL_BAD_ALLOC, EGL_NO_SURFACE);
	}
'''),
])

patch("Main/FrameBufferAndroid.cpp", [
    ("#include <system/window.h>\n",
     "#include <system/window.h>\n#include <android/log.h>   /* V82 */\n#include <errno.h>\n#include <string.h>\n"
     '#define SSLOG(...) __android_log_print(ANDROID_LOG_INFO, "SwiftShader", __VA_ARGS__)\n'
     '#define SSLOGE(...) __android_log_print(ANDROID_LOG_ERROR, "SwiftShader", __VA_ARGS__)\n'),
    ('''		nativeWindow->common.incRef(&nativeWindow->common);
		native_window_set_usage(nativeWindow, GRALLOC_USAGE_SW_READ_OFTEN | GRALLOC_USAGE_SW_WRITE_OFTEN);
	}

	FrameBufferAndroid::~FrameBufferAndroid()
	{
		nativeWindow->common.decRef(&nativeWindow->common);
	}''',
     '''		nativeWindow->common.incRef(&nativeWindow->common);
		int rc = native_window_set_usage(nativeWindow, GRALLOC_USAGE_SW_READ_OFTEN | GRALLOC_USAGE_SW_WRITE_OFTEN);
		SSLOG("FrameBufferAndroid: window=%p %dx%d set_usage rc=%d", window, width, height, rc);   /* V82 */
	}

	FrameBufferAndroid::~FrameBufferAndroid()
	{
		SSLOG("~FrameBufferAndroid: window=%p", nativeWindow);   /* V82 */
		nativeWindow->common.decRef(&nativeWindow->common);
	}'''),
    ('''			queueBuffer(nativeWindow, buffer, -1);
		}
	}''',
     '''			int rc = queueBuffer(nativeWindow, buffer, -1);
			static int nq = 0;   /* V82 */
			if(rc != 0 || nq < 3) { SSLOG("FrameBufferAndroid: queueBuffer window=%p buffer=%p rc=%d (%s)", nativeWindow, buffer, rc, strerror(-rc)); }
			nq++;
		}
	}'''),
    ('''		if(dequeueBuffer(nativeWindow, &buffer) != 0)
		{
			return nullptr;
		}
''',
     '''		int rc = dequeueBuffer(nativeWindow, &buffer);   /* V82 */
		if(rc != 0)
		{
			SSLOGE("FrameBufferAndroid: dequeueBuffer window=%p rc=%d (%s)", nativeWindow, rc, strerror(-rc));
			return nullptr;
		}
		{
			static int nd = 0;
			if(nd < 3) { SSLOG("FrameBufferAndroid: dequeueBuffer window=%p buffer=%p %dx%d fmt=%d stride=%d", nativeWindow, buffer, buffer->width, buffer->height, buffer->format, buffer->stride); }
			nd++;
		}
'''),
    ('''			TRACE("%s failed to lock buffer %p", __FUNCTION__, buffer);
			return nullptr;''',
     '''			SSLOGE("FrameBufferAndroid: gralloc lock failed buffer=%p", buffer);   /* V82 */
			return nullptr;'''),
])
print("V82_DONE")
