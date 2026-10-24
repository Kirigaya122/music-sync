package com.kirito.musicsync
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val prefs = Prefs(this)
        val urlField = findViewById<EditText>(R.id.urlField)
        val tokenField = findViewById<EditText>(R.id.tokenField)

        urlField.setText(prefs.serverUrl ?: "http://192.168.1.185:8000")
        tokenField.setText(prefs.token ?: "")

        findViewById<Button>(R.id.saveButton).setOnClickListener {
            val url = urlField.text.toString().trim().trimEnd('/')
            val token = tokenField.text.toString().trim()

            if (url.isBlank() || token.isBlank()) {
                Toast.makeText(this, "Both fields required", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            prefs.serverUrl = url
            prefs.token = token
            Toast.makeText(this, "Saved!", Toast.LENGTH_SHORT).show()
            finish()
        }
           flushQueue(prefs)
    }

    private fun flushQueue(prefs: Prefs) {
        if (!prefs.isConfigured()) return

        val pending = OfflineQueue.getAll(this)
        if (pending.isEmpty()) return

        Toast.makeText(this, "Sending ${pending.size} queued songs...", Toast.LENGTH_SHORT).show()

        var successCount = 0
        for (shareText in pending) {
            ApiClient.submitShare(prefs.serverUrl!!, prefs.token!!, shareText) { success, _ ->
                if (success) {
                    runOnUiThread {
                        successCount++
                        // If all sent, clear the queue
                        if (successCount == pending.size) {
                            OfflineQueue.clear(this)
                            Toast.makeText(this, "Queue flushed successfully!", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
        }
    }
}