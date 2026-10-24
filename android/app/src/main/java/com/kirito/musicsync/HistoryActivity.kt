package com.kirito.musicsync

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.ListView
import androidx.appcompat.app.AppCompatActivity

class HistoryActivity : AppCompatActivity() {
override fun onCreate(savedInstanceState: Bundle?) {
super.onCreate(savedInstanceState)
setContentView(R.layout.activity_history)

val historyItems = AppStorage.getHistory(this)
val adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, historyItems)

findViewById<ListView>(R.id.listHistory).adapter = adapter
}
}