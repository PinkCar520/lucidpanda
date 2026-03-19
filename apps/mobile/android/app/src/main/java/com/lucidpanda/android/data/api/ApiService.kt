package com.lucidpanda.android.data.api

import com.lucidpanda.android.data.model.IntelligenceMobileRead
import com.lucidpanda.android.data.model.MarketSnapshot
import retrofit2.http.GET
import retrofit2.http.Query

import com.lucidpanda.android.data.model.*
import retrofit2.http.*

interface ApiService {
    @GET("api/v1/mobile/intelligence")
    suspend fun getIntelligence(
        @Query("limit") limit: Int = 20
    ): List<IntelligenceMobileRead>

    @GET("api/v1/mobile/market/snapshot")
    suspend fun getMarketSnapshot(): MarketSnapshot

    @GET("api/v1/mobile/market/pulse")
    suspend fun getMarketPulse(): MarketPulseResponse

    @GET("api/v1/mobile/intelligence/{id}/ai_summary")
    suspend fun getAiSummary(
        @Path("id") id: Int
    ): Map<String, String>

    // Watchlist V2 (Registered under /api/v1/web prefix)
    @GET("api/v1/web/watchlist")
    suspend fun getWatchlist(
        @Query("group_id") groupId: String? = null
    ): WatchlistDataResponse

    @GET("api/v1/web/watchlist/groups")
    suspend fun getWatchlistGroups(): WatchlistGroupResponse

    // Sync is registered at app level with /api/v2 prefix
    @POST("api/v2/watchlist/sync")
    suspend fun syncWatchlist(
        @Body request: WatchlistSyncRequest
    ): Map<String, Any>

    @GET("api/v1/web/watchlist/{code}/ai_analysis")
    suspend fun getFundAiAnalysis(
        @Path("code") fundCode: String
    ): Map<String, Any>

    // Fund Discovery
    @GET("api/v1/web/funds/search")
    suspend fun searchFunds(
        @Query("kw") keyword: String,
        @Query("limit") limit: Int = 20
    ): SearchResponse

    // Authentication (Registered under /api/v1/auth prefix)
    @FormUrlEncoded
    @POST("api/v1/auth/login")
    suspend fun login(
        @Field("username") email: String,
        @Field("password") password: String
    ): TokenResponse

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(
        @Body request: RefreshTokenRequest
    ): TokenResponse

    @GET("api/v1/auth/me")
    suspend fun getCurrentUser(): UserProfile

    // Passkey (WebAuthn)
    @POST("api/v1/auth/passkeys/register/options")
    suspend fun getPasskeyRegisterOptions(): Map<String, Any>

    @POST("api/v1/auth/passkeys/register/verify")
    suspend fun verifyPasskeyRegister(@Body response: Map<String, Any>): Map<String, Any>

    @POST("api/v1/auth/passkeys/login/options")
    suspend fun getPasskeyLoginOptions(): Map<String, Any>

    @POST("api/v1/auth/passkeys/login/verify")
    suspend fun verifyPasskeyLogin(@Body response: Map<String, Any>): TokenResponse
}
