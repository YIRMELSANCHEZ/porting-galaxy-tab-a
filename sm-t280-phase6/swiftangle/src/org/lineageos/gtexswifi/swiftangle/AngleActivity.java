package org.lineageos.gtexswifi.swiftangle;

import android.app.Activity;
import android.os.Bundle;

/** Actividad vacia: solo existe para que GraphicsEnvironment resuelva el paquete "ANGLE". */
public class AngleActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        finish();
    }
}
