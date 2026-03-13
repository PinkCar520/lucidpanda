package com.alphasignal.android.data.api

import com.alphasignal.android.data.model.IntelligenceMobileRead
import com.alphasignal.android.data.model.MarketSnapshot
import retrofit2.http.GET
import retrofit2.http.Query

import com.alphasignal.android.data.model.*
import retrofit2.http.*

interface ApiService {
    @GET("mobile/intelligence")
    suspend fun getIntelligence(
        @Query("limit") limit: Int = 20
    ): List<IntelligenceMobileRead>

    @GET("mobile/market/snapshot")
    suspend fun getMarketSnapshot(): MarketSnapshot

    @GET("mobile/market/pulse")
    suspend fun getMarketPulse(): MarketPulseResponse

    @GET("mobile/intelligence/{id}/ai_summary")
    suspend fun getAiSummary(
        @Path("id") id: Int
    ): Map<String, String>

    // Watchlist V2
    @GET("watchlist")
    suspend fun getWatchlist(
        @Query("group_id") groupId: String? = null
    ): WatchlistDataResponse

    @GET("watchlist/groups")
    suspend fun getWatchlistGroups(): WatchlistGroupResponse

    @POST("watchlist/sync")
    suspend fun syncWatchlist(
        @Body request: WatchlistSyncRequest
    ): Map<String, Any>

    @GET("watchlist/{code}/ai_analysis")
    suspend fun getFundAiAnalysis(
        @Path("code") fundCode: String
    ): Map<String, Any>

    // Fund Discovery
    @GET("funds/search")
    suspend fun searchFunds(
        @Query("kw") keyword: String,
        @Query("limit") limit: Int = 20
    ): SearchResponse

    // Authentication
    @POST("auth/login")
    suspend fun login(
        @Body request: LoginRequest
    ): TokenResponse

    @POST("auth/refresh")
    suspend fun refreshToken(
        @Header("Authorization") refreshToken: String
    ): TokenResponse

    @GET("auth/me")
    suspend fun getCurrentUser(): UserProfile

    // Passkey (WebAuthn)
    @GET("auth/passkey/register/options")
    suspend fun getPasskeyRegisterOptions(): Map<String, Any>

    @POST("auth/passkey/register/verify")
    suspend fun verifyPasskeyRegister(@Body response: Map<String, Any>): Map<String, Any>

    @GET("auth/passkey/login/options")
    suspend fun getPasskeyLoginOptions(): Map<String, Any>

    @POST("auth/passkey/login/verify")
    suspend fun verifyPasskeyLogin(@Body response: Map<String, Any>): TokenResponse
}
