#!/usr/bin/env python3
# V13: "multi-binder" backport to the 3.10 binder driver (Treble/Android 10).
# Creates /dev/binder, /dev/hwbinder, /dev/vndbinder with a per-device context
# manager. Without it, the HIDL services abort with EBADF (-9). Idempotent.
import sys, re

F = "/home/lineage/android/lineage-17.1/drivers/staging/android/binder.c"
# The real kernel tree:
F = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/staging/android/binder.c"

with open(F, "r", encoding="utf-8", errors="surrogateescape") as fh:
    s = fh.read()

if "struct binder_device {" in s:
    print("V13_PATCH_ALREADY_PRESENT")
    sys.exit(0)

def req(old, new, s):
    if old not in s:
        print("ERROR: block not found:\n" + old, file=sys.stderr)
        sys.exit(2)
    return s.replace(old, new, 1)

# R1: replace the context manager globals with structs + a device list.
R1_OLD = ("static struct binder_node *binder_context_mgr_node;\n"
          "static kuid_t binder_context_mgr_uid = INVALID_UID;\n"
          "static int binder_last_id;\n")
R1_NEW = ("static int binder_last_id;\n\n"
          "struct binder_context {\n"
          "\tstruct binder_node *binder_context_mgr_node;\n"
          "\tkuid_t binder_context_mgr_uid;\n"
          "\tconst char *name;\n"
          "};\n\n"
          "struct binder_device {\n"
          "\tstruct hlist_node hlist;\n"
          "\tstruct miscdevice miscdev;\n"
          "\tstruct binder_context context;\n"
          "};\n\n"
          "static char *binder_devices_param = \"binder,hwbinder,vndbinder\";\n"
          "static HLIST_HEAD(binder_devices);\n")
s = req(R1_OLD, R1_NEW, s)

# R2: campo context en struct binder_proc.
R2_OLD = "\tint pid;\n\tstruct vm_area_struct *vma;\n"
R2_NEW = "\tint pid;\n\tstruct binder_context *context;\n\tstruct vm_area_struct *vma;\n"
s = req(R2_OLD, R2_NEW, s)

# R3a: declarar binder_dev en binder_open.
R3A_OLD = ("static int binder_open(struct inode *nodp, struct file *filp)\n"
           "{\n"
           "\tstruct binder_proc *proc;\n")
R3A_NEW = ("static int binder_open(struct inode *nodp, struct file *filp)\n"
           "{\n"
           "\tstruct binder_proc *proc;\n"
           "\tstruct binder_device *binder_dev;\n")
s = req(R3A_OLD, R3A_NEW, s)

# R3b: set proc->context from the miscdevice.
R3B_OLD = ("\tget_task_struct(current);\n"
           "\tproc->tsk = current;\n"
           "\tINIT_LIST_HEAD(&proc->todo);\n")
R3B_NEW = ("\tget_task_struct(current);\n"
           "\tproc->tsk = current;\n"
           "\tbinder_dev = container_of(filp->private_data,\n"
           "\t\t\t\t  struct binder_device, miscdev);\n"
           "\tproc->context = &binder_dev->context;\n"
           "\tINIT_LIST_HEAD(&proc->todo);\n")
s = req(R3B_OLD, R3B_NEW, s)

# R4: context-manager uses -> per-context (proc in scope at every site).
n1 = s.count("binder_context_mgr_node")
n2 = s.count("binder_context_mgr_uid")
s = s.replace("binder_context_mgr_node", "proc->context->binder_context_mgr_node")
s = s.replace("binder_context_mgr_uid", "proc->context->binder_context_mgr_uid")
# Restore the field names inside the struct definition.
s = s.replace("struct binder_node *proc->context->binder_context_mgr_node;",
              "struct binder_node *binder_context_mgr_node;")
s = s.replace("kuid_t proc->context->binder_context_mgr_uid;",
              "kuid_t binder_context_mgr_uid;")
# binder_inc_node() has no 'proc'; use the node's own context.
s = s.replace("!(node == proc->context->binder_context_mgr_node &&",
              "!(node == node->proc->context->binder_context_mgr_node &&")

# R5a: replace the static miscdevice with an init_binder_device() helper.
R5A_OLD = ("static struct miscdevice binder_miscdev = {\n"
           "\t.minor = MISC_DYNAMIC_MINOR,\n"
           "\t.name = \"binder\",\n"
           "\t.fops = &binder_fops\n"
           "};\n")
R5A_NEW = ("static int __init init_binder_device(const char *name)\n"
           "{\n"
           "\tint ret;\n"
           "\tstruct binder_device *binder_device;\n\n"
           "\tbinder_device = kzalloc(sizeof(*binder_device), GFP_KERNEL);\n"
           "\tif (!binder_device)\n"
           "\t\treturn -ENOMEM;\n\n"
           "\tbinder_device->miscdev.fops = &binder_fops;\n"
           "\tbinder_device->miscdev.minor = MISC_DYNAMIC_MINOR;\n"
           "\tbinder_device->miscdev.name = name;\n\n"
           "\tbinder_device->context.binder_context_mgr_uid = INVALID_UID;\n"
           "\tbinder_device->context.name = name;\n\n"
           "\tret = misc_register(&binder_device->miscdev);\n"
           "\tif (ret < 0) {\n"
           "\t\tkfree(binder_device);\n"
           "\t\treturn ret;\n"
           "\t}\n\n"
           "\thlist_add_head(&binder_device->hlist, &binder_devices);\n\n"
           "\treturn ret;\n"
           "}\n")
s = req(R5A_OLD, R5A_NEW, s)

# R5b: in binder_init, replace the single misc_register with the device loop.
R5B_OLD = "\tret = misc_register(&binder_miscdev);\n"
R5B_NEW = ("\t{\n"
           "\t\tchar *device_name, *device_names, *names_orig;\n\n"
           "\t\tret = -ENOMEM;\n"
           "\t\tdevice_names = kstrdup(binder_devices_param, GFP_KERNEL);\n"
           "\t\tif (device_names) {\n"
           "\t\t\tnames_orig = device_names;\n"
           "\t\t\tret = 0;\n"
           "\t\t\twhile ((device_name = strsep(&device_names, \",\")) != NULL) {\n"
           "\t\t\t\tret = init_binder_device(device_name);\n"
           "\t\t\t\tif (ret)\n"
           "\t\t\t\t\tbreak;\n"
           "\t\t\t}\n"
           "\t\t\tkfree(names_orig);\n"
           "\t\t}\n"
           "\t}\n")
s = req(R5B_OLD, R5B_NEW, s)

with open(F, "w", encoding="utf-8", errors="surrogateescape") as fh:
    fh.write(s)
print("V13_PATCH_APPLIED context_mgr_node_refs=%d context_mgr_uid_refs=%d" % (n1, n2))
