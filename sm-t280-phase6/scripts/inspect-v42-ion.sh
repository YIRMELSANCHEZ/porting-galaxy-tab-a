#!/usr/bin/env bash
set -euo pipefail
cd /home/lineage/android/lineage-17.1
printf '%s\n' '=== source references ==='
grep -RIn --exclude-dir=.git --exclude='*.o' --exclude='*.so' 'ion_is_legacy' system hardware frameworks device vendor 2>/dev/null | head -100 || true
printf '%s\n' '=== relevant output libraries ==='
find out/target/product/gtexswifi/system -type f \( -name '*ion*.so' -o -name 'libcodec2_vndk.so' -o -name 'mediaserver' \) -print | sort
printf '%s\n' '=== undefined ion symbols in codec2 ==='
prebuilts/clang/host/linux-x86/clang-r353983c/bin/llvm-nm -D out/target/product/gtexswifi/system/lib/libcodec2_vndk.so 2>/dev/null | grep -E 'ion_| U ' | grep ion || true
printf '%s\n' '=== exported symbols in ion libraries ==='
while IFS= read -r file; do
  printf '\n-- %s --\n' "$file"
  prebuilts/clang/host/linux-x86/clang-r353983c/bin/llvm-nm -D "$file" 2>/dev/null | grep ' ion_' || true
done < <(find out/target/product/gtexswifi/system -type f -name '*ion*.so' | sort)
printf '%s\n' '=== build definitions ==='
grep -RIn --exclude-dir=.git 'cc_library.*libion\|name: "libion"\|LOCAL_MODULE.*libion' system/core/libion system/core/libion_mirror hardware 2>/dev/null | head -100 || true
printf '%s\n' '=== Spreadtrum ION implementation and makefile ==='
sed -n '1,260p' hardware/sprd/libion_sprd/sc8830/ion.c 2>/dev/null || true
sed -n '1,140p' hardware/sprd/libion_sprd/sc8830/Android.mk 2>/dev/null || true
