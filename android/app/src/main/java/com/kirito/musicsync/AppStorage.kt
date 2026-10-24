package com.kirito.musicsync

import android.content.Context
import org.json.JSONArray

object AppStorage {
    private const val PREFS_NAME = "music_sync_data"
    private const val KEY_QUEUE = "pending_queue"
    private const val KEY_HISTORY = "history"

    // --- QUEUE METHODS ---
    fun getQueue(context: Context): MutableList<String> {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val jsonStr = prefs.getString(KEY_QUEUE, "[]")
        val list = mutableListOf<String>()
        val arr = JSONArray(jsonStr)
        for (i in 0 until arr.length()) list.add(arr.getString(i))
        return list
    }

    fun saveQueue(context: Context, queue: List<String>) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_QUEUE, JSONArray(queue).toString()).apply()
    }

    fun addToQueue(context: Context, text: String) {
        val queue = getQueue(context)
        if (!queue.contains(text)) {
            queue.add(text)
            saveQueue(context, queue)
        }
    }

    fun removeFromQueue(context: Context, text: String) {
        val queue = getQueue(context)
        queue.remove(text)
        saveQueue(context, queue)
    }

    // --- HISTORY METHODS ---
    fun getHistory(context: Context): MutableList<String> {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val jsonStr = prefs.getString(KEY_HISTORY, "[]")
        val list = mutableListOf<String>()
        val arr = JSONArray(jsonStr)
        for (i in 0 until arr.length()) list.add(arr.getString(i))
        return list
    }

    fun addToHistory(context: Context, text: String) {
        val history = getHistory(context)
        history.add(0, text) // Add to the top
        if (history.size > 50) history.removeAt(history.size - 1) // Keep last 50

        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_HISTORY, JSONArray(history).toString()).apply()
    }
}