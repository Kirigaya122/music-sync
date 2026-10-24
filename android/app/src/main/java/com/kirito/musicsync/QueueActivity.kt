package com.kirito.musicsync

import android.app.AlertDialog
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.ListView
import androidx.appcompat.app.AppCompatActivity

class QueueActivity : AppCompatActivity() {
    private lateinit var adapter: ArrayAdapter<String>
    private val queueItems = mutableListOf<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_queue)

        queueItems.addAll(AppStorage.getQueue(this))
        adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, queueItems)

        val listView = findViewById<ListView>(R.id.listQueue)
        listView.adapter = adapter

        // Tap to Edit or Delete
        listView.setOnItemClickListener { _, _, position, _ ->
            val item = queueItems[position]
            val options = arrayOf("Edit", "Delete")

            AlertDialog.Builder(this)
                .setTitle(item.take(40) + "...")
                .setItems(options) { _, which ->
                    if (which == 0) editItem(item, position)
                    else deleteItem(item, position)
                }.show()
        }
    }

    private fun editItem(oldItem: String, position: Int) {
        val input = EditText(this)
        input.setText(oldItem)

        AlertDialog.Builder(this)
            .setTitle("Edit Share Text")
            .setView(input)
            .setPositiveButton("Save") { _, _ ->
                val newText = input.text.toString().trim()
                if (newText.isNotEmpty()) {
                    AppStorage.removeFromQueue(this, oldItem)
                    AppStorage.addToQueue(this, newText)
                    queueItems[position] = newText
                    adapter.notifyDataSetChanged()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun deleteItem(item: String, position: Int) {
        AppStorage.removeFromQueue(this, item)
        queueItems.removeAt(position)
        adapter.notifyDataSetChanged()
    }
}