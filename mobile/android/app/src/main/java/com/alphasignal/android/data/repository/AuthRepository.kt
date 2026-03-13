package com.alphasignal.android.data.repository

import com.alphasignal.android.data.api.ApiService
import com.alphasignal.android.data.local.AuthManager
import com.alphasignal.android.data.model.LoginRequest
import com.alphasignal.android.data.model.UserProfile
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetPublicKeyCredentialOption
import androidx.credentials.PublicKeyCredential
import com.google.gson.Gson
import com.google.gson.reflect.TypeType
import dagger.hilt.android.qualifiers.ApplicationContext

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
            val response = apiService.login(request)
            authManager.saveTokens(response.accessToken, response.refreshToken)
            
            // Fetch profile after login
            val profile = apiService.getCurrentUser()
            Result.success(profile)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun loginWithPasskey(activityContext: Context): Result<UserProfile> {
        return try {
            // 1. Get options from server
            val optionsMap = apiService.getPasskeyLoginOptions()
            val optionsJson = gson.toJson(optionsMap)

            // 2. Request credential from Android system
            val getPublicKeyCredentialOption = GetPublicKeyCredentialOption(optionsJson)
            val getCredRequest = GetCredentialRequest(listOf(getPublicKeyCredentialOption))
            
            val result = credentialManager.getCredential(activityContext, getCredRequest)
            val credential = result.credential
            
            if (credential !is PublicKeyCredential) {
                return Result.failure(Exception("Unexpected credential type"))
            }

            // 3. Verify with server
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
...        authManager.clearTokens()
    }

    fun getAccessToken() = authManager.accessToken
}
