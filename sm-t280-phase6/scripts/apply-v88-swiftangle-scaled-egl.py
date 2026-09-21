#!/usr/bin/env python3
# V88: fixes the V87 scale experiment. V87 requested 640x400 buffers from the ANativeWindow but
# WindowSurface/FrameBuffer stayed sized at 1280x800; lock() rejected each buffer as
# too small and a frame was never queued. V88 keeps the original logical size and makes
# EGL/backbuffer/framebuffer also use the scaled size. SurfaceFlinger enlarges the buffer.
# Idempotent; only affects the SwiftAngle/SwiftShader package.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src/OpenGL/libEGL")

h = T / "Surface.hpp"
s = h.read_text(encoding="utf-8", errors="surrogateescape")
if "V88_SCALE_STATE" not in s:
    old = '''\tconst EGLNativeWindowType window;
\tsw::FrameBuffer *frameBuffer = nullptr;
'''
    new = '''\tconst EGLNativeWindowType window;
\tsw::FrameBuffer *frameBuffer = nullptr;
\t// V88_SCALE_STATE: dimensiones logicas originales y escala fijada al crear la EGLSurface.
\tint nativeWindowWidth = 0;
\tint nativeWindowHeight = 0;
\tint requestedBufferScale = 1;
'''
    if s.count(old) != 1:
        print("V88_ERROR: unexpected Surface.hpp")
        sys.exit(1)
    h.write_text(s.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
    print("V88: scale state added to WindowSurface")
else:
    print("V88: Surface.hpp already patched")

p = T / "Surface.cpp"
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V88_SCALE_EGL" not in s:
    old_ctor = '''\t#if defined(__ANDROID__) && defined(__BIONIC__)
\t// V87_SWIFTANGLE_SCALE: SwiftShader rasteriza por CPU; reducir solo su buffer baja
\t// el numero de pixeles sin alterar la resolucion del sistema/Mali. SurfaceFlinger
\t// escala el buffer al tamano del SurfaceView. 1 desactiva; rango seguro 1..4.
\tchar scaleValue[PROPERTY_VALUE_MAX] = {};
\tproperty_get("persist.swiftangle.scale", scaleValue, "2");
\tconst int scale = atoi(scaleValue);
\tif(scale >= 2 && scale <= 4)
\t{
\t\tint nativeWidth = 0;
\t\tint nativeHeight = 0;
\t\twindow->query(window, NATIVE_WINDOW_WIDTH, &nativeWidth);
\t\twindow->query(window, NATIVE_WINDOW_HEIGHT, &nativeHeight);
\t\tconst int scaledWidth = nativeWidth / scale;
\t\tconst int scaledHeight = nativeHeight / scale;
\t\tif(scaledWidth >= 320 && scaledHeight >= 200)
\t\t{
\t\t\t(void)native_window_set_buffers_dimensions(window, scaledWidth, scaledHeight);
\t\t}
\t}
\t#endif
'''
    new_ctor = '''\t#if defined(__ANDROID__) && defined(__BIONIC__)
\t// V88_SCALE_EGL: guardar el tamano logico antes de pedir buffers reducidos. El
\t// resize real se aplica en checkForResize para que EGL y FrameBuffer coincidan.
\twindow->query(window, NATIVE_WINDOW_WIDTH, &nativeWindowWidth);
\twindow->query(window, NATIVE_WINDOW_HEIGHT, &nativeWindowHeight);
\tchar scaleValue[PROPERTY_VALUE_MAX] = {};
\tproperty_get("persist.swiftangle.scale", scaleValue, "2");
\tconst int scale = atoi(scaleValue);
\tif(scale >= 2 && scale <= 4 && nativeWindowWidth / scale >= 320 && nativeWindowHeight / scale >= 200)
\t{
\t\trequestedBufferScale = scale;
\t}
\t#endif
'''
    if s.count(old_ctor) != 1:
        print("V88_ERROR: V87 constructor not found")
        sys.exit(1)
    s = s.replace(old_ctor, new_ctor, 1)

    old_android = '''\t#elif defined(__ANDROID__)
\t\tint windowWidth;  window->query(window, NATIVE_WINDOW_WIDTH, &windowWidth);
\t\tint windowHeight; window->query(window, NATIVE_WINDOW_HEIGHT, &windowHeight);
'''
    new_android = '''\t#elif defined(__ANDROID__)
\t\tint windowWidth;  window->query(window, NATIVE_WINDOW_WIDTH, &windowWidth);
\t\tint windowHeight; window->query(window, NATIVE_WINDOW_HEIGHT, &windowHeight);
\t\t#if defined(__BIONIC__)
\t\t// V88: no basta con reducir el buffer nativo; EGL debe crear tambien su
\t\t// backbuffer/FrameBuffer a esas dimensiones para que lock() no lo rechace.
\t\tif(requestedBufferScale > 1 && nativeWindowWidth > 0 && nativeWindowHeight > 0)
\t\t{
\t\t\twindowWidth = nativeWindowWidth / requestedBufferScale;
\t\t\twindowHeight = nativeWindowHeight / requestedBufferScale;
\t\t\t(void)native_window_set_buffers_dimensions(window, windowWidth, windowHeight);
\t\t}
\t\t#endif
'''
    if s.count(old_android) != 1:
        print("V88_ERROR: rama Android checkForResize inesperada")
        sys.exit(1)
    p.write_text(s.replace(old_android, new_android, 1), encoding="utf-8", errors="surrogateescape")
    print("V88: scale synchronized between ANativeWindow and EGL")
else:
    print("V88: Surface.cpp already patched")

print("V88_DONE")
