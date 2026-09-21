package org.lineageos.gtexswifi.swiftangle;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Settings;
import android.util.Log;

/**
 * V87: mantiene SwiftAngle seleccionado para la app objetivo incluso tras borrar /data.
 * El APK es de sistema y esta firmado con la clave platform, por lo que puede escribir
 * Settings.Global. No activa ANGLE globalmente: el Mali sigue atendiendo al resto del sistema.
 */
public final class BootCompletedReceiver extends BroadcastReceiver {
    private static final String TAG = "SwiftAngle";
    private static final String TARGET_PACKAGE = "com.example.app";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            return;
        }

        boolean packagesWritten = Settings.Global.putString(
                context.getContentResolver(),
                "angle_gl_driver_selection_pkgs",
                TARGET_PACKAGE);
        boolean valuesWritten = Settings.Global.putString(
                context.getContentResolver(),
                "angle_gl_driver_selection_values",
                "angle");

        if (packagesWritten && valuesWritten) {
            Log.i(TAG, "ANGLE opt-in restored for " + TARGET_PACKAGE);
        } else {
            Log.e(TAG, "Could not restore ANGLE opt-in");
        }
    }
}
