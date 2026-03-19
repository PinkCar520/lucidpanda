package com.lucidpanda.android.data.repository

import com.lucidpanda.android.data.api.ApiService
import com.lucidpanda.android.data.model.MarketPulseResponse
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DashboardRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getMarketPulse(): Result<MarketPulseResponse> {
        return try {
            val response = apiService.getMarketPulse()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
