# Phase 5 -- V15: /data mounts READ-ONLY (invalid fs) -> format

Date: 2026-09-18. Source: `results/fase-5/v15-hang-recovery/last_kmsg.txt` +
ADB inspection of the block device in recovery.

## Results

- binder `bad object type`: **0** (the PTR case in `buffer_release` fixed it). OK
- `/data`: **mounts but read-only**. Cascade of
  `mkdir /data/... failed: Read-only file system`,
  `SELinux: setxattr failed: /data: Read-only file system`, and therefore
  `dalvik-cache`/`keystore` fail.
- `hwservicemanager`: still SIGSEGV (null deref); pending, does not depend on
  /data.

## Cause of /data RO

`userdata` = `/dev/block/mmcblk0p27`. In recovery, `blkid` and `dumpe2fs -h` **do
not recognize a valid ext4** on that partition. The fs is corrupt/absent (it was
the `ext4_find_entry` of mmcblk0p25/27 seen since V12). fs_mgr cannot mount it
RW; the `formattable` flag does not fire because the mount does not fully fail (it
stays RO).

## Action: format /data

The user deemed the loss of `/data` acceptable. It only affects the `userdata`
partition (mmcblk0p27); it does NOT touch boot/system/PIT. **It does not require
reflashing V15.**

Options (once formatted, boot to system and capture):

1. Recovery V21 -> **Wipe -> Format data / Factory reset** (the user does it; it is
   the path that creates the fs as LineageOS expects).
2. Via ADB from recovery (root):
   `mke2fs -t ext4 /dev/block/platform/sdio_emmc/by-name/userdata`
   (or `mkfs.ext4`). Available in the recovery.

After formatting, `/data` should mount RW (plain `formattable` fstab), and the
post-fs-data failure cascade should disappear.

## Format performed (2026-09-18)

`/data` (mmcblk0p27) formatted via ADB from recovery:
`mke2fs -F -t ext4 -L data /dev/block/platform/sdio_emmc/by-name/userdata`.
Result: clean ext4, 1,291,264 4k blocks (~5.28 GB), 323,200 inodes, journal
created, UUID `627f2f44-bffa-4a72-bf72-92f00c7eae88`. (`blkid`/`e2fsck` are not
in the recovery PATH, but mke2fs reported everything `done`.) V15 was not reflashed.
Next: reboot to system and capture `last_kmsg`.

## Next

- (Done) Format /data -> boot to system (V15 already flashed) -> capture `last_kmsg`.
- Re-evaluate the `hwservicemanager` SIGSEGV: if it persists with /data now
  mounted, look in detail at the PTR case of `binder_transaction` or the VINTF
  manifest.
