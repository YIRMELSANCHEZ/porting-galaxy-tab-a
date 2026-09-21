#!/usr/bin/env python3
"""V89: bounded recovery when the SC2331 client interface dies during startup.

The V87 finit_module retry covers the early "SDIO not ready" return, but hardware
testing showed a second race: Bluetooth and Wi-Fi start together on the shared
Marlin/SC2331 coprocesor.  sprdwl can load and create wlan0, then lose the Marlin
wake handshake while scanning.  Android 10 reports CMD_STA_START_FAILURE and
leaves Wi-Fi disabled even though the user's toggle remains enabled.

V89 turns that terminal state into a bounded, delayed full client-stack retry.
It does not reset wcnd/Marlin and does not touch Bluetooth.
"""

import sys
from pathlib import Path


ROOT = Path("/home/lineage/android/lineage-17.1")
SOURCE = ROOT / "frameworks/opt/net/wifi/service/java/com/android/server/wifi/WifiController.java"
MARKER = "V89_SC2331_START_RECOVERY"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        print(f"V89_ERROR: {label}: expected 1 block, found {count}")
        sys.exit(1)
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if MARKER in source:
    print("V89: Wi-Fi startup recovery already applied")
    print("V89_DONE")
    sys.exit(0)

source = replace_once(
    source,
    "    static final int CMD_DEFERRED_RECOVERY_RESTART_WIFI         = BASE + 22;\n",
    "    static final int CMD_DEFERRED_RECOVERY_RESTART_WIFI         = BASE + 22;\n"
    "    // V89_SC2331_START_RECOVERY: private message; BASE + 23 is unused in Q.\n"
    "    private static final int CMD_V89_STA_STABLE                 = BASE + 23;\n"
    "    private static final int V89_MAX_STA_START_RETRIES          = 6;\n"
    "    private static final int V89_STA_START_RETRY_DELAY_MS       = 15 * 1000;\n"
    "    private static final int V89_STA_STABLE_RESET_DELAY_MS      = 60 * 1000;\n",
    "constants",
)

source = replace_once(
    source,
    "    private int mRecoveryDelayMillis;\n",
    "    private int mRecoveryDelayMillis;\n\n"
    "    // Consecutive client-start failures. A successful 60 s window clears it.\n"
    "    private int mV89StaStartRetries;\n",
    "retry field",
)

source = replace_once(
    source,
    "                case CMD_DEFERRED_RECOVERY_RESTART_WIFI:\n"
    "                    break;\n",
    "                case CMD_DEFERRED_RECOVERY_RESTART_WIFI:\n"
    "                case CMD_V89_STA_STABLE:\n"
    "                    break;\n",
    "default-state message",
)

source = replace_once(
    source,
    "        public void enter() {\n"
    "            mActiveModeWarden.disableWifi();\n"
    "            // Supplicant can't restart right away, so note the time we switched off\n",
    "        public void enter() {\n"
    "            removeMessages(CMD_V89_STA_STABLE);\n"
    "            mActiveModeWarden.disableWifi();\n"
    "            // Supplicant can't restart right away, so note the time we switched off\n",
    "disabled enter",
)

source = replace_once(
    source,
    "                case CMD_WIFI_TOGGLED:\n"
    "                    if (mSettingsStore.isWifiToggleEnabled()) {\n"
    "                        if (doDeferEnable(msg)) {\n"
    "                            if (mHaveDeferredEnable) {\n"
    "                                //  have 2 toggles now, inc serial number and ignore both\n",
    "                case CMD_WIFI_TOGGLED:\n"
    "                    if (mSettingsStore.isWifiToggleEnabled()) {\n"
    "                        // A real user off/on cycle starts a fresh bounded attempt set.\n"
    "                        mV89StaStartRetries = 0;\n"
    "                        if (doDeferEnable(msg)) {\n"
    "                            if (mHaveDeferredEnable) {\n"
    "                                //  have 2 toggles now, inc serial number and ignore both\n",
    "manual-enable reset",
)

source = replace_once(
    source,
    "                case CMD_WIFI_TOGGLED:\n"
    "                    if (! mSettingsStore.isWifiToggleEnabled()) {\n"
    "                        if (checkScanOnlyModeAvailable()) {\n",
    "                case CMD_WIFI_TOGGLED:\n"
    "                    if (! mSettingsStore.isWifiToggleEnabled()) {\n"
    "                        removeMessages(CMD_V89_STA_STABLE);\n"
    "                        mV89StaStartRetries = 0;\n"
    "                        if (checkScanOnlyModeAvailable()) {\n",
    "manual-disable reset",
)

source = replace_once(
    source,
    "                case CMD_STA_START_FAILURE:\n"
    "                    if (!checkScanOnlyModeAvailable()) {\n"
    "                        transitionTo(mStaDisabledState);\n"
    "                    } else {\n"
    "                        transitionTo(mStaDisabledWithScanState);\n"
    "                    }\n"
    "                    break;\n",
    "                case CMD_STA_START_FAILURE:\n"
    "                    removeMessages(CMD_V89_STA_STABLE);\n"
    "                    if (mSettingsStore.isWifiToggleEnabled()\n"
    "                            && mV89StaStartRetries < V89_MAX_STA_START_RETRIES) {\n"
    "                        mV89StaStartRetries++;\n"
    "                        log(\"V89 SC2331 client start failure; retry \"\n"
    "                                + mV89StaStartRetries + \"/\"\n"
    "                                + V89_MAX_STA_START_RETRIES + \" in \"\n"
    "                                + V89_STA_START_RETRY_DELAY_MS + \" ms\");\n"
    "                        transitionTo(mStaDisabledState);\n"
    "                        sendMessageDelayed(CMD_RECOVERY_RESTART_WIFI_CONTINUE,\n"
    "                                V89_STA_START_RETRY_DELAY_MS);\n"
    "                    } else if (!checkScanOnlyModeAvailable()) {\n"
    "                        transitionTo(mStaDisabledState);\n"
    "                    } else {\n"
    "                        transitionTo(mStaDisabledWithScanState);\n"
    "                    }\n"
    "                    break;\n"
    "                case CMD_V89_STA_STABLE:\n"
    "                    if (mV89StaStartRetries != 0) {\n"
    "                        log(\"V89 SC2331 client stable for 60 s; retry counter reset\");\n"
    "                        mV89StaStartRetries = 0;\n"
    "                    }\n"
    "                    break;\n",
    "start-failure recovery",
)

source = replace_once(
    source,
    "            if (state == WifiManager.WIFI_STATE_UNKNOWN) {\n"
    "                logd(\"ClientMode unexpected failure: state unknown\");\n"
    "                sendMessage(CMD_STA_START_FAILURE);\n"
    "            } else if (state == WifiManager.WIFI_STATE_DISABLED) {\n",
    "            if (state == WifiManager.WIFI_STATE_UNKNOWN) {\n"
    "                removeMessages(CMD_V89_STA_STABLE);\n"
    "                logd(\"ClientMode unexpected failure: state unknown\");\n"
    "                sendMessage(CMD_STA_START_FAILURE);\n"
    "            } else if (state == WifiManager.WIFI_STATE_DISABLED) {\n",
    "callback failure",
)

source = replace_once(
    source,
    "            } else if (state == WifiManager.WIFI_STATE_ENABLED) {\n"
    "                // scan mode is ready to go\n"
    "                logd(\"client mode active\");\n"
    "            } else {\n",
    "            } else if (state == WifiManager.WIFI_STATE_ENABLED) {\n"
    "                // Do not call the SC2331 stable immediately: on hardware it can create\n"
    "                // wlan0 and still lose the Marlin wake handshake during the first scans.\n"
    "                removeMessages(CMD_V89_STA_STABLE);\n"
    "                sendMessageDelayed(CMD_V89_STA_STABLE,\n"
    "                        V89_STA_STABLE_RESET_DELAY_MS);\n"
    "                logd(\"client mode active\");\n"
    "            } else {\n",
    "callback enabled",
)

SOURCE.write_text(source, encoding="utf-8")
print("V89: bounded SC2331 client-start recovery applied")
print("V89_DONE")
