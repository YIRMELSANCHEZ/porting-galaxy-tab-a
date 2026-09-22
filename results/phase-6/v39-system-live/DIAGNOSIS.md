# Phase 6 -- V39: audio HAL registers (6.4b advanced). Blocker: missing audio policy xi:includes

Date: 2026-09-19. Source: V39 flashed, `results/phase-6/v39-system-live/`. User: "animation".

## Progress -- the audio HIDL service starts and REGISTERS IDevicesFactory

`init.svc.vendor.audio-hal-2-0=running`. audiohalservice log:
```
E Could not get passthrough implementation for android.hardware.audio@5.0::IDevicesFactory  (no 5.0-impl, expected)
I Registration complete for android.hardware.audio@4.0::IDevicesFactory/default
I Registration complete for android.hardware.audio.effect@4.0::IEffectsFactory/default
```
-> The @4.0 passthrough wraps the legacy HAL audio.primary.sc8830 correctly. AudioFlinger now constructs
(`AudioFlinger: Using default 3000 mSec as standby time`); the previous null-deref (null IDevicesFactory) is
PASSED.

## NEW crash point (same audioserver, further along): audio policy config

audioserver now dies in AudioPolicyService (not in AudioFlinger):
```
F libc: Fatal signal 11 (SIGSEGV), fault addr 0x68 (null deref), audioserver
  #00 libaudiopolicyenginedefault.so  VolumeGroup::addSupportedStream()+16
  #01 EngineBase::loadAudioPolicyEngineConfig()+920
  #02 Engine::Engine()
  #04 AudioPolicyManager::initialize()
  #06 AudioPolicyService::onFirstRef()
```
ROOT cause (config, not code):
```
E APM::Serializer: deserialize: libxml failed to resolve XIncludes on
  /system/etc/audio_policy_configuration.xml document.
E APM::AudioPolicyEngine/Config: parseLegacyVolumeFile: libxml failed to resolve
  XIncludes on document /system/etc/audio_policy_configuration.xml
```
audio_policy_configuration.xml references 5 <xi:include> (a2dp/usb/r_submix + audio_policy_volumes.xml +
default_volume_tables.xml) but NONE were installed (the device only packaged the main file). libxml does
not resolve the XIncludes -> EMPTY volume groups -> a stream references a null VolumeGroup ->
addSupportedStream on null -> SIGSEGV. audioserver does not publish media.audio_policy -> system_server
stays in "Waiting for service 'media.audio_policy'". LAST known blocker before boot_completed.

## V40 (fix) -- install the 5 audio policy xi:includes

`apply-v40-audio-policy-includes.py`: PRODUCT_COPY_FILES of
frameworks/av/services/audiopolicy/config/{a2dp,usb,r_submix}_audio_policy_configuration.xml +
audio_policy_volumes.xml + default_volume_tables.xml to /system/etc (same dir as the config; relative
XInclude). With the includes resolved, the volume groups are populated and AudioPolicyManager::initialize
does not crash. system.img only; boot = V35.

Expected success: audioserver starts fully and publishes media.audio_policy; system_server exits the loop
and (ideally) reaches sys.boot_completed=1.

## keystore (SIGABRT) -- pending separately
Still restarting (abort in keystore main -> libbase LogMessage fatal). Backtrace: main+1202 ->
LogMessage::~LogMessage -> DefaultAborter -> abort. Probable failure of the keymaster HAL or a keystore
boot check. Does NOT seem to block system_server directly (it only waited for health and then
audio_policy). Re-evaluate after V40.
