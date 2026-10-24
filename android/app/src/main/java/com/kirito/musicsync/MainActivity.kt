package com.kirito.musicsync

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onResume() {
        super.onResume()
        updateQueueStatus()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        findViewById<Button>(R.id.btnViewQueue).setOnClickListener {
            startActivity(Intent(this, QueueActivity::class.java))
        }

        findViewById<Button>(R.id.btnViewHistory).setOnClickListener {
            startActivity(Intent(this, HistoryActivity::class.java))
        }

        findViewById<Button>(R.id.btnSettings).setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        findViewById<Button>(R.id.btnSyncNow).setOnClickListener {
            flushQueue()
        }
    }

    private fun updateQueueStatus() {
        val queueSize = AppStorage.getQueue(this).size
        findViewById<TextView>(R.id.tvQueueStatus).text = "Queue: $queueSize pending"
    }

    private fun flushQueue() {
        val prefs = Prefs(this)
        if (!prefs.isConfigured()) {
            Toast.makeText(this, "Configure server in Settings first", Toast.LENGTH_SHORT).show()
            return
        }

        val queue = AppStorage.getQueue(this)
        if (queue.isEmpty()) {
            Toast.makeText(this, "Queue is empty", Toast.LENGTH_SHORT).show()
            return
        }

        Toast.makeText(this, "Syncing ${queue.size} items...", Toast.LENGTH_SHORT).show()

        for (item in queue) {
            ApiClient.submitShare(prefs.serverUrl!!, prefs.token!!, item) { success, _ ->
                if (success) {
                    runOnUiThread {
                        AppStorage.removeFromQueue(this, item)
                        AppStorage.addToHistory(this, item)
                        updateQueueStatus()
                    }
                }
            }
        }
    }
}