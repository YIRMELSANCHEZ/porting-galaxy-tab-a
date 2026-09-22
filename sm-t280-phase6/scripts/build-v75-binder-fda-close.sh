#!/bin/bash
# V75: applies apply-v75-binder-fda-close.py, forces the kernel relink, verifies that
# binder_transaction_buffer_release references task_close_fd and packages boot(V75)+system(V73).
# Run inside WSL (user lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
KO=$OUT/obj/KERNEL_OBJ
OBJDUMP=$T/prebuilts/gcc/linux-x86/arm/arm-linux-androideabi-4.9/bin/arm-linux-androideabi-objdump

cd "$T"
python3 "$S/apply-v75-binder-fda-close.py"
touch kernel/samsung/gtexswifi/drivers/staging/android/binder.c
rm -f "$KO/drivers/staging/android/binder.o" "$KO/arch/arm/boot/zImage" "$KO/arch/arm/boot/Image" "$KO/vmlinux" "$OUT/kernel" "$OUT/boot.img"

source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
mka bootimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|Error |binder|boot.img|build completed|FAILED' | tail -20

echo "=== verify ==="
ls -la "$KO/drivers/staging/android/binder.o" "$OUT/boot.img"
# the function is static: find the block by its new error string and the task_close_fd calls
grep -c "bad FDA parent index" "$KO/drivers/staging/android/binder.o" | sed 's/^/cadena V75 en binder.o: /'
"$OBJDUMP" -d "$KO/drivers/staging/android/binder.o" 2>/dev/null | awk '/<binder_transaction_buffer_release>:/,/^$/' | grep -c "task_close_fd" | sed 's/^/llamadas a task_close_fd en binder_transaction_buffer_release: /'
grep -q "V74 (gtexswifi): port de" kernel/samsung/gtexswifi/fs/pnode.c && echo "V74 present in pnode.c"
sha256sum "$OUT/system.img" | cut -c1-16 | sed 's/^/system.img (should be 651e16773ccab288): /'

echo "=== package (boot V75 + system V73) ==="
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v73.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-binder-fda-PHASE6-v75-DO-NOT-FLASH.tar.md5"
