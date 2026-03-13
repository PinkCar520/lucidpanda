package com.alphasignal.android.data.repository

import com.alphasignal.android.data.api.ApiService
import com.alphasignal.android.data.model.MarketPulseResponse
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
