package com.alphasignal.android.di

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Singleton

import android.content.Context
import androidx.room.Room
import com.alphasignal.android.data.local.AppDatabase
import com.alphasignal.android.data.local.dao.WatchlistDao
import com.alphasignal.android.data.local.AuthManager
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(
        authManager: AuthManager,
        @javax.inject.Named("baseUrl") baseUrl: String
    ): OkHttpClient {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            .addInterceptor { chain ->
                val token = runBlocking { authManager.accessToken.first() }
                val request = chain.request().newBuilder()
                if (token != null) {
                    request.addHeader("Authorization", "Bearer $token")
                }
                chain.proceed(request.build())
            }
            .addInterceptor(loggingInterceptor)
            .authenticator { _, response ->
                val refreshToken = runBlocking { authManager.refreshToken.first() }
                if (refreshToken == null) return@authenticator null

                val refreshClient = OkHttpClient.Builder().addInterceptor(loggingInterceptor).build()
                val retrofit = Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .addConverterFactory(GsonConverterFactory.create())
                    .client(refreshClient)
                    .build()
                
                val authApiService = retrofit.create(com.alphasignal.android.data.api.ApiService::class.java)
                
                try {
                    val newTokenResponse = runBlocking { 
                        authApiService.refreshToken("Bearer $refreshToken") 
                    }
                    runBlocking { 
                        authManager.saveTokens(newTokenResponse.accessToken, newTokenResponse.refreshToken) 
                    }
                    
                    response.request.newBuilder()
                        .header("Authorization", "Bearer ${newTokenResponse.accessToken}")
                        .build()
                } catch (e: Exception) {
                    runBlocking { authManager.clearTokens() }
                    null
                }
            }
            .build()
    }

    @Provides
    @Singleton
    @javax.inject.Named("baseUrl")
    fun provideBaseUrl(): String = "https://alphasignal.ai/api/v1/"

    @Provides
    @Singleton
    fun provideRetrofit(@javax.inject.Named("baseUrl") baseUrl: String, okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .client(okHttpClient)
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): com.alphasignal.android.data.api.ApiService {
        return retrofit.create(com.alphasignal.android.data.api.ApiService::class.java)
    }

    @Provides
    @Singleton
    fun provideAppDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "alphasignal_db"
        ).build()
    }

    @Provides
    @Singleton
    fun provideWatchlistDao(database: AppDatabase): WatchlistDao {
        return database.watchlistDao()
    }
}
