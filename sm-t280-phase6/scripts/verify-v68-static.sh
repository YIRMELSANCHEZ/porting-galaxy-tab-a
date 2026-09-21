#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: verify-v68-static.sh ANDROID_ROOT}
device="$root/device/samsung/gtexswifi"

python3 - "$device/manifest.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
ET.parse(sys.argv[1])
print("V68_MANIFEST_XML_PARSE_PASS")
PY

grep -Fq 'V68 consolidated legacy-HAL bridge' "$device/device.mk"
grep -Fq 'android.hardware.bluetooth@1.0-service' "$device/device.mk"
grep -Fq 'android.hardware.sensors@1.0-service' "$device/device.mk"
grep -Fq 'android.hardware.power@1.0-service' "$device/device.mk"
grep -Fq 'android.hardware.camera.provider@2.4-service' "$device/device.mk"
grep -Fq 'android.hardware.gnss@1.0-service' "$device/device.mk"
grep -Fq 'android.hardware.light@2.0-service' "$device/device.mk"
grep -Fq 'android.hardware.memtrack@1.0-service' "$device/device.mk"
grep -Fq 'android.hardware.drm@1.2-service.clearkey' "$device/device.mk"

grep -Fq 'V68: binderized wrappers' "$device/manifest.xml"
grep -Fq '<instance>legacy/0</instance>' "$device/manifest.xml"
grep -Fq '<instance>clearkey</instance>' "$device/manifest.xml"
grep -Fq 'libiwnpi_source_unsupported' "$root/hardware/sprd/iwnpi/Android.mk"
grep -Fq 'libiwnpi.so:system/lib/libiwnpi.so' \
  "$root/vendor/samsung/gtexswifi/gtexswifi-vendor.mk"
if grep -Eq '^[+[:space:]]+libiwnpi$' "$device/device.mk"; then
  echo 'V68_STATIC_FAIL: incompatible source libiwnpi requested' >&2
  exit 1
fi

test -s "$device/rootdir/efs/.keep"
test -s "$device/rootdir/productinfo/.keep"
grep -Fq '/productinfo(/.*)?' "$device/sepolicy/file_contexts"
grep -Fq '/file_contexts\.bin' "$device/sepolicy/file_contexts"
grep -Fq 'V68: framebuffer/UMP handles' \
  "$root/hardware/sprd/gralloc/scx30g_v2/gralloc_module.cpp"
grep -Fq 'imageToSave.compress' \
  "$root/frameworks/base/packages/SystemUI/src/com/android/systemui/screenshot/GlobalScreenshot.java"
grep -Fq 'V68: retry the Spreadtrum HWC1/GSP' \
  "$root/hardware/interfaces/graphics/composer/2.1/utils/passthrough/include/composer-passthrough/2.1/HwcLoader.h"
grep -Fq 'V68: using V67 gralloc/framebuffer fallback' \
  "$root/hardware/interfaces/graphics/composer/2.1/utils/passthrough/include/composer-passthrough/2.1/HwcLoader.h"
grep -Fq 'V68: modem monitor disabled' \
  "$root/hardware/sprd/audio/sc8830/audio_hw.c"

# Deliberate exclusions: these services would wrap non-existent/inapplicable HALs.
if grep -Fq 'android.hardware.gatekeeper@1.0-service' "$device/device.mk"; then
  echo 'V68_STATIC_FAIL: gatekeeper HIDL must not replace software fallback' >&2
  exit 1
fi
if grep -Fq 'android.hardware.vibrator@1.0-service' "$device/device.mk"; then
  echo 'V68_STATIC_FAIL: vibrator service added without hardware' >&2
  exit 1
fi

printf 'V68_STATIC_VERIFY_PASS\n'
