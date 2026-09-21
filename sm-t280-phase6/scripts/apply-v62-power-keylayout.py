#!/usr/bin/env python3
"""V62: make the sci-keypad layout valid for the Android 10 input parser."""

import sys

path = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/keylayout/sci-keypad.kl"
expected_bad = (
    "key 116   POWER          WAKE\n"
    "key 114   VOLUME_DOWN\n"
    "key 115   VOLUME_UP\n"
    "key 9     CAMERA\n"
    "key 172   HOME          WAKE\n"
)
expected_good = (
    "# Android 10 accepts only VIRTUAL/FUNCTION/GESTURE key-layout flags.\n"
    "# POWER is handled by PhoneWindowManager and must not use the removed WAKE flag.\n"
    "key 116   POWER\n"
    "key 114   VOLUME_DOWN\n"
    "key 115   VOLUME_UP\n"
    "key 9     CAMERA\n"
    "key 172   HOME\n"
)

text = open(path, encoding="utf-8", errors="surrogateescape").read()
if text == expected_good:
    print("V62_KEYLAYOUT_ALREADY")
elif text != expected_bad:
    print("V62_ERROR: unexpected sci-keypad.kl contents")
    print(repr(text))
    sys.exit(1)
else:
    open(path, "w", encoding="utf-8", errors="surrogateescape").write(expected_good)
    print("V62_KEYLAYOUT_APPLIED")

