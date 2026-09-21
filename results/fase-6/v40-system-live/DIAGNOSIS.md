# Phase 6 -- V40: audio OK, system_server reaches systemReady. FINAL BLOCKER: keystore/keymaster

Date: 2026-09-19. Source: V40 flashed, `results/fase-6/v40-system-live/`. User: "animation".

## Progress -- audio resolved, boot almost complete

With the 5 audio policy xi:includes (V40): audioserver starts (`init.svc.audioserver=running`), publishes
`media.audio_policy` (`service check media.audio_policy: found`). system_server exits the loop and reaches
the END of boot: StartSystemUI, WebViewFactoryPreparation, MakeConnectivityServiceReady,
PhaseThirdPartyAppsCanStart, ActivityManagerService.systemReady. **systemReady is the last phase before
boot_completed.**

## FINAL BLOCKER: keystore aborts (no keymaster TEE) -> system_server dies at systemReady

```
FATAL EXCEPTION IN SYSTEM PROCESS: main
RuntimeException: Failed to boot service com.android.server.trust.TrustManagerService:
  onBootPhase threw an exception during phase 600
Caused by: NullPointerException: ...IKeystoreService.onKeyguardVisibilityChanged() on a
  null object reference
Zygote: Exit zygote because system server has terminated
```
IKeystoreService is NULL because keystore CRASHES (SIGABRT) on every attempt:
```
F keystore: keystore_main.cpp:141] Check failed:
  kmDevices[SecurityLevel::TRUSTED_ENVIRONMENT] Error no viable keymaster device found
Abort message: 'Check failed: kmDevices[SecurityLevel::TRUSTED_ENVIRONMENT] ...'
```
keystore_main.cpp creates the SOFTWARE fallback but ALSO REQUIRES a keymaster reporting TRUSTED_ENVIRONMENT
(TEE). The device has NO keymaster HAL registered (no Trusty/SPRD in the tree). Without keystore ->
IKeystoreService null -> TrustManagerService NPE in boot phase 600 -> system_server FATAL -> zygote
restarts. This was the LAST blocker (all others resolved): keystore had been restarting since V36 but is
only now on the critical path.

## V41 (fix) -- software keymaster presented as TRUSTED_ENVIRONMENT

The AOSP service android.hardware.keymaster@4.0-service registers CreateKeymasterDevice(
SecurityLevel::SOFTWARE) -> reports SOFTWARE, which would go to the SOFTWARE slot and leave
TRUSTED_ENVIRONMENT null (the CHECK would still fail). `apply-v41-keymaster.py`:
- service.cpp: SecurityLevel::SOFTWARE -> TRUSTED_ENVIRONMENT (the software keymaster presents itself as
  TEE). It is NOT a real TEE (software-backed keys; reduced security), reversible if the Spreadtrum Trusty
  keymaster is wired.
- PRODUCT_PACKAGES += android.hardware.keymaster@4.0-service (class early_hal; registers
  IKeymasterDevice/default; /system/vendor/bin/hw).
- VINTF manifest += keymaster@4.0 IKeymasterDevice (hwbinder).
system.img only; boot = V35.

Expected success: keystore starts and registers IKeystoreService; TrustManagerService does not NPE;
system_server completes systemReady -> sys.boot_completed=1 and (expected) UI / launcher.
