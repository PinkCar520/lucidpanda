package com.lucidpanda.android.data.repository

import com.lucidpanda.android.data.api.ApiService
import com.lucidpanda.android.data.model.IntelligenceMobileRead
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class IntelligenceRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getIntelligence(limit: Int): Result<List<IntelligenceMobileRead>> {
        return try {
            val response = apiService.getIntelligence(limit)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getAiSummary(id: Int): Result<String> {
        return try {
            val response = apiService.getAiSummary(id)
            Result.success(response["ai_summary"] ?: "No summary available")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
