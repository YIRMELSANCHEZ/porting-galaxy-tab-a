# Phase 4 -- Read-only USB preflight

Date: September 16, 2026.

## Result

**USB_READ_ONLY_PREFLIGHT_PASS**

The tablet was queried only via ADB in stock Android. No reboots, writes,
installs, configuration changes or Download Mode/recovery commands were run.

| Check | Result |
|---|---|
| ADB state | `device` |
| USB identifier | detected; masked in this report |
| Model | `SM-T280` |
| Device | `gtexswifi` |
| Product | `gtexswifixx` |
| Android | 5.1.1 / SDK 22 |
| Build | `LMY47V.T280XXU0AQJ1` |
| Bootloader | `T280XXU0AQJ1` |
| Build type | `user`, release keys |
| `ro.secure` | `1` |
| `ro.debuggable` | `0` |
| `ro.adb.secure` | `1` |
| Current USB | `mtp,adb` |
| Battery | 81%, present, health=good |
| Power | USB |
| Temperature | 30.5 degrees C |
| Voltage | 4,312 mV |

## Conclusion

The identity matches exactly the downloaded and validated stock firmware. The
Samsung driver and ADB work in normal Android mode. This does not yet prove the
device is recognized in Download Mode nor authorize a write.

The next gate requires manual entry into Download Mode without flashing, visual
reading of the security indicators and a USB enumeration check. It must be
authorized separately.
