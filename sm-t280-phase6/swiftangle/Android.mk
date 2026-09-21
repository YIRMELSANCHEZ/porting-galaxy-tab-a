LOCAL_PATH := $(call my-dir)

# SwiftAngle: APK de sistema con SwiftShader (GLES 3.0 por CPU, armeabi-v7a) expuesto como
# "paquete ANGLE" de Android 10. Las libs prebuilt se generan con build-v78 a partir de los
# modulos lib*_swiftshader (external/swiftshader) renombrados a lib*_angle.so.
include $(CLEAR_VARS)
LOCAL_PACKAGE_NAME := SwiftAngle
LOCAL_MODULE_TAGS := optional
LOCAL_SRC_FILES := $(call all-java-files-under, src)
# GraphicsEnvironment.setupAngleRulesApk abre el asset a4a_rules.json del paquete ANGLE; si no
# existe, no configura el driver aunque haya opt-in por app. Lo abre con AssetManager.openFd(), que
# falla si el asset esta comprimido en el APK (V78): -0 .json lo deja almacenado sin comprimir (V79;
# aapt2 2.19 compara el sufijo literal, "-0 json" no surte efecto).
LOCAL_ASSET_DIR := $(LOCAL_PATH)/assets
LOCAL_AAPT_FLAGS := -0 .json
LOCAL_SDK_VERSION := current
LOCAL_CERTIFICATE := platform
LOCAL_PRIVILEGED_MODULE := false
LOCAL_MODULE_PATH := $(TARGET_OUT)/app
LOCAL_PREBUILT_JNI_LIBS := \
    lib/armeabi-v7a/libEGL_angle.so \
    lib/armeabi-v7a/libGLESv2_angle.so \
    lib/armeabi-v7a/libGLESv1_CM_angle.so
LOCAL_DEX_PREOPT := false
include $(BUILD_PACKAGE)
