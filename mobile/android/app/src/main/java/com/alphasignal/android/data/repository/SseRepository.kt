package com.alphasignal.android.data.repository

import android.util.Log
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SseRepository @Inject constructor(
    private val client: OkHttpClient,
    @javax.inject.Named("baseUrl") private val baseUrl: String
) {
    fun listenToIntelligenceUpdates(): Flow<String> = callbackFlow {
        val request = Request.Builder()
            .url("${baseUrl}mobile/intelligence/stream") // Assume this endpoint exists or will be added
            .build()

        val listener = object : EventSourceListener() {
            override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
                trySend(data)
            }

            override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                Log.e("SseRepository", "SSE Failure: ${t?.message}")
                // In production, implement reconnection logic here
            }

            override fun onOpen(eventSource: EventSource, response: Response) {
                Log.d("SseRepository", "SSE Connection Opened")
            }

            override fun onClosed(eventSource: EventSource) {
                Log.d("SseRepository", "SSE Connection Closed")
            }
        }

        val eventSource = EventSources.createFactory(client).newEventSource(request, listener)

        awaitClose {
            eventSource.cancel()
        }
    }
}
