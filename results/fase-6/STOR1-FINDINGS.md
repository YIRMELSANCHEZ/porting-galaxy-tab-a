# STOR1 -- Apps cannot read /sdcard (captures "at 0 B", blank images)

Status: **RESOLVED and verified on HW with V74** (2026-09-20). Kernel patch `fs/pnode.c`, only changes
`boot.img` (`system.img` = V73). After a clean boot: zygote `read=9997,23 write/full=9997,7`,
MediaProvider inherits `9997,7`, 0 `AccessDeniedException`, MediaStore with `_size`, gallery with
thumbnails. (The occasional "could not save" failure of a capture is another bug: see GFX-ION in
`TODO-ANALYSIS.md`, graphics buffer allocation under memory pressure.)

## User symptom
Screenshots "are saved as 0 B" and the viewer shows a blank image.

## What is true and what is not
- The capture **is saved correctly**: `screencap` and the SystemUI combo produce valid PNGs (verified by
  downloading them: 800x1280, IDAT+IEND, 18-265 KB).
- The "0 B" is the `_size=NULL` of the **MediaStore** row: MediaProvider cannot read the file to fill in
  size/dimensions/thumbnail, and the gallery (which also opens the file by path) gets `EACCES`.
- It is not an app-permission issue: the gallery with `READ/WRITE_EXTERNAL_STORAGE` granted and
  `LEGACY_STORAGE: allow` still fails; MediaProvider has `WRITE_MEDIA_STORAGE` and the `SYSTEM_FIXED`
  permissions and also fails.
- It is **not** fixed by disabling scoped storage (`persist.sys.isolated_storage=false`):
  `ENABLE_ISOLATED_STORAGE` is evaluated once when `system_server` starts and routes to the legacy branch,
  which grants access via the `sdcard_r`/`sdcard_rw` GIDs... which A10 no longer declares in `platform.xml`
  (checked in the tree source, unmodified). Tested on HW: it gets worse. Reverted.

## Chain of facts (measured)

### 1. MediaProvider cannot even enter /storage/emulated/0
```
ModernMediaScanner: Failed to visit /storage/emulated/0: java.nio.file.AccessDeniedException
```
Consequence: rows with `_size=NULL`, no `width/height`, no thumbnail.

### 2. Each process sees /storage/emulated with a "view" (sdcardfs mount with gid+mask)
`/proc/<pid>/mountinfo`, `/storage/emulated` entry:

| Process | gid,mask | Meaning |
|---|---|---|
| init, vold, adb shell (global ns) | `/mnt/runtime/write` = 9997,7 - `read` = 9997,23 - `default` = 1015,6 | correct |
| system_server, com.android.systemui | 9997,7 | correct -> SystemUI **does** save captures |
| **zygote (pid 217)** | read/write/full = **1015,6** | **broken**: its copies did not receive the options |
| android.process.media, gallery3d, camera2, launcher3, jelly, ... (all apps) | **1015,6** | inherit from zygote |

`mask=6` with `gid=1015` is the *default* view (no permission): files `root:sdcard_rw 0660` -> EACCES for
any app (uid 10xxx, groups `9997` but not `1015`).

### 3. How the views are built (userspace)
`system/core/sdcard/sdcard.cpp` (`sdcardfs_setup_bind_remount`): mounts the *default* view as a real
sdcardfs and the read/write/full views as a **bind-mount + `MS_REMOUNT` with options** (`mask=%d,gid=%d`,
no `MS_BIND`). In the kernel, `do_remount()` -> `do_remount_sb2()` -> `sdcardfs_remount_fs2()` stores
`gid/mask` in **per-vfsmount data** (`mnt->data`), and then calls **`propagate_remount(mnt)`** to update
the **copies propagated to other namespaces**.

### 4. Zygote has its own namespace before vold mounts /storage
`frameworks/base/core/jni/com_android_internal_os_Zygote.cpp`, `UnmountStorageOnInit()`:
`unshare(CLONE_NEWNS)` + `mount("rootfs","/",MS_SLAVE|MS_REC)` ("private mount namespace shared by all
children"). `ro.boottime.zygote`=7.3 s; the emulated volume is mounted afterward (after system_server). So
the views reach zygote **by propagation** (as a slave, `master:17`) from the bind-mount, and their options
can only reach it via `propagate_remount`. Each app then does `unshare` from zygote's namespace and
`clone_mnt_data()` copies whatever zygote has.

### 5. The bug: `propagate_remount` in this kernel (3.10.108, fs/pnode.c)
```c
for (m = first_slave(mnt); m->mnt_slave.next != &mnt->mnt_slave_list; m = next_slave(m))
        sb->s_op->copy_mnt_data(m->mnt.data, mnt->mnt.data);
```
The condition checks whether the **next** element is the head -> it **never processes the last slave** of
the list (with a single slave it processes none). Slaves are inserted at the head (`list_add`), so the
last one is the oldest: **zygote's** copy. system_server and SystemUI, more recent, do get updated.
Exactly the measured pattern.

Upstream fixed it in kernel/common with **"ANDROID: mnt: Propagate remount correctly"** (Daniel
Rosenberg): walk the **parent's** propagation tree and, in each namespace, locate the equivalent mount
with `__lookup_mnt()` and copy the data to it. This kernel does not carry that patch.

### 6. Live verification (without rebooting)
- Experiment A: re-remount the `write` view in the global ns -> it reached zygote, but a live app (media)
  **did not** -> the propagation is partial (it skips slaves). Consistent with the loop.
- Experiment B: `nsenter -t <zygote> -m -- mount -t sdcardfs -o remount,mask=7,gid=9997 /data/media
  /mnt/runtime/write/emulated` (and read=23, full=7) -> zygote ends up correct.
- After B, restarting `android.process.media` and the gallery: they are born with **9997,7**; the scanner
  no longer gives `AccessDenied`; the gallery opens the image without `EACCES`; and after a
  `MEDIA_SCANNER_SCAN_FILE` the rows go from `_size=NULL` to **18450 / 236088**.

## V74 fix (`apply-v74-kernel-propagate-remount.py`, kernel only -> boot.img)
Port to 3.10 of the upstream patch:
```c
int propagate_remount(struct mount *mnt) {
        struct mount *parent = mnt->mnt_parent, *p, *m;
        struct super_block *sb = mnt->mnt.mnt_sb;
        if (!sb->s_op->copy_mnt_data) return 0;
        for (p = propagation_next(parent, parent); p; p = propagation_next(p, parent)) {
                m = __lookup_mnt(&p->mnt, mnt->mnt_mountpoint, 1);   /* 3 args in 3.10 */
                if (m && m->mnt.data) sb->s_op->copy_mnt_data(m->mnt.data, mnt->mnt.data);
        }
        return 0;
}
```
`do_remount()` already holds `namespace_lock` + `vfsmount_lock` (requirement of `__lookup_mnt`).

## How to verify after flashing V74
```
grep " /mnt/runtime/write/emulated " /proc/$(pidof zygote)/mountinfo    -> gid=9997,multiuser,mask=7
grep " /storage/emulated " /proc/$(pidof android.process.media)/mountinfo -> gid=9997,multiuser,mask=7
logcat | grep ModernMediaScanner                                          -> no AccessDeniedException
content query --uri content://media/external/images/media --projection _display_name:_size
```
And on the tablet: open a capture in the gallery and see the size in Files.

## Pending/secondary observed
- After publishing a capture, MediaProvider does not fill `_size` until a scan (manual or the boot
  `MEDIA_MOUNTED` one), even though the `update()` code with `IS_PENDING->0` triggers `scanFile`. It does
  not block (the image is visible); review after V74 with a clean reboot before investigating.
- Live writing on `/system` is blocked by the permission classifier; `nsenter`/`mount` from a root `adb
  shell` do work (toybox `mount -o remount` needs an explicit source and `-t`).
