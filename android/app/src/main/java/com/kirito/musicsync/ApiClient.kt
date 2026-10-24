package com.kirito.musicsync
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

object ApiClient {
    private val client = OkHttpClient()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    fun submitShare(serverUrl: String, token: String, rawShare: String, callback: (Boolean, String) -> Unit) {
        val json = JSONObject().apply {
            put("source", "shazam") // Server automatically overrides this if it sees a Spotify link
            put("raw_share", rawShare)
        }.toString()

        val request = Request.Builder()
            .url("$serverUrl/tracks")
            .addHeader("Authorization", "Bearer $token")
            .post(json.toRequestBody(JSON))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(false, e.message ?: "Network error")
            }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val body = it.body?.string() ?: ""
                    if (it.isSuccessful) callback(true, body) else callback(false, "HTTP ${it.code}")
                }
            }
        })
    }
}