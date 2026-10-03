package com.saurabh.antigravityhub

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class HubForegroundService : Service() {
    private val TAG = "HubForegroundService"
    private val FOREGROUND_CHANNEL_ID = "antigravity_hub_foreground"
    private val ALERT_CHANNEL_ID = "default"
    private val NOTIFICATION_ID = 1001

    private var client: OkHttpClient? = null
    private var webSocket: WebSocket? = null
    private var isRunning = false
    private val retryHandler = Handler(Looper.getMainLooper())
    private var reconnectRunnable: Runnable? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startServiceInForeground()
        isRunning = true
        startWebSocket()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isRunning) {
            isRunning = true
            startWebSocket()
        }
        return START_STICKY
    }

    private fun startServiceInForeground() {
        val notification = createForegroundNotification()
        if (Build.VERSION.SDK_INT >= 34) {
            try {
                startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                )
            } catch (e: Exception) {
                Log.w(TAG, "Fallback to basic startForeground: ${e.message}")
                startForeground(NOTIFICATION_ID, notification)
            }
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

            // Low-priority, silent channel for persistent service notification
            val fgChannel = NotificationChannel(
                FOREGROUND_CHANNEL_ID,
                "Antigravity Hub Background Sync",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Maintains connection with your PC for 3-slot daily interview preparation"
                setShowBadge(false)
            }
            manager.createNotificationChannel(fgChannel)

            // High-priority alert channel for actual interview prep notifications
            val alertChannel = NotificationChannel(
                ALERT_CHANNEL_ID,
                "Antigravity Hub Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Real-time interview preparation alerts and action prompts"
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 250, 250, 250)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            manager.createNotificationChannel(alertChannel)
        }
    }

    private fun createForegroundNotification(): Notification {
        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, launchIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, FOREGROUND_CHANNEL_ID)
            .setContentTitle("Antigravity Hub Active")
            .setContentText("Connected to PC for 3-slot daily interview prep")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun getHubUrl(): String {
        val prefs = getSharedPreferences("antigravity_hub", Context.MODE_PRIVATE)
        val saved = prefs.getString("hub_url", null)
        if (!saved.isNullOrBlank()) {
            return saved
        }
        return "http://192.168.31.210:8765"
    }

    private fun startWebSocket() {
        try {
            webSocket?.close(1000, "Reconnecting")
        } catch (_: Exception) {}

        if (client == null) {
            client = OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .pingInterval(20, TimeUnit.SECONDS)
                .retryOnConnectionFailure(true)
                .build()
        }

        val hubBase = getHubUrl()
        val wsUrl = hubBase.replace("http://", "ws://").replace("https://", "wss://").trimEnd('/') + "/ws/notifications"
        Log.i(TAG, "Connecting background WebSocket to: $wsUrl")

        val request = Request.Builder().url(wsUrl).build()
        webSocket = client?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                Log.i(TAG, "Background WebSocket connected successfully to $wsUrl")
            }

            override fun onMessage(ws: WebSocket, text: String) {
                Log.i(TAG, "Background WebSocket received message: $text")
                handleIncomingMessage(text)
            }

            override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                ws.close(1000, null)
                scheduleReconnect()
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "Background WebSocket failure: ${t.message}")
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        if (!isRunning) return
        reconnectRunnable?.let { retryHandler.removeCallbacks(it) }
        reconnectRunnable = Runnable {
            if (isRunning) {
                startWebSocket()
            }
        }
        retryHandler.postDelayed(reconnectRunnable!!, 5000)
    }

    private fun handleIncomingMessage(jsonStr: String) {
        try {
            val json = JSONObject(jsonStr)
            if (json.has("event") && json.getString("event") == "qna_updated") {
                return
            }

            val title = json.optString("title", "Antigravity Hub")
            val message = json.optString("message", "New notification received")
            val notifId = json.optString("id", "${System.currentTimeMillis()}")
            val intId = notifId.hashCode()

            val launchIntent = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("notification_id", notifId)
            }
            val pendingIntent = PendingIntent.getActivity(
                this, intId, launchIntent,
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )

            val alertNotif = NotificationCompat.Builder(this, ALERT_CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(message)
                .setStyle(NotificationCompat.BigTextStyle().bigText(message))
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentIntent(pendingIntent)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setDefaults(Notification.DEFAULT_ALL)
                .build()

            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.notify(intId, alertNotif)
            Log.i(TAG, "Posted background system notification: $title")
        } catch (e: Exception) {
            Log.e(TAG, "Error handling incoming notification in background service", e)
        }
    }

    override fun onDestroy() {
        isRunning = false
        reconnectRunnable?.let { retryHandler.removeCallbacks(it) }
        try {
            webSocket?.close(1000, "Service destroyed")
        } catch (_: Exception) {}
        super.onDestroy()
    }
}
