# Phase 4 -- Download Mode preflight

Date: September 16, 2026.

## Result

**DOWNLOAD_MODE_READ_ONLY_PREFLIGHT_PASS**

Entry into Download Mode was done manually and authorized. Only the screen and
the Windows USB enumeration were observed. Odin, Heimdall or any write command
was not run.

## Visual evidence

| Field | Observed value |
|---|---|
| Mode | `ODIN MODE` |
| Product Name | `SM-T280` |
| Current Binary | `Samsung Official` |
| System Status | `Official` |
| FRP Lock | `ON` |
| Secure Download | `Enabled` |
| Knox Warranty Void | `0x0` |
| RP SWREV | `B:0 K:0 S:0` |

The reading comes from the photograph provided by the user. The device
identifier is not reproduced in this report.

## USB enumeration

| Field | Value |
|---|---|
| Windows status | `OK` |
| USB VID/PID | `04E8:685D` |
| Device | `SAMSUNG Mobile USB CDC Composite Device` |
| Service | `dg_ssudbus` |
| Vendor | `SAMSUNG Electronics Co., Ltd.` |
| Driver | `2.21.4.0` |
| ADB in Download Mode | absent, expected behavior |

## Assessment

- The identity matches `SM-T280` and not SM-T285.
- The Knox counter shows no prior modification (`0x0`).
- Binary and system declare themselves official.
- FRP is active. No unlock or bypass operation should be attempted.
- `RP SWREV B:0` is consistent with binary revision 0 of the AQJ1 stock firmware.
- The exact validated stock firmware is a consistent restore candidate.
- USB recognition is demonstrated, but an Odin/Heimdall protocol session has not
  been tested yet and no partition has been written.

## Next gate

Exit from Download Mode completed without flashing. The user confirmed the
tablet turned on and booted stock Android normally again.

Before any first write there must be an explicit and independent authorization.

## Later OEM Unlock / FRP check

After explicit user authorization, `OEM Unlock` was enabled through the official
Android interface. A new manual entry into Download Mode showed:

| Field | Observed value |
|---|---|
| Product Name | `SM-T280` |
| Current Binary | `Samsung Official` |
| System Status | `Official` |
| FRP Lock | `OFF` |
| Secure Download | `Enabled` |
| Knox Warranty Void | `0x0` |

**FRP_OFF_VERIFIED**

The check was visual only. No write was run during this verification. The change
removes the lock that rejected the first attempt, but does not yet prove the
custom recovery will boot.
