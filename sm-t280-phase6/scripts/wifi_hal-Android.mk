# V51: HAL WiFi generico nl80211 para sc2331/sc2341 (SPRD Marlin), copiado del HAL del
# emulador (device/generic/goldfish/wifi/wifi_hal) que implementa la wifi_hal func table via
# netlink/rtnetlink estandar sobre "wlan0". Se construye como modulo de ESTE device (no del
# goldfish, que solo compila para su producto), con LOCAL_VENDOR_MODULE para producir las
# variantes que necesita libwifi-hal (como libwifi-hal-fallback). Seleccionado por el caso
# BOARD_WLAN_DEVICE=sc2341 en frameworks/opt/net/wifi/libwifi_hal/Android.mk.
LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_CFLAGS := -Wall -Wextra -Werror
LOCAL_C_INCLUDES += \
	$(call include-path-for, libhardware_legacy)/hardware_legacy \

LOCAL_SRC_FILES := \
	halstate.cpp \
	info.cpp \
	interface.cpp \
	netlink.cpp \
	netlinkmessage.cpp \
	wifi_hal.cpp \

LOCAL_SHARED_LIBRARIES += \
	liblog \

LOCAL_HEADER_LIBRARIES += \
	libcutils_headers \

LOCAL_MODULE := libwifi-hal-generic
LOCAL_VENDOR_MODULE := true

include $(BUILD_STATIC_LIBRARY)
