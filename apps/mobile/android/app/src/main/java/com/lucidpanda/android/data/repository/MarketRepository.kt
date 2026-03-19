package com.lucidpanda.android.data.repository

import com.lucidpanda.android.data.api.ApiService
import com.lucidpanda.android.data.model.MarketSnapshot
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MarketRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getMarketSnapshot(): Result<MarketSnapshot> {
        return try {
            val response = apiService.getMarketSnapshot()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
