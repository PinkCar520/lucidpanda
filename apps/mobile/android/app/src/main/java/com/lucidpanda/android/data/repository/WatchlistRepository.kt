package com.lucidpanda.android.data.repository

import com.lucidpanda.android.data.api.ApiService
import com.lucidpanda.android.data.local.dao.WatchlistDao
import com.lucidpanda.android.data.local.entity.WatchlistEntity
import com.lucidpanda.android.data.local.entity.WatchlistGroupEntity
import com.lucidpanda.android.data.model.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WatchlistRepository @Inject constructor(
    private val apiService: ApiService,
    private val watchlistDao: WatchlistDao
) {
    val watchlistItems: Flow<List<WatchlistItem>> = watchlistDao.getAllItemsFlow().map { entities ->
        entities.map { it.toDomainModel() }
    }

    val watchlistGroups: Flow<List<WatchlistGroup>> = watchlistDao.getAllGroupsFlow().map { entities ->
        entities.map { it.toDomainModel() }
    }

    suspend fun refreshWatchlist(groupId: String? = null): Result<Unit> {
        return try {
            val response = apiService.getWatchlist(groupId)
            
            val itemEntities = response.data.map { it.toEntity() }
            val groupEntities = response.groups.map { it.toEntity() }
            
            watchlistDao.syncWatchlist(itemEntities, groupEntities)
            
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getWatchlistGroups(): Result<List<WatchlistGroup>> {
        return try {
            val response = apiService.getWatchlistGroups()
            Result.success(response.data)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun syncWatchlist(operations: List<SyncOperation>, lastSyncTime: String?): Result<Map<String, Any>> {
        return try {
            val response = apiService.syncWatchlist(WatchlistSyncRequest(operations, lastSyncTime))
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getFundAiAnalysis(fundCode: String): Result<Map<String, Any>> {
        return try {
            val response = apiService.getFundAiAnalysis(fundCode)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // Mappers
    private fun WatchlistEntity.toDomainModel() = WatchlistItem(
        id = id, fundCode = fundCode, fundName = fundName,
        groupId = groupId, sortIndex = sortIndex,
        createdAt = createdAt, updatedAt = updatedAt, isDeleted = isDeleted
    )

    private fun WatchlistGroupEntity.toDomainModel() = WatchlistGroup(
        id = id, name = name, icon = icon, color = color,
        sortIndex = sortIndex, createdAt = createdAt, updatedAt = updatedAt
    )

    private fun WatchlistItem.toEntity() = WatchlistEntity(
        id = id, fundCode = fundCode, fundName = fundName,
        groupId = groupId, sortIndex = sortIndex,
        createdAt = createdAt, updatedAt = updatedAt, isDeleted = isDeleted
    )

    private fun WatchlistGroup.toEntity() = WatchlistGroupEntity(
        id = id, name = name, icon = icon, color = color,
        sortIndex = sortIndex, createdAt = createdAt, updatedAt = updatedAt
    )
}
