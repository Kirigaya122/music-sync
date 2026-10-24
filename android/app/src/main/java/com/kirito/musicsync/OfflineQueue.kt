package com.kirito.musicsync

import android.content.Context
import org.json.JSONArray

object OfflineQueue {
    private const val PREFS_NAME = "music_sync_queue"
    private const val KEY_QUEUE = "pending_shares"

    fun add(context: Context, rawShare: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val queueString = prefs.getString(KEY_QUEUE, "[]")
        val jsonArray = JSONArray(queueString)

        // Don't add it if it's already in the queue
        if (!jsonArray.toString().contains(rawShare)) {
            jsonArray.put(rawShare)
            prefs.edit().putString(KEY_QUEUE, jsonArray.toString()).apply()
        }
    }

    fun getAll(context: Context): List<String> {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val queueString = prefs.getString(KEY_QUEUE, "[]")
        val jsonArray = JSONArray(queueString)
        val list = mutableListOf<String>()
        for (i in 0 until jsonArray.length()) {
            list.add(jsonArray.getString(i))
        }
        return list
    }

    fun clear(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().remove(KEY_QUEUE).apply()
    }
}