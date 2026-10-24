package com.kirito.musicsync
import android.content.Context

class Prefs(context: Context) {
    private val prefs = context.getSharedPreferences("music_sync", Context.MODE_PRIVATE)

    var serverUrl: String?
        get() = prefs.getString("server_url", null)
        set(value) = prefs.edit().putString("server_url", value).apply()

    var token: String?
        get() = prefs.getString("token", null)
        set(value) = prefs.edit().putString("token", value).apply()

    fun isConfigured(): Boolean = !serverUrl.isNullOrBlank() && !token.isNullOrBlank()
}