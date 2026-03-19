package com.lucidpanda.android.data.local.dao

import androidx.room.*
import com.lucidpanda.android.data.local.entity.WatchlistEntity
import com.lucidpanda.android.data.local.entity.WatchlistGroupEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface WatchlistDao {
    @Query("SELECT * FROM watchlist_items WHERE isDeleted = 0 ORDER BY sortIndex ASC")
    fun getAllItemsFlow(): Flow<List<WatchlistEntity>>

    @Query("SELECT * FROM watchlist_groups ORDER BY sortIndex ASC")
    fun getAllGroupsFlow(): Flow<List<WatchlistGroupEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertItems(items: List<WatchlistEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertGroups(groups: List<WatchlistGroupEntity>)

    @Query("DELETE FROM watchlist_items WHERE id = :id")
    suspend fun deleteItem(id: String)

    @Query("UPDATE watchlist_items SET isDeleted = 1 WHERE id = :id")
    suspend fun softDeleteItem(id: String)

    @Transaction
    suspend fun syncWatchlist(items: List<WatchlistEntity>, groups: List<WatchlistGroupEntity>) {
        // Simple implementation: replace all for now
        // In full sync, we'd handle deletions and updates specifically
        insertGroups(groups)
        insertItems(items)
    }
}
