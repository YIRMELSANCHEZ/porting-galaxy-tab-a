#!/system/bin/sh
# Run ON THE TABLET (adb shell, root). Cleans the orphan synthetic password that brings down
# system_server on every boot (LockSettingsService.tryDeriveAuthTokenForUnsecuredPrimaryUser ->
# KeyPermanentlyInvalidatedException): PIN set at 03:47 (blob tied to the gatekeeper SID) and
# removed at 03:50 by editing locksettings.db, without regenerating the blob.
# Copia previa de todo en /data/local/tmp/lockstate-backup.
H=87375c6482c7083b
B=/data/local/tmp/lockstate-backup
mkdir -p $B
cp -a /data/system_de/0/spblob /data/misc/keystore/user_0 /data/misc/gatekeeper /data/system/locksettings.db $B/ 2>/dev/null
cp -a /data/misc/keystore/user_0/.1000_chr_USRPKEY_synthetic_password_$H $B/user_0/ 2>/dev/null
stop
stop keystore
stop gatekeeperd
sleep 2
rm -f /data/system_de/0/spblob/$H.pwd /data/system_de/0/spblob/$H.secdis /data/system_de/0/spblob/$H.spblob
rm -f /data/misc/keystore/user_0/.1000_chr_USRPKEY_synthetic_password_$H /data/misc/keystore/user_0/1000_USRPKEY_synthetic_password_$H
rm -f /data/misc/gatekeeper/0
sqlite3 /data/system/locksettings.db "update locksettings set value='0' where name='sp-handle' and user=0; pragma wal_checkpoint(TRUNCATE);"
echo "--- db"
sqlite3 /data/system/locksettings.db "select user,name,value from locksettings where name in ('sp-handle','lockscreen.password_type');"
echo "--- files"
ls -la /data/system_de/0/spblob /data/misc/keystore/user_0 /data/misc/gatekeeper
sync
echo FIXLOCK_DONE
