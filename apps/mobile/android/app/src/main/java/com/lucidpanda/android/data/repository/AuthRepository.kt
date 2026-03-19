package com.lucidpanda.android.data.repository

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetPublicKeyCredentialOption
import androidx.credentials.PublicKeyCredential
import com.lucidpanda.android.data.api.ApiService
import com.lucidpanda.android.data.local.AuthManager
import com.lucidpanda.android.data.model.LoginRequest
import com.lucidpanda.android.data.model.UserProfile
import com.google.gson.Gson
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val apiService: ApiService,
    private val authManager: AuthManager,
    @ApplicationContext private val context: Context
) {
    private val credentialManager = CredentialManager.create(context)
    private val gson = Gson()

    suspend fun login(request: LoginRequest): Result<UserProfile> {
        return try {
            val response = apiService.login(request.email, request.password)
            authManager.saveTokens(response.accessToken, response.refreshToken)
            
            val profile = apiService.getCurrentUser()
            Result.success(profile)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun loginWithPasskey(activityContext: Context): Result<UserProfile> {
        return try {
            val optionsMap = apiService.getPasskeyLoginOptions()
            val optionsJson = gson.toJson(optionsMap)

            val getPublicKeyCredentialOption = GetPublicKeyCredentialOption(optionsJson)
            val getCredRequest = GetCredentialRequest(listOf(getPublicKeyCredentialOption))
            
            val result = credentialManager.getCredential(activityContext, getCredRequest)
            val credential = result.credential
            
            if (credential !is PublicKeyCredential) {
                return Result.failure(Exception("Unexpected credential type"))
            }

            val authResponse = gson.fromJson<Map<String, Any>>(
                credential.authenticationResponseJson,
                object : com.google.gson.reflect.TypeToken<Map<String, Any>>() {}.type
            )
            
            val tokenResponse = apiService.verifyPasskeyLogin(authResponse)
            authManager.saveTokens(tokenResponse.accessToken, tokenResponse.refreshToken)
            
            val profile = apiService.getCurrentUser()
            Result.success(profile)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout() {
        authManager.clearTokens()
    }

    fun getAccessToken() = authManager.accessToken
}
