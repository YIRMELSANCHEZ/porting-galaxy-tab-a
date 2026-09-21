#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: verify-v68-vintf.sh ANDROID_ROOT}
product="$root/out/target/product/gtexswifi"
checker="$root/out/host/linux-x86/bin/checkvintf"
stage=$(mktemp -d /tmp/gtexswifi-v68-vintf.XXXXXX)
trap 'rm -rf "$stage"' EXIT

# system.img is a non-Treble system-as-root image. Recreate the logical mount
# layout expected by checkvintf without modifying the image or source tree.
ln -s "$product/system" "$stage/system"
ln -s "$product/system/vendor" "$stage/vendor"
ln -s "$product/system/product" "$stage/product"
if test -d "$product/system/odm"; then
  ln -s "$product/system/odm" "$stage/odm"
fi

log="$stage/checkvintf.stderr"
set +e
result=$("$checker" --check-compat --rootdir="$stage" \
  --property ro.product.first_api_level=22 \
  --property ro.boot.product.hardware.sku= 2>"$log")
status=$?
set -e
cat "$log" >&2

if test "$status" -eq 0 && test "$result" = "true"; then
  printf 'V68_VINTF_COMPATIBILITY_PASS\n'
  exit 0
fi

# V67 intentionally uses framework software GateKeeper and software Codec2.
# The stock 5.1 OMX blobs were disabled after proven process crashes. Accept
# exactly those three legacy gaps, but fail if checkvintf reports anything else.
required_count=$(grep -c '^[[:space:]]*required:' "$log" || true)
if test "$required_count" -eq 3 && \
   grep -Fq 'android.hardware.gatekeeper:' "$log" && \
   grep -Fq 'required: @1.0::IGatekeeper/default' "$log" && \
   grep -Fq 'required: @1.0::IOmxStore/default' "$log" && \
   grep -Fq 'required: @1.0::IOmx/default' "$log"; then
  printf 'V68_VINTF_EXPECTED_LEGACY_EXCEPTIONS gatekeeper=software omx=codec2_software\n'
  exit 0
fi

printf 'V68_VINTF_COMPATIBILITY_FAIL status=%s result=%s\n' "$status" "$result" >&2
exit 1
