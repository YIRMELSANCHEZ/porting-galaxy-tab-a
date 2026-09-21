#!/usr/bin/env python3
# V54 (WiFi - "connection without internet"): with V53 WiFi associates, DHCP gets an IP
# (192.168.1.175/24) and the lease brings the default route (0.0.0.0/0 -> 192.168.1.1). But:
#   ConnectivityService: Exception in addRoute for gateway:
#     ServiceSpecificException: Network is unreachable (code 101)
# -> the default route is not installed -> DNS (outside the subnet) is unreachable
# (ENONET) -> "connection without internet". The gateway 192.168.1.1 DOES answer ping and the subnet
# route is in the wlan0 table, but adding the gatewayed default fails with
# ENETUNREACH. CONFIRMED on the device: `ip route add default via 192.168.1.1 dev wlan0
# table wlan0` -> "Network is unreachable"; with the ONLINK flag ->
# `ip route add default via 192.168.1.1 dev wlan0 table wlan0 onlink` -> OK and ping 8.8.8.8 +
# DNS WORK. It is a kernel 3.10 quirk: it rejects the gatewayed route because the
# gateway reachability validation fails, even though it is on-link; ONLINK skips it.
#
# Fix: netd does not use ONLINK when installing routes. modifyIpRoute() is patched in
# system/netd/server/RouteController.cpp to set rtm_flags = RTNH_F_ONLINK when there is
# a nexthop (gateway). For this device (a single interface, gateway always in the local subnet)
# it is safe. netd goes in system.img; boot = V53 (dd2d8154). Cumulative over V53. Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/system/netd/server/RouteController.cpp"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "RTNH_F_ONLINK" in s:
    print("V54_ALREADY"); sys.exit(0)

OLD = (
    "    rtmsg route = {\n"
    "        .rtm_protocol = RTPROT_STATIC,\n"
    "        .rtm_type = type,\n"
    "        .rtm_family = family,\n"
    "        .rtm_dst_len = prefixLength,\n"
    "        .rtm_scope = static_cast<uint8_t>(nexthop ? RT_SCOPE_UNIVERSE : RT_SCOPE_LINK),\n"
    "    };\n"
)
NEW = (
    "    rtmsg route = {\n"
    "        .rtm_protocol = RTPROT_STATIC,\n"
    "        .rtm_type = type,\n"
    "        .rtm_family = family,\n"
    "        .rtm_dst_len = prefixLength,\n"
    "        .rtm_scope = static_cast<uint8_t>(nexthop ? RT_SCOPE_UNIVERSE : RT_SCOPE_LINK),\n"
    "        // V54: el kernel 3.10 rechaza rutas gatewayed sin ONLINK (ENETUNREACH aunque el\n"
    "        // gateway este on-link). Forzar ONLINK cuando hay nexthop -> la default se instala.\n"
    "        .rtm_flags = static_cast<unsigned>(nexthop ? RTNH_F_ONLINK : 0),\n"
    "    };\n"
)

if OLD not in s:
    print("V54_ERROR: cannot find the expected rtmsg route initializer")
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V54_APPLIED -> netd RouteController: RTNH_F_ONLINK on gatewayed routes")
