# V42 — Android 10 Codec2 / legacy ION compatibility

Date: 2026-09-19

## Purpose

V41 completed Android boot, but `mediaserver` restarted every five seconds because `/system/lib/libcodec2_vndk.so` required the unresolved symbol `ion_is_legacy`.

## Single-variable change

The SC8830 Spreadtrum ION compatibility library now exports:

```c
int ion_is_legacy(int fd)
{
    (void)fd;
    return 1;
}
```

This is correct for the device's Linux 3.10 handle-based ION driver. No V41 keymaster, framework, graphics, kernel, ramdisk, audio-policy, or boot changes were altered.

Source changed in the Android tree:

`hardware/sprd/libion_sprd/sc8830/ion.c`

Reproducible patch script:

`sm-t280-phase5/scripts/apply-v42-ion-legacy.py`

## Offline verification

- Build: `PASS`
- `libion_sprd.so` exports `ion_is_legacy`: `PASS`
- `libcodec2_vndk.so` imports `ion_is_legacy`: `PASS`
- Codec2 declares `libion.so` as a dependency: `PASS`
- `/system/lib/libion.so -> libion_sprd.so`: `PASS`
- Legacy sparse headers 32/16: `PASS`
- Odin package contains only `boot.img` and `system.img`: `PASS`
- Embedded Odin MD5: `PASS`

Markers:

```text
V42_ION_OFFLINE_VERIFY_PASS
ODIN_SYSTEM_PACKAGE_PASS
ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS
V42_PACKAGE_PASS
```

## Artifact

`sm-t280-phase5/packages/SM-T280-android10-ion-legacy-PHASE6-v42-DO-NOT-FLASH.tar.md5`

SHA-256:

```text
40515cd5f5c84b6a127426bdac5d526c071b983acc7ea2a810b38ad3f70711af
```

Embedded images:

- `boot.img`: `27c04393efb4ad77c6cc2df3fe5b3ac25cf1f1513d6f8f8502d207187b5fb5a4` (unchanged V35/V41 boot)
- legacy sparse `system.img`: `e67a3035a288ab8f5a2f58d98aa427f4916a0af88b5583f462c1a07efbbd70d5`

## Hardware test target

After the user flashes V42 under the existing Odin authorization, collect a fresh boot log and confirm:

1. `sys.boot_completed=1`.
2. `mediaserver` remains alive.
3. `media.player` is published.
4. The unresolved `ion_is_legacy` linker error is absent.
5. SetupWizard responds and produces a focused visible window.
6. The screen does not become visually black while Android reports display state `ON`.

Bluetooth and LMKD remain separate known issues and are not changed by V42.
