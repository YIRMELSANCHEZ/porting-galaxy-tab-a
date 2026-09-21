#!/usr/bin/env python3
# V81 (APP: SwiftAngle). With the V80 log the JIT says: "Symbols not found: __aeabi_f2iz, __aeabi_fadd,
# __aeabi_fcmpge, __aeabi_fcmpgt, __aeabi_fcmplt, __aeabi_fmul" = floating-point routines BY
# SOFTWARE: Reactor creates the TargetMachine with setMArch("arm") without CPU or features (empty mattrs on
# armv7), so LLVM generates code for a generic ARM without VFP/NEON. Besides not linking, it would be
# very slow. The real CPU is passed (llvm::sys::getHostCPUName -> cortex-a7) and its features
# (getHostCPUFeatures: vfpv4, neon, hwdiv...) to the EngineBuilder. Idempotent.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")
p = T / "external/swiftshader/src/Reactor/LLVMReactor.cpp"
s = p.read_text(encoding="utf-8", errors="surrogateescape")
if "V81" in s:
    print("LLVMReactor.cpp: already patched (V81)"); print("V81_DONE"); sys.exit(0)

edits = [
    ("#include <numeric>\n",
     '#include <numeric>\n#include "llvm/Support/Host.h"   /* V81 */\n'),
    ('''		LLVMReactorJIT(const char *arch, const llvm::SmallVectorImpl<std::string>& mattrs,
					   const llvm::TargetOptions &targetOpts):''',
     '''		LLVMReactorJIT(const char *arch, const std::string &cpu, const llvm::SmallVectorImpl<std::string>& mattrs,
					   const llvm::TargetOptions &targetOpts):   /* V81: +cpu */'''),
    ('''			targetMachine(llvm::EngineBuilder()
				.setMArch(arch)
				.setMAttrs(mattrs)''',
     '''			targetMachine(llvm::EngineBuilder()
				.setMArch(arch)
				.setMCPU(cpu)
				.setMAttrs(mattrs)'''),
    ('''#elif defined(__arm__)
#if __ARM_ARCH >= 8
		mattrs.push_back("+armv8-a");
#else
		// armv7-a requires compiler-rt routines; otherwise, compiled kernel
		// might fail to link.
#endif
#endif
''',
     '''#elif defined(__arm__)
		/* V81: sin CPU/features LLVM emite coma flotante por software (__aeabi_fadd...) */
		{
			llvm::StringMap<bool> hostFeatures;
			if(llvm::sys::getHostCPUFeatures(hostFeatures))
			{
				for(auto &f : hostFeatures)
				{
					mattrs.push_back((f.second ? "+" : "-") + f.first().str());
				}
			}
		}
#endif
		std::string cpu;   /* V81 */
#if defined(__arm__) || defined(__aarch64__)
		cpu = llvm::sys::getHostCPUName().str();
		if(cpu == "generic") { cpu.clear(); }
		{
			std::string feats;
			for(auto &m : mattrs) { feats += m + " "; }
			REACTOR_LOGE("Reactor: host cpu '%s' features: %s", cpu.c_str(), feats.c_str());
		}
#endif
'''),
    ('''			::reactorJIT = new LLVMReactorJIT(arch, mattrs, targetOpts);''',
     '''			::reactorJIT = new LLVMReactorJIT(arch, cpu, mattrs, targetOpts);   /* V81 */'''),
]
for old, new in edits:
    if s.count(old) != 1:
        print(f"V81_ERROR: unique block not found: {old[:70]!r}"); sys.exit(1)
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8", errors="surrogateescape")
print("LLVMReactor.cpp: host CPU and features in the TargetMachine")
print("V81_DONE")
