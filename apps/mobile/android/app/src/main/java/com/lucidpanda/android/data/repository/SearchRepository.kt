package com.lucidpanda.android.data.repository

import com.lucidpanda.android.data.api.ApiService
import com.lucidpanda.android.data.model.FundSearchResult
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SearchRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun searchFunds(keyword: String): Result<List<FundSearchResult>> {
        return try {
            val response = apiService.searchFunds(keyword)
            Result.success(response.data)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
