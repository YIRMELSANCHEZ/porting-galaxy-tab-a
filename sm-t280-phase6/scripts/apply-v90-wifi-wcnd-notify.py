#!/usr/bin/env python3
# V90 (WIFI/BT coexistence, root cause measured 2026-09-21 in V87):
# wcnd (blob) keeps the count of CP2 (Marlin) clients: BT-OPEN/BT-CLOSE are sent by libbt-vendor and
# WIFI-OPEN/WIFI-CLOSE were sent by the 5.1 Wi-Fi HAL (hardware/sprd/wlan/wifi_legacy/wifi_priv.c,
# sprd_wifi_preload_driver / sprd_wifi_after_unload_driver). Our A10 libwifi_hal does not notify, so
# wcnd thinks CP2 is stopped (WCND_STATE_CP2_STOPPED) even though Wi-Fi works (it was started
# by the `download` service at boot). Consequence measured in the wcnd log: on turning BT on it does
# "Enter WCND_STATE_CP2_STARTING from WCND_STATE_CP2_STOPPED" -> startwcn (restarts CP2) -> the
# sprdwl driver loses the chip (cfg80211_report_scan_frame err, 0 networks, DisconnectedState) and on
# turning BT off it does stopwcn (the same). With both correctly open wcnd does not restart CP2.
# Patch: libwifi_hal sends "wcn WIFI-OPEN" to wcnd (abstract socket "wcnd") before loading sprdwl and
# "wcn WIFI-CLOSE" after unloading it, waiting for "BTWIFI-CMD OK" (same protocol as 5.1). A wcnd
# failure does not block the driver load (it is only logged). Idempotent.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/frameworks/opt/net/wifi/libwifi_hal/wifi_hal_common.cpp")
s = p.read_text(encoding="utf-8")
if "V90_WCND" in s:
    print("wifi_hal_common.cpp: already patched (V90)"); print("V90_DONE"); sys.exit(0)

helper = '''#include <sys/syscall.h>
#include <cutils/sockets.h>   /* V90_WCND */
#include <string.h>
#include <sys/socket.h>

// V90_WCND: wcnd (SPRD, Marlin/CP2) cuenta los usuarios del coprocesador. Sin este aviso cree que
// el CP2 esta parado y lo reinicia en cada BT-OPEN/BT-CLOSE, tirando el Wi-Fi.
static int wcnd_notify(const char *cmd) {
  int fd = -1;
  for (int retry = 0; retry < 20 && fd < 0; retry++) {
    fd = socket_local_client("wcnd", ANDROID_SOCKET_NAMESPACE_ABSTRACT, SOCK_STREAM);
    if (fd < 0) usleep(100 * 1000);
  }
  if (fd < 0) {
    PLOG(ERROR) << "V90_WCND: cannot connect to wcnd for '" << cmd << "'";
    return -1;
  }
  struct timeval tv = {20, 0};
  setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  char buf[128] = {0};
  int ret = -1;
  if (TEMP_FAILURE_RETRY(write(fd, cmd, strlen(cmd) + 1)) > 0) {
    int n = TEMP_FAILURE_RETRY(read(fd, buf, sizeof(buf) - 1));
    if (n > 0 && strstr(buf, "BTWIFI-CMD OK")) ret = 0;
    LOG(INFO) << "V90_WCND: '" << cmd << "' -> " << n << " bytes '" << buf << "'";
  } else {
    PLOG(ERROR) << "V90_WCND: write failed for '" << cmd << "'";
  }
  close(fd);
  return ret;
}
'''
edits = [
    ("#include <sys/syscall.h>\n", helper),
    ('''  if (insmod(DRIVER_MODULE_PATH, DRIVER_MODULE_ARG) < 0) return -1;
#endif
''',
     '''  if (wcnd_notify("wcn WIFI-OPEN") < 0) {   /* V90_WCND */
    LOG(WARNING) << "V90_WCND: WIFI-OPEN not acknowledged, loading driver anyway";
  }
  if (insmod(DRIVER_MODULE_PATH, DRIVER_MODULE_ARG) < 0) return -1;
#endif
'''),
    ('''    usleep(500000); /* allow card removal */
    if (count) {
      return 0;
    }
    return -1;''',
     '''    usleep(500000); /* allow card removal */
    if (count) {
      wcnd_notify("wcn WIFI-CLOSE");   /* V90_WCND */
      return 0;
    }
    return -1;'''),
]
for old, new in edits:
    if s.count(old) != 1:
        print(f"V90_ERROR: unique block not found ({s.count(old)}): {old[:50]!r}"); sys.exit(1)
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("wifi_hal_common.cpp: aviso WIFI-OPEN/WIFI-CLOSE a wcnd")
print("V90_DONE")
