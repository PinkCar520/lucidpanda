package com.lucidpanda.android.data.model

import com.google.gson.annotations.SerializedName

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer"
)

data class LoginRequest(
    val email: String,
    val password: String,
    @SerializedName("device_id") val deviceId: String = "Android"
)

data class UserProfile(
    val id: String,
    val email: String,
    val username: String?,
    @SerializedName("is_pro") val isPro: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class RefreshTokenRequest(
    @SerializedName("refresh_token") val refreshToken: String
)
