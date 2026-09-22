#!/usr/bin/env python3
# V96 (SwiftShader performance, phases 0-2). Requires V95 (stats) applied first.
#  Phase 0: extra counters (JIT compilations and attribution of waits per GL call), all gated by
#          persist.swiftangle.stats=1 (no dump by default).
#  Phase 1: real fences. eglCreateSync annotates the serial of the next draw; eglGetSyncAttrib does not drain;
#          eglClientWaitSync respects timeout 0 and waits only for draws prior to the fence.
#          Switch: persist.swiftangle.fence (1 by default; 0 = old behavior, drain).
#  Phase 2: deferred clears. glClear (color/depth/stencil) is queued as a DrawCall that a
#          worker runs in order (MANAGED lock like the draws), instead of blocking the render thread
#          until the previous draws finish. Switch: persist.swiftangle.deferclear (1).
# Idempotente (marcador V96).
import re
import sys
from pathlib import Path

SW = Path("/home/lineage/android/lineage-17.1/external/swiftshader/src")
MARK = "V96"

def patch(path, fn):
    s = path.read_text(encoding="utf-8", errors="surrogateescape")
    if MARK + "_" in s or ("// " + MARK) in s:
        print(f"{path.name}: already patched"); return
    s2 = fn(s)
    if s2 is None:
        print(f"V96_ERROR: {path.name}"); sys.exit(1)
    path.write_text(s2, encoding="utf-8", errors="surrogateescape")
    print(f"{path.name}: patched")

def rep(s, old, new, count=1):
    if s.count(old) != count:
        raise RuntimeError(f"anchor x{s.count(old)} != {count}: {old[:60]!r}")
    return s.replace(old, new)

# ---------------------------------------------------------------- phase 0: contadores extra
def v95stats_hpp(s):
    return rep(s, "extern long v95_draws, v95_waits, v95_wait_us, v95_syncs, v95_sync_us, v95_clears, v95_clear_us;\n",
               "extern long v95_draws, v95_waits, v95_wait_us, v95_syncs, v95_sync_us, v95_clears, v95_clear_us;\n"
               "extern long v95_jit, v95_jit_us;   // V96_JIT\n"
               "extern const char *v95_tag;\n"
               "struct V95TagEntry { const char *tag; long n; long us; };\n"
               "extern V95TagEntry v95_tags[12];\n"
               "void v95_account_wait(long us);\n").replace(
               "struct V95Timer { long t0; long *acc; V95Timer(long *a) : t0(v95_now_us()), acc(a) {} ~V95Timer() { *acc += v95_now_us() - t0; } };\n",
               "struct V95Timer { long t0; long *acc; V95Timer(long *a) : t0(v95_now_us()), acc(a) {} ~V95Timer() { *acc += v95_now_us() - t0; } };\n"
               "struct V95Tag { const char *old; V95Tag(const char *t) { old = v95_tag; v95_tag = t; } ~V95Tag() { v95_tag = old; } };\n", 1)

def resource_cpp(s):
    s = rep(s, "\tlong v95_draws = 0, v95_waits = 0, v95_wait_us = 0, v95_syncs = 0, v95_sync_us = 0, v95_clears = 0, v95_clear_us = 0;\n",
            "\tlong v95_draws = 0, v95_waits = 0, v95_wait_us = 0, v95_syncs = 0, v95_sync_us = 0, v95_clears = 0, v95_clear_us = 0;\n"
            "\tlong v95_jit = 0, v95_jit_us = 0;   // V96_JIT\n"
            "\tconst char *v95_tag = \"other/swap\";\n"
            "\tV95TagEntry v95_tags[12] = {};\n"
            "\tvoid v95_account_wait(long us)\n"
            "\t{\n"
            "\t\tfor(int i = 0; i < 12; i++)\n"
            "\t\t{\n"
            "\t\t\tif(v95_tags[i].tag == v95_tag || v95_tags[i].tag == nullptr)\n"
            "\t\t\t{\n"
            "\t\t\t\tv95_tags[i].tag = v95_tag; v95_tags[i].n++; v95_tags[i].us += us;\n"
            "\t\t\t\treturn;\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n")
    s = rep(s, "\t\t\t{ V95Timer v95t(&v95_wait_us); v95_waits++; unblock.wait(); }\n",
            "\t\t\t{ long t0 = v95_now_us(); v95_waits++; unblock.wait(); long dt = v95_now_us() - t0; v95_wait_us += dt; v95_account_wait(dt); }   // V96\n", 2)
    # non-blocking check (phase 2 does not use it; useful for diagnostics)
    return s

def llvmreactor_cpp(s):
    s = rep(s, '#include "llvm/Support/Host.h"   /* V81 */\n',
            '#include "llvm/Support/Host.h"   /* V81 */\n#include <time.h>   // V96_JIT\nnamespace sw { extern long v95_jit, v95_jit_us; }\n')
    old = "\t\tLLVMRoutine *routine = ::reactorJIT->acquireRoutine(::function);\n\n\t\treturn routine;\n"
    new = ("\t\tstruct timespec v96t0; clock_gettime(CLOCK_MONOTONIC, &v96t0);   // V96_JIT\n"
           "\t\tLLVMRoutine *routine = ::reactorJIT->acquireRoutine(::function);\n"
           "\t\tstruct timespec v96t1; clock_gettime(CLOCK_MONOTONIC, &v96t1);\n"
           "\t\tsw::v95_jit++; sw::v95_jit_us += (v96t1.tv_sec - v96t0.tv_sec) * 1000000L + (v96t1.tv_nsec - v96t0.tv_nsec) / 1000;\n\n"
           "\t\treturn routine;\n")
    return rep(s, old, new)

TAGGED = ["Clear", "DrawArrays", "DrawElements", "DrawArraysInstancedEXT", "DrawElementsInstancedEXT", "BufferData",
          "BufferSubData", "TexImage2D", "TexSubImage2D", "CopyTexSubImage2D", "ReadPixels", "Finish", "Flush",
          "GenerateMipmap", "BlitFramebufferANGLE", "EGLImageTargetTexture2DOES"]
def libglesv2_cpp(s):
    s = rep(s, '#include "Common/Version.h"\n', '#include "Common/Version.h"\n#include "Common/V95Stats.hpp"   // V96_TAGS\n')
    for name in TAGGED:
        pat = re.compile(r"^(void %s\([^{]*?\)\n\{\n)" % re.escape(name), re.M | re.S)
        n = len(pat.findall(s))
        if n != 1:
            raise RuntimeError(f"tag {name}: {n} coincidencias")
        s = pat.sub(lambda m: m.group(1) + '\tsw::V95Tag v95tag("%s");\n' % name, s, count=1)
    return s

# ---------------------------------------------------------------- phases 1 and 2: Renderer
def renderer_hpp(s):
    s = rep(s, "#include <list>\n", "#include <list>\n#include <set>   // V96\n") if "#include <list>\n" in s else s
    if "#include <set>" not in s:
        s = rep(s, "namespace sw\n{\n", "#include <set>   // V96\n\nnamespace sw\n{\n")
    s = rep(s, "\t\tstd::list<Query*> queries;\n\t\tResource *sync;\n",
            "\t\tstd::list<Query*> queries;\n\t\tResource *sync;\n\n"
            "\t\t// V96: fences reales (serial del draw) y clears diferidos\n"
            "\t\tMutexLock fenceMutex;\n"
            "\t\tstd::set<int> inFlight;\n"
            "\tpublic:\n"
            "\t\tint fencePoint();\n"
            "\t\tbool fenceComplete(int point);\n"
            "\t\tvoid fenceWait(int point, long long timeoutNs);\n"
            "\t\tbool clearDeferred(Surface *dest, int plane, int index, const Rect &rect, unsigned int packed, int bytes, float depth, unsigned char stencilValue, unsigned char stencilMask);\n"
            "\t\tvoid performClear(DrawCall *draw);\n"
            "\tprivate:\n")
    s = rep(s, "\t\tDrawData *data;\n\t};\n}\n",
            "\t\tDrawData *data;\n\n"
            "\t\t// V96\n"
            "\t\tint serial;\n"
            "\t\tbool isClear;\n"
            "\t\tint clearPlane;   // 0 color, 1 profundidad, 2 stencil\n"
            "\t\tSurface *clearSurface;\n"
            "\t\tint clearX0, clearY0, clearX1, clearY1;\n"
            "\t\tunsigned int clearPacked;\n"
            "\t\tint clearBytes;\n"
            "\t\tfloat clearDepthValue;\n"
            "\t\tunsigned char clearStencilValue, clearStencilMask;\n"
            "\t};\n}\n")
    return s

def renderer_cpp(s):
    s = rep(s, "#include <android/log.h>\n#else\n#define __android_log_print(...) ((void)0)\n#endif\n",
            "#include <android/log.h>\n#else\n#define __android_log_print(...) ((void)0)\n#endif\n#include <unistd.h>   // V96 usleep\n#include <stdio.h>\n")
    # constructor DrawCall
    s = rep(s, "\t\treferences = -1;\n\n\t\tdata = (DrawData*)allocate(sizeof(DrawData));\n",
            "\t\treferences = -1;\n\t\tserial = -1;   // V96\n\t\tisClear = false;\n\t\tclearSurface = nullptr;\n\n\t\tdata = (DrawData*)allocate(sizeof(DrawData));\n")
    # stats dump gated by property + JIT + tags
    old_dump = ("\t\t\tif(now - v95_last >= 2000000L)\n\t\t\t{\n"
                "\t\t\t\t__android_log_print(ANDROID_LOG_INFO, \"V95_STATS\", \"per %ld ms: draws=%ld waits=%ld wait_ms=%ld syncs=%ld sync_ms=%ld clears=%ld clear_ms=%ld\",\n"
                "\t\t\t\t                    (now - v95_last) / 1000, v95_draws, v95_waits, v95_wait_us / 1000, v95_syncs, v95_sync_us / 1000, v95_clears, v95_clear_us / 1000);\n"
                "\t\t\t\tv95_draws = v95_waits = v95_wait_us = v95_syncs = v95_sync_us = v95_clears = v95_clear_us = 0;\n")
    new_dump = ("\t\t\tif(now - v95_last >= 2000000L)\n\t\t\t{\n"
                "\t\t\t\tbool v96_stats = false;   // V96: volcado solo con persist.swiftangle.stats=1\n"
                "\t\t\t\t#if defined(__ANDROID__) && defined(__BIONIC__)\n"
                "\t\t\t\t{ char v[PROPERTY_VALUE_MAX] = {}; v96_stats = property_get(\"persist.swiftangle.stats\", v, \"0\") > 0 && v[0] == '1'; }\n"
                "\t\t\t\t#endif\n"
                "\t\t\t\tif(v96_stats)\n"
                "\t\t\t\t{\n"
                "\t\t\t\t\tchar tags[512] = {}; int p = 0;\n"
                "\t\t\t\t\tfor(int i = 0; i < 12 && v95_tags[i].tag; i++) { p += snprintf(tags + p, sizeof(tags) - p, \" %s=%ld/%ldms\", v95_tags[i].tag, v95_tags[i].n, v95_tags[i].us / 1000); v95_tags[i].n = 0; v95_tags[i].us = 0; }\n"
                "\t\t\t\t\t__android_log_print(ANDROID_LOG_INFO, \"V95_STATS\", \"per %ld ms: draws=%ld waits=%ld wait_ms=%ld syncs=%ld sync_ms=%ld clears=%ld clear_ms=%ld jit=%ld jit_ms=%ld waits_by:%s\",\n"
                "\t\t\t\t\t                    (now - v95_last) / 1000, v95_draws, v95_waits, v95_wait_us / 1000, v95_syncs, v95_sync_us / 1000, v95_clears, v95_clear_us / 1000, v95_jit, v95_jit_us / 1000, tags);\n"
                "\t\t\t\t}\n"
                "\t\t\t\tv95_draws = v95_waits = v95_wait_us = v95_syncs = v95_sync_us = v95_clears = v95_clear_us = v95_jit = v95_jit_us = 0;\n")
    s = rep(s, old_dump, new_dump)
    # serial registration in draw()
    s = rep(s, "\t\t\tdraw->references = (count + batch - 1) / batch;\n\n\t\t\tschedulerMutex.lock();\n\t\t\t++nextDraw; // Atomic\n\t\t\tschedulerMutex.unlock();\n",
            "\t\t\tdraw->references = (count + batch - 1) / batch;\n\n"
            "\t\t\tdraw->isClear = false;   // V96\n"
            "\t\t\tdraw->serial = nextDraw;\n"
            "\t\t\tfenceMutex.lock();\n"
            "\t\t\tinFlight.insert(draw->serial);\n"
            "\t\t\tfenceMutex.unlock();\n\n"
            "\t\t\tschedulerMutex.lock();\n\t\t\t++nextDraw; // Atomic\n\t\t\tschedulerMutex.unlock();\n")
    # executeTask: clear diferido
    s = rep(s, "\t\tcase Task::PRIMITIVES:\n\t\t\t{\n\t\t\t\tint unit = task[threadIndex].primitiveUnit;\n",
            "\t\tcase Task::PRIMITIVES:\n\t\t\t{\n\t\t\t\tint unit = task[threadIndex].primitiveUnit;\n\n"
            "\t\t\t\t{   // V96: clear diferido, sin vertices ni pixel routine\n"
            "\t\t\t\t\tDrawCall *clearDraw = drawList[primitiveProgress[unit].drawCall & DRAW_COUNT_BITS];\n"
            "\t\t\t\t\tif(clearDraw->isClear)\n"
            "\t\t\t\t\t{\n"
            "\t\t\t\t\t\tperformClear(clearDraw);\n"
            "\t\t\t\t\t\tprimitiveProgress[unit].visible = 0;\n"
            "\t\t\t\t\t\tprimitiveProgress[unit].references = clusterCount;\n"
            "\t\t\t\t\t\tbreak;\n"
            "\t\t\t\t\t}\n"
            "\t\t\t\t}\n")
    # finishRendering: unbind with guard, fence erase
    s = rep(s, "\t\t\t\tdraw.vertexRoutine->unbind();\n\t\t\t\tdraw.setupRoutine->unbind();\n\t\t\t\tdraw.pixelRoutine->unbind();\n\n\t\t\t\tsync->unlock();\n",
            "\t\t\t\tif(draw.vertexRoutine) draw.vertexRoutine->unbind();   // V96: nulos en clears diferidos\n"
            "\t\t\t\tif(draw.setupRoutine) draw.setupRoutine->unbind();\n"
            "\t\t\t\tif(draw.pixelRoutine) draw.pixelRoutine->unbind();\n\n"
            "\t\t\t\tfenceMutex.lock();   // V96\n"
            "\t\t\t\tinFlight.erase(draw.serial);\n"
            "\t\t\t\tfenceMutex.unlock();\n\n"
            "\t\t\t\tsync->unlock();\n")
    # nuevas funciones antes de synchronize()
    new_fns = r'''	// V96 ---------------------------------------------------------------------------------------
	static void v96_fill4(void *buffer, int pattern, int bytes)
	{
		sw::clear((uint32_t*)buffer, (uint32_t)pattern, bytes / 4);
	}

	int Renderer::fencePoint()
	{
		return nextDraw;
	}

	bool Renderer::fenceComplete(int point)
	{
		fenceMutex.lock();
		bool done = inFlight.empty() || (*inFlight.begin() >= point);
		fenceMutex.unlock();
		return done;
	}

	void Renderer::fenceWait(int point, long long timeoutNs)
	{
		long long start = v95_now_us();
		while(!fenceComplete(point))
		{
			if(timeoutNs >= 0 && (v95_now_us() - start) * 1000LL >= timeoutNs)
			{
				return;
			}
			usleep(200);
		}
	}

	bool Renderer::clearDeferred(Surface *dest, int plane, int index, const Rect &rect, unsigned int packed, int bytes, float depth, unsigned char stencilValue, unsigned char stencilMask)
	{
		if(!dest || rect.x0 >= rect.x1 || rect.y0 >= rect.y1)
		{
			return true;
		}

		updateConfiguration();

		sync->lock(sw::PRIVATE);

		DrawCall *draw = nullptr;

		do
		{
			for(int i = 0; i < DRAW_COUNT; i++)
			{
				if(drawCall[i]->references == -1)
				{
					draw = drawCall[i];
					drawList[nextDraw & DRAW_COUNT_BITS] = draw;

					break;
				}
			}

			if(!draw)
			{
				resumeApp->wait();
			}
		}
		while(!draw);

		DrawData *data = draw->data;

		draw->isClear = true;
		draw->clearPlane = plane;
		draw->clearSurface = dest;
		draw->clearX0 = rect.x0;
		draw->clearY0 = rect.y0;
		draw->clearX1 = rect.x1;
		draw->clearY1 = rect.y1;
		draw->clearPacked = packed;
		draw->clearBytes = bytes;
		draw->clearDepthValue = depth;
		draw->clearStencilValue = stencilValue;
		draw->clearStencilMask = stencilMask;

		draw->drawType = DRAW_TRIANGLELIST;
		draw->batchSize = 1;
		draw->vertexRoutine = nullptr;
		draw->setupRoutine = nullptr;
		draw->pixelRoutine = nullptr;
		draw->vertexPointer = nullptr;
		draw->setupPointer = nullptr;
		draw->pixelPointer = nullptr;
		draw->setupPrimitives = nullptr;
		draw->queries = nullptr;
		draw->clipFlags = 0;

		for(int i = 0; i < MAX_VERTEX_INPUTS; i++) draw->vertexStream[i] = nullptr;
		draw->indexBuffer = nullptr;
		for(int i = 0; i < RENDERTARGETS; i++) draw->renderTarget[i] = nullptr;
		draw->depthBuffer = nullptr;
		draw->stencilBuffer = nullptr;
		for(int i = 0; i < TOTAL_IMAGE_UNITS; i++) draw->texture[i] = nullptr;
		for(int i = 0; i < MAX_UNIFORM_BUFFER_BINDINGS; i++) { draw->pUniformBuffers[i] = nullptr; draw->vUniformBuffers[i] = nullptr; }
		for(int i = 0; i < MAX_TRANSFORM_FEEDBACK_INTERLEAVED_COMPONENTS; i++) draw->transformFeedbackBuffers[i] = nullptr;

		if(plane == 0)
		{
			unsigned int layer = context->renderTargetLayer[index];
			draw->renderTarget[0] = dest;
			data->colorBuffer[0] = (unsigned int*)dest->lockInternal(0, 0, layer, LOCK_READWRITE, MANAGED);
			data->colorPitchB[0] = dest->getInternalPitchB();
			data->colorSliceB[0] = dest->getInternalSliceB();
		}
		else if(plane == 1)
		{
			unsigned int layer = context->depthBufferLayer;
			draw->depthBuffer = dest;
			data->depthBuffer = (float*)dest->lockInternal(0, 0, layer, LOCK_READWRITE, MANAGED);
			data->depthPitchB = dest->getInternalPitchB();
			data->depthSliceB = dest->getInternalSliceB();
		}
		else
		{
			unsigned int layer = context->stencilBufferLayer;
			draw->stencilBuffer = dest;
			data->stencilBuffer = (unsigned char*)dest->lockStencil(0, 0, layer, MANAGED);
			data->stencilPitchB = dest->getStencilPitchB();
			data->stencilSliceB = dest->getStencilSliceB();
		}

		draw->primitive = 0;
		draw->count = 1;
		draw->references = 1;

		draw->serial = nextDraw;
		fenceMutex.lock();
		inFlight.insert(draw->serial);
		fenceMutex.unlock();

		schedulerMutex.lock();
		++nextDraw; // Atomic
		schedulerMutex.unlock();

		#ifndef NDEBUG
		if(threadCount == 1)   // Use main thread for draw execution
		{
			threadsAwake = 1;
			task[0].type = Task::RESUME;

			taskLoop(0);
		}
		else
		#endif
		{
			if(!threadsAwake)
			{
				suspend[0]->wait();

				threadsAwake = 1;
				task[0].type = Task::RESUME;

				resume[0]->signal();
			}
		}

		return true;
	}

	void Renderer::performClear(DrawCall *draw)
	{
		DrawData *data = draw->data;
		Surface *dest = draw->clearSurface;
		int x0 = draw->clearX0, y0 = draw->clearY0, x1 = draw->clearX1, y1 = draw->clearY1;
		int samples = dest->getSamples();

		if(draw->clearPlane == 0)
		{
			unsigned char *slice = (unsigned char*)data->colorBuffer[0] + y0 * data->colorPitchB[0] + x0 * draw->clearBytes;

			for(int j = 0; j < samples; j++)
			{
				unsigned char *d = slice;

				for(int y = y0; y < y1; y++)
				{
					if(draw->clearBytes == 2)
					{
						sw::clear((uint16_t*)d, (uint16_t)draw->clearPacked, x1 - x0);
					}
					else
					{
						sw::clear((uint32_t*)d, draw->clearPacked, x1 - x0);
					}

					d += data->colorPitchB[0];
				}

				slice += data->colorSliceB[0];
			}
		}
		else if(draw->clearPlane == 1)
		{
			float depth = draw->clearDepthValue;
			int pitchP = data->depthPitchB / sizeof(float);
			int sliceP = data->depthSliceB / sizeof(float);
			int width = x1 - x0;

			if(!Surface::hasQuadLayout(dest->getInternalFormat()))
			{
				float *target = data->depthBuffer + y0 * pitchP + x0;

				for(int z = 0; z < samples; z++)
				{
					float *row = target;

					for(int y = y0; y < y1; y++)
					{
						v96_fill4(row, (int&)depth, width * sizeof(float));
						row += pitchP;
					}

					target += sliceP;
				}
			}
			else   // Quad layout
			{
				if(complementaryDepthBuffer)
				{
					depth = 1 - depth;
				}

				float *buffer = data->depthBuffer;

				int oddX0 = (x0 & ~1) * 2 + (x0 & 1);
				int oddX1 = (x1 & ~1) * 2;
				int evenX0 = ((x0 + 1) & ~1) * 2;
				int evenBytes = (oddX1 - evenX0) * sizeof(float);

				for(int z = 0; z < samples; z++)
				{
					for(int y = y0; y < y1; y++)
					{
						float *target = buffer + (y & ~1) * pitchP + (y & 1) * 2;

						if((y & 1) == 0 && y + 1 < y1)   // Fill quad line at once
						{
							if((x0 & 1) != 0)
							{
								target[oddX0 + 0] = depth;
								target[oddX0 + 2] = depth;
							}

							v96_fill4(&target[evenX0], (int&)depth, evenBytes);

							if((x1 & 1) != 0)
							{
								target[oddX1 + 0] = depth;
								target[oddX1 + 2] = depth;
							}

							y++;
						}
						else
						{
							for(int x = x0, i = oddX0; x < x1; x++, i = (x & ~1) * 2 + (x & 1))
							{
								target[i] = depth;
							}
						}
					}

					buffer += sliceP;
				}
			}
		}
		else
		{
			unsigned char s = draw->clearStencilValue;
			unsigned char mask = draw->clearStencilMask;
			int pitchP = data->stencilPitchB;
			int sliceP = data->stencilSliceB;

			int oddX0 = (x0 & ~1) * 2 + (x0 & 1);
			int oddX1 = (x1 & ~1) * 2;
			int evenX0 = ((x0 + 1) & ~1) * 2;
			int evenBytes = oddX1 - evenX0;

			unsigned char maskedS = s & mask;
			unsigned char invMask = ~mask;
			unsigned int fill = maskedS;
			fill = fill | (fill << 8) | (fill << 16) | (fill << 24);

			char *buffer = (char*)data->stencilBuffer;

			for(int z = 0; z < samples; z++)
			{
				for(int y = y0; y < y1; y++)
				{
					char *target = buffer + (y & ~1) * pitchP + (y & 1) * 2;

					if((y & 1) == 0 && y + 1 < y1 && mask == 0xFF)   // Fill quad line at once
					{
						if((x0 & 1) != 0)
						{
							target[oddX0 + 0] = fill;
							target[oddX0 + 2] = fill;
						}

						v96_fill4(&target[evenX0], fill, evenBytes);

						if((x1 & 1) != 0)
						{
							target[oddX1 + 0] = fill;
							target[oddX1 + 2] = fill;
						}

						y++;
					}
					else
					{
						for(int x = x0; x < x1; x++)
						{
							int i = (x & ~1) * 2 + (x & 1);
							target[i] = maskedS | (target[i] & invMask);
						}
					}
				}

				buffer += sliceP;
			}
		}
	}

'''
    s = rep(s, "\tvoid Renderer::synchronize()\n\t{\n", new_fns + "\tvoid Renderer::synchronize()\n\t{\n")
    return s

# ---------------------------------------------------------------- phase 2: es2::Device usa clears diferidos
def device_hpp(s):
    return rep(s, "\t\tsw::Rect scissorRect;\n\t\tbool scissorEnable;\n",
               "\t\tsw::Rect scissorRect;\n\t\tbool scissorEnable;\n\t\tbool deferClears;   // V96\n")

def device_cpp(s):
    s = rep(s, '#include "Device.hpp"\n', '#include "Device.hpp"\n#if defined(__ANDROID__) && defined(__BIONIC__)\n#include <cutils/properties.h>   // V96\n#endif\n')
    s = rep(s, "\t\tdepthBuffer = nullptr;\n\t\tstencilBuffer = nullptr;\n\n\t\tsetDepthBufferEnable(true);\n",
            "\t\tdepthBuffer = nullptr;\n\t\tstencilBuffer = nullptr;\n\n"
            "\t\tdeferClears = true;   // V96: persist.swiftangle.deferclear (1 por defecto)\n"
            "\t\t#if defined(__ANDROID__) && defined(__BIONIC__)\n"
            "\t\t{ char v[PROPERTY_VALUE_MAX] = {}; if(property_get(\"persist.swiftangle.deferclear\", v, \"1\") > 0) deferClears = (v[0] != '0'); }\n"
            "\t\t#endif\n\n\t\tsetDepthBufferEnable(true);\n")
    old_c = "\t\t\t\tclear(rgba, FORMAT_A32B32G32R32F, renderTarget[i], clearRect, rgbaMask);\n"
    new_c = ("\t\t\t\tif(deferClears && !renderTarget[i]->isExternalDirty())   // V96\n"
             "\t\t\t\t{\n"
             "\t\t\t\t\tuint32_t packed = 0; int bytes = 0; bool ok = true;\n"
             "\t\t\t\t\tswitch(renderTarget[i]->getFormat())\n"
             "\t\t\t\t\t{\n"
             "\t\t\t\t\tcase FORMAT_R5G6B5:\n"
             "\t\t\t\t\t\tok = (rgbaMask & 0x7) == 0x7; bytes = 2;\n"
             "\t\t\t\t\t\tpacked = ((uint16_t)(31 * blue + 0.5f) << 0) | ((uint16_t)(63 * green + 0.5f) << 5) | ((uint16_t)(31 * red + 0.5f) << 11);\n"
             "\t\t\t\t\t\tbreak;\n"
             "\t\t\t\t\tcase FORMAT_X8B8G8R8:\n"
             "\t\t\t\t\t\tok = (rgbaMask & 0x7) == 0x7; bytes = 4;\n"
             "\t\t\t\t\t\tpacked = ((uint32_t)(255) << 24) | ((uint32_t)(255 * blue + 0.5f) << 16) | ((uint32_t)(255 * green + 0.5f) << 8) | ((uint32_t)(255 * red + 0.5f) << 0);\n"
             "\t\t\t\t\t\tbreak;\n"
             "\t\t\t\t\tcase FORMAT_A8B8G8R8:\n"
             "\t\t\t\t\t\tok = (rgbaMask & 0xF) == 0xF; bytes = 4;\n"
             "\t\t\t\t\t\tpacked = ((uint32_t)(255 * alpha + 0.5f) << 24) | ((uint32_t)(255 * blue + 0.5f) << 16) | ((uint32_t)(255 * green + 0.5f) << 8) | ((uint32_t)(255 * red + 0.5f) << 0);\n"
             "\t\t\t\t\t\tbreak;\n"
             "\t\t\t\t\tcase FORMAT_X8R8G8B8:\n"
             "\t\t\t\t\t\tok = (rgbaMask & 0x7) == 0x7; bytes = 4;\n"
             "\t\t\t\t\t\tpacked = ((uint32_t)(255) << 24) | ((uint32_t)(255 * red + 0.5f) << 16) | ((uint32_t)(255 * green + 0.5f) << 8) | ((uint32_t)(255 * blue + 0.5f) << 0);\n"
             "\t\t\t\t\t\tbreak;\n"
             "\t\t\t\t\tcase FORMAT_A8R8G8B8:\n"
             "\t\t\t\t\t\tok = (rgbaMask & 0xF) == 0xF; bytes = 4;\n"
             "\t\t\t\t\t\tpacked = ((uint32_t)(255 * alpha + 0.5f) << 24) | ((uint32_t)(255 * red + 0.5f) << 16) | ((uint32_t)(255 * green + 0.5f) << 8) | ((uint32_t)(255 * blue + 0.5f) << 0);\n"
             "\t\t\t\t\t\tbreak;\n"
             "\t\t\t\t\tdefault:\n"
             "\t\t\t\t\t\tok = false;\n"
             "\t\t\t\t\t}\n"
             "\t\t\t\t\tif(ok && renderTarget[i]->getInternalFormat() == renderTarget[i]->getFormat() && clearDeferred(renderTarget[i], 0, i, clearRect, packed, bytes, 0.0f, 0, 0))\n"
             "\t\t\t\t\t{\n"
             "\t\t\t\t\t\tcontinue;\n"
             "\t\t\t\t\t}\n"
             "\t\t\t\t}\n\n"
             "\t\t\t\tclear(rgba, FORMAT_A32B32G32R32F, renderTarget[i], clearRect, rgbaMask);\n")
    s = rep(s, old_c, new_c)
    old_d = "\t\tdepthBuffer->clearDepth(z, clearRect.x0, clearRect.y0, clearRect.width(), clearRect.height());\n"
    new_d = ("\t\tif(deferClears && depthBuffer->getInternalFormat() != FORMAT_NULL)   // V96\n"
             "\t\t{\n"
             "\t\t\tsw::Rect r = clearRect;\n"
             "\t\t\tr.clip(0, 0, depthBuffer->getWidth(), depthBuffer->getHeight());\n"
             "\t\t\tif(clearDeferred(depthBuffer, 1, 0, r, 0, 0, z, 0, 0))\n"
             "\t\t\t{\n"
             "\t\t\t\treturn;\n"
             "\t\t\t}\n"
             "\t\t}\n\n"
             "\t\tdepthBuffer->clearDepth(z, clearRect.x0, clearRect.y0, clearRect.width(), clearRect.height());\n")
    s = rep(s, old_d, new_d)
    old_s = "\t\tstencilBuffer->clearStencil(stencil, mask, clearRect.x0, clearRect.y0, clearRect.width(), clearRect.height());\n"
    new_s = ("\t\tif(deferClears && stencilBuffer->hasStencil() && (mask & 0xFF) != 0)   // V96\n"
             "\t\t{\n"
             "\t\t\tsw::Rect r = clearRect;\n"
             "\t\t\tr.clip(0, 0, stencilBuffer->getWidth(), stencilBuffer->getHeight());\n"
             "\t\t\tif(clearDeferred(stencilBuffer, 2, 0, r, 0, 0, 0.0f, (unsigned char)stencil, (unsigned char)mask))\n"
             "\t\t\t{\n"
             "\t\t\t\treturn;\n"
             "\t\t\t}\n"
             "\t\t}\n\n"
             "\t\tstencilBuffer->clearStencil(stencil, mask, clearRect.x0, clearRect.y0, clearRect.width(), clearRect.height());\n")
    s = rep(s, old_s, new_s)
    return s

# ---------------------------------------------------------------- phase 1: interfaz egl::Context + es2::Context + libEGL
def eglcontext_hpp(s):
    return rep(s, "\tvirtual void blit(sw::Surface *source, const sw::SliceRect &sRect, sw::Surface *dest, const sw::SliceRect &dRect) = 0;\n",
               "\tvirtual void blit(sw::Surface *source, const sw::SliceRect &sRect, sw::Surface *dest, const sw::SliceRect &dRect) = 0;\n\n"
               "\t// V96: fences reales (por defecto, drenar como antes; ES2 lo implementa con el serial de draw)\n"
               "\tvirtual int fencePoint() { return 0; }\n"
               "\tvirtual bool fenceComplete(int point) { finish(); return true; }\n"
               "\tvirtual void fenceWait(int point, long long timeoutNs) { finish(); }\n")

def es2context_h(s):
    return rep(s, "\tvoid finish() override;\n\tvoid flush();\n",
               "\tvoid finish() override;\n\tvoid flush();\n\tint fencePoint() override;   // V96\n\tbool fenceComplete(int point) override;\n\tvoid fenceWait(int point, long long timeoutNs) override;\n")

def es2context_cpp(s):
    return rep(s, "void Context::finish()\n{\n\tdevice->finish();\n}\n",
               "void Context::finish()\n{\n\tdevice->finish();\n}\n\n"
               "int Context::fencePoint()   // V96\n{\n\treturn device->fencePoint();\n}\n\n"
               "bool Context::fenceComplete(int point)\n{\n\treturn device->fenceComplete(point);\n}\n\n"
               "void Context::fenceWait(int point, long long timeoutNs)\n{\n\tdevice->fenceWait(point, timeoutNs);\n}\n")

def sync_hpp(s):
    old = ("\texplicit FenceSync(Context *context) : context(context)\n\t{\n\t\tstatus = EGL_UNSIGNALED_KHR;\n\t\tcontext->addRef();\n\t}\n")
    new = ("\texplicit FenceSync(Context *context) : context(context)\n\t{\n\t\tstatus = EGL_UNSIGNALED_KHR;\n\t\tcontext->addRef();\n\t\tpoint = context->fencePoint();   // V96\n\t}\n")
    s = rep(s, old, new)
    old2 = ("\tvoid wait() { context->finish(); signal(); }\n\tvoid signal() { status = EGL_SIGNALED_KHR; }\n\tbool isSignaled() const { return status == EGL_SIGNALED_KHR; }\n\nprivate:\n\tEGLint status;\n")
    new2 = ("\tvoid wait() { context->finish(); signal(); }\n\tvoid signal() { status = EGL_SIGNALED_KHR; }\n\tbool isSignaled() const { return status == EGL_SIGNALED_KHR; }\n\n"
            "\t// V96: fence real por serial de draw\n"
            "\tbool poll() { if(status != EGL_SIGNALED_KHR && context->fenceComplete(point)) status = EGL_SIGNALED_KHR; return status == EGL_SIGNALED_KHR; }\n"
            "\tvoid waitPoint(long long timeoutNs) { context->fenceWait(point, timeoutNs); poll(); }\n\n"
            "private:\n\tint point;\n\tEGLint status;\n")
    return rep(s, old2, new2)

def libegl_cpp(s):
    s = rep(s, "long v95e_polls = 0, v95e_poll_us = 0, v95e_cwaits = 0;\n",
            "long v95e_polls = 0, v95e_poll_us = 0, v95e_cwaits = 0;\n"
            "#if defined(__ANDROID__) && defined(__BIONIC__)\n#include <cutils/properties.h>\n#endif\n"
            "static bool v96_realFence()   // V96: persist.swiftangle.fence (1 por defecto)\n"
            "{\n"
            "\tstatic int cached = -1;\n"
            "\tif(cached < 0)\n"
            "\t{\n"
            "\t\tcached = 1;\n"
            "\t\t#if defined(__ANDROID__) && defined(__BIONIC__)\n"
            "\t\tchar v[PROPERTY_VALUE_MAX] = {};\n"
            "\t\tif(property_get(\"persist.swiftangle.fence\", v, \"1\") > 0) cached = (v[0] != '0') ? 1 : 0;\n"
            "\t\t#endif\n"
            "\t}\n"
            "\treturn cached == 1;\n"
            "}\n")
    old_cw = "\tif(!eglSync->isSignaled())\n\t{\n\t\tv95e_cwaits++;   // V95_STATS\n\t\teglSync->wait();\n\t}\n\n\treturn success(EGL_CONDITION_SATISFIED_KHR);\n"
    new_cw = ("\tif(v96_realFence())   // V96\n"
              "\t{\n"
              "\t\tif(eglSync->poll())\n"
              "\t\t{\n"
              "\t\t\treturn success(EGL_CONDITION_SATISFIED_KHR);\n"
              "\t\t}\n"
              "\t\tif(timeout == 0)\n"
              "\t\t{\n"
              "\t\t\treturn success(EGL_TIMEOUT_EXPIRED_KHR);\n"
              "\t\t}\n"
              "\t\tv95e_cwaits++;\n"
              "\t\tlong t0 = v95e_now_us();\n"
              "\t\teglSync->waitPoint(timeout == EGL_FOREVER_KHR ? -1LL : (long long)timeout);\n"
              "\t\tv95e_poll_us += v95e_now_us() - t0;\n"
              "\t\treturn success(eglSync->isSignaled() ? EGL_CONDITION_SATISFIED_KHR : EGL_TIMEOUT_EXPIRED_KHR);\n"
              "\t}\n\n"
              "\tif(!eglSync->isSignaled())\n\t{\n\t\tv95e_cwaits++;   // V95_STATS\n\t\teglSync->wait();\n\t}\n\n\treturn success(EGL_CONDITION_SATISFIED_KHR);\n")
    s = rep(s, old_cw, new_cw)
    old_ga = "\t\t{ long t0 = v95e_now_us(); if(!eglSync->isSignaled()) v95e_polls++; eglSync->wait(); v95e_poll_us += v95e_now_us() - t0; }   // V95_STATS (TODO: Don't block)\n"
    new_ga = ("\t\tif(v96_realFence())   // V96: sin drenar\n"
              "\t\t{\n"
              "\t\t\tif(!eglSync->poll()) v95e_polls++;\n"
              "\t\t}\n"
              "\t\telse\n"
              "\t\t{ long t0 = v95e_now_us(); if(!eglSync->isSignaled()) v95e_polls++; eglSync->wait(); v95e_poll_us += v95e_now_us() - t0; }   // V95_STATS (TODO: Don't block)\n")
    s = rep(s, old_ga, new_ga)
    return s

def eglsurface_cpp(s):
    old = "\t\t\t__android_log_print(ANDROID_LOG_INFO, \"V95_EGL\","
    new = "\t\t\tif(v96_stats_enabled()) __android_log_print(ANDROID_LOG_INFO, \"V95_EGL\","
    s = rep(s, old, new)
    s = rep(s, "extern long v95e_polls, v95e_poll_us, v95e_cwaits;\n",
            "extern long v95e_polls, v95e_poll_us, v95e_cwaits;\n"
            "#if defined(__ANDROID__) && defined(__BIONIC__)\n#include <cutils/properties.h>\n#endif\n"
            "static bool v96_stats_enabled()   // V96\n"
            "{\n"
            "\t#if defined(__ANDROID__) && defined(__BIONIC__)\n"
            "\tchar v[PROPERTY_VALUE_MAX] = {};\n"
            "\treturn property_get(\"persist.swiftangle.stats\", v, \"0\") > 0 && v[0] == '1';\n"
            "\t#else\n"
            "\treturn false;\n"
            "\t#endif\n"
            "}\n")
    return s

try:
    patch(SW / "Common/V95Stats.hpp", v95stats_hpp)
    patch(SW / "Common/Resource.cpp", resource_cpp)
    patch(SW / "Reactor/LLVMReactor.cpp", llvmreactor_cpp)
    patch(SW / "OpenGL/libGLESv2/libGLESv2.cpp", libglesv2_cpp)
    patch(SW / "Renderer/Renderer.hpp", renderer_hpp)
    patch(SW / "Renderer/Renderer.cpp", renderer_cpp)
    patch(SW / "OpenGL/libGLESv2/Device.hpp", device_hpp)
    patch(SW / "OpenGL/libGLESv2/Device.cpp", device_cpp)
    patch(SW / "OpenGL/libEGL/Context.hpp", eglcontext_hpp)
    patch(SW / "OpenGL/libGLESv2/Context.h", es2context_h)
    patch(SW / "OpenGL/libGLESv2/Context.cpp", es2context_cpp)
    patch(SW / "OpenGL/libEGL/Sync.hpp", sync_hpp)
    patch(SW / "OpenGL/libEGL/libEGL.cpp", libegl_cpp)
    patch(SW / "OpenGL/libEGL/Surface.cpp", eglsurface_cpp)
except RuntimeError as e:
    print("V96_ERROR:", e); sys.exit(1)
print("V96_DONE")
