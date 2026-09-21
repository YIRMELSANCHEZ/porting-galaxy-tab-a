#!/usr/bin/env python3
# V83 (APP: SwiftAngle, diagnostic). With debug.angle.backend=1 the app now queues frames (RGBA_8888,
# ~515 ms/frame) but the image is a uniform color. Traces in SwiftShader's libGLESv2: each draw
# (first 150 and then 1 in every 500) with framebuffer, size/format of color attachment 0, program,
# viewport and vertices; each clear (first 60) with mask and color; each blitFramebuffer (first 30).
# Idempotente.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src/OpenGL/libGLESv2")
p = T / "Context.cpp"
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V83" in s:
    print("Context.cpp: already patched"); print("V83_DONE"); sys.exit(0)

helper = '''#include "Sampler.h"
#include <android/log.h>   /* V83 */
#define SSLOG(...) __android_log_print(ANDROID_LOG_INFO, "SwiftShader", __VA_ARGS__)
namespace es2 {
static void ssLogDraw(const char *what, Context *ctx, Framebuffer *fb, GLuint fbName, GLuint prog, int vpW, int vpH, GLenum mode, int count, int inst)
{
	static int n = 0;
	n++;
	if(n > 150 && (n % 500) != 0) return;
	int w = 0, h = 0, fmt = 0, samples = 0;
	GLenum status = fb ? fb->completeness(w, h, samples) : 0;
	Renderbuffer *cb = fb ? fb->getColorbuffer(0) : nullptr;
	if(cb) { fmt = cb->getFormat(); }
	SSLOG("GL %s #%d fbo=%u status=0x%x rt=%dx%d fmt=0x%x prog=%u vp=%dx%d mode=%u count=%d inst=%d", what, n, fbName, status, w, h, fmt, prog, vpW, vpH, mode, count, inst);
}
}
'''
edits = [
    ('#include "Sampler.h"\n', helper),
    ('''void Context::drawArrays(GLenum mode, GLint first, GLsizei count, GLsizei instanceCount)
{
	if(!applyRenderTarget())
	{
		return;
	}

	if(mState.currentProgram == 0)
	{
		return;   // Nothing to process.
	}
''',
     '''void Context::drawArrays(GLenum mode, GLint first, GLsizei count, GLsizei instanceCount)
{
	if(!applyRenderTarget())
	{
		SSLOG("GL drawArrays: applyRenderTarget FAILED fbo=%u", mState.drawFramebuffer);   /* V83 */
		return;
	}

	if(mState.currentProgram == 0)
	{
		return;   // Nothing to process.
	}
	ssLogDraw("drawArrays", this, getDrawFramebuffer(), mState.drawFramebuffer, mState.currentProgram, mState.viewportWidth, mState.viewportHeight, mode, count, instanceCount);   /* V83 */
'''),
    ('''void Context::drawElements(GLenum mode, GLuint start, GLuint end, GLsizei count, GLenum type, const void *indices, GLsizei instanceCount)
{
	if(!applyRenderTarget())
	{
		return;
	}

	if(mState.currentProgram == 0)
	{
		return;   // Nothing to process.
	}
''',
     '''void Context::drawElements(GLenum mode, GLuint start, GLuint end, GLsizei count, GLenum type, const void *indices, GLsizei instanceCount)
{
	if(!applyRenderTarget())
	{
		SSLOG("GL drawElements: applyRenderTarget FAILED fbo=%u", mState.drawFramebuffer);   /* V83 */
		return;
	}

	if(mState.currentProgram == 0)
	{
		return;   // Nothing to process.
	}
	ssLogDraw("drawElements", this, getDrawFramebuffer(), mState.drawFramebuffer, mState.currentProgram, mState.viewportWidth, mState.viewportHeight, mode, count, instanceCount);   /* V83 */
'''),
    ('''void Context::clear(GLbitfield mask)
{
''',
     '''void Context::clear(GLbitfield mask)
{
	{
		static int nc = 0;   /* V83 */
		if(nc < 60) { SSLOG("GL clear #%d fbo=%u mask=0x%x color=%.2f,%.2f,%.2f,%.2f", nc, mState.drawFramebuffer, mask, mState.colorClearValue.red, mState.colorClearValue.green, mState.colorClearValue.blue, mState.colorClearValue.alpha); }
		nc++;
	}
'''),
    ('''                              GLbitfield mask, bool filter, bool allowPartialDepthStencilBlit)
{
	Framebuffer *readFramebuffer = getReadFramebuffer();
	Framebuffer *drawFramebuffer = getDrawFramebuffer();
''',
     '''                              GLbitfield mask, bool filter, bool allowPartialDepthStencilBlit)
{
	Framebuffer *readFramebuffer = getReadFramebuffer();
	Framebuffer *drawFramebuffer = getDrawFramebuffer();
	{
		static int nb = 0;   /* V83 */
		if(nb < 30) { SSLOG("GL blitFramebuffer #%d read=%u draw=%u src=%d,%d-%d,%d dst=%d,%d-%d,%d mask=0x%x", nb, mState.readFramebuffer, mState.drawFramebuffer, srcX0, srcY0, srcX1, srcY1, dstX0, dstY0, dstX1, dstY1, mask); }
		nb++;
	}
'''),
]
for old, new in edits:
    if s.count(old) != 1:
        print(f"V83_ERROR: unique block not found ({s.count(old)}): {old[:60]!r}"); sys.exit(1)
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8", errors="surrogateescape")
print("Context.cpp: trazas V83 de draw/clear/blit")
print("V83_DONE")
