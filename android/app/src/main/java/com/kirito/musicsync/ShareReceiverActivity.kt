package com.kirito.musicsync
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class ShareReceiverActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = Prefs(this)
        if (!prefs.isConfigured()) {
            Toast.makeText(this, "Please configure the app first", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, SettingsActivity::class.java))
            finish()
            return
        }

        val sharedText = intent?.getStringExtra(Intent.EXTRA_TEXT)
        if (sharedText.isNullOrBlank()) {
            Toast.makeText(this, "No text received", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        ApiClient.submitShare(prefs.serverUrl!!, prefs.token!!, sharedText) { success, message ->
            runOnUiThread {
                if (success) {
                    AppStorage.addToHistory(this, sharedText)
                    Toast.makeText(this, "Sent to server!", Toast.LENGTH_SHORT).show()
                } else {
                    AppStorage.addToQueue(this, sharedText)
                    Toast.makeText(this, "Server offline. Saved to queue!", Toast.LENGTH_SHORT).show()
                }
                finish()
            }
        }
    }
}