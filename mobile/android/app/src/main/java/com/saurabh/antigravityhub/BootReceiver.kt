package com.saurabh.antigravityhub

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action
        Log.i("BootReceiver", "Received boot broadcast: $action")
        if (action == Intent.ACTION_BOOT_COMPLETED ||
            action == "android.intent.action.QUICKBOOT_POWERON" ||
            action == "com.htc.intent.action.QUICKBOOT_POWERON") {
            try {
                val serviceIntent = Intent(context, HubForegroundService::class.java)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
                Log.i("BootReceiver", "Auto-started HubForegroundService on boot")
            } catch (e: Exception) {
                Log.e("BootReceiver", "Failed to start service on boot", e)
            }
        }
    }
}
