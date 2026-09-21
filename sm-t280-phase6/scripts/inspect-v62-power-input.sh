#!/usr/bin/env bash
set -e
cd /home/lineage/android/lineage-17.1

printf '%s\n' '=== Key flag parser ==='
grep -RIn --exclude-dir=.git 'Expected key flag label\|key flag label\|mapKey.*status' frameworks system 2>/dev/null | head -120 || true
sed -n '230,310p' frameworks/native/libs/input/KeyLayoutMap.cpp
grep -RIn --exclude-dir=.git 'lookupValueByLabel.*flag\|POLICY_FLAG_VIRTUAL\|POLICY_FLAG_FUNCTION' frameworks/native/libs/input frameworks/native/include 2>/dev/null | head -120 || true
grep -RIn --exclude-dir=.git 'getKeyFlagByLabel' frameworks/native 2>/dev/null || true
sed -n '420,465p' frameworks/native/include/input/InputEventLabels.h
grep -RIn --exclude-dir=.git 'WAKE_DROPPED\|"WAKE"' frameworks/native/libs/input frameworks/native/include 2>/dev/null | head -120 || true
grep -RIn --exclude-dir=.git 'static const.*flag\|WAKE_DROPPED\|POLICY_FLAG_WAKE' frameworks/native/libs/input frameworks/native/services/inputflinger 2>/dev/null | head -300 || true
grep -RIn --exclude-dir=.git 'WAKE_DROPPED\|POLICY_FLAG_WAKE\|POLICY_FLAG_PASS_TO_USER\|mapKey.*policyFlags' frameworks/native/services/inputflinger frameworks/base/services/core/jni frameworks/base/services/core/java/com/android/server/policy 2>/dev/null | head -240 || true

printf '%s\n' '=== keylayout sources ==='
find device/samsung/gtexswifi vendor/samsung/gtexswifi -type f \( -name '*.kl' -o -name '*.idc' \) -print -exec sed -n '1,80p' {} \; 2>/dev/null || true
grep -RIn --exclude-dir=.git 'sci-keypad.kl\|Generic.kl\|PRODUCT_COPY_FILES.*keylayout' device/samsung/gtexswifi vendor/samsung/gtexswifi 2>/dev/null || true

printf '%s\n' '=== current V61 kernel changes ==='
grep -n -A35 -B15 'gtex_panel_resume\|sprdfb_pan_display\|late_resume\|early_suspend' kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c | head -280 || true

printf '%s\n' '=== power key driver ==='
grep -n -A80 -B30 'KEY_POWER\|PB_INT\|sci_keypad' kernel/samsung/gtexswifi/drivers/input/keyboard/sc_keypad.c | head -360 || true
sed -n '450,560p' kernel/samsung/gtexswifi/drivers/input/keyboard/sc_keypad.c
