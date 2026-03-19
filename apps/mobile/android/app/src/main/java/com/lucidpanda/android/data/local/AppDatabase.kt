package com.lucidpanda.android.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.lucidpanda.android.data.local.dao.WatchlistDao
import com.lucidpanda.android.data.local.entity.WatchlistEntity
import com.lucidpanda.android.data.local.entity.WatchlistGroupEntity

@Database(
    entities = [WatchlistEntity::class, WatchlistGroupEntity::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun watchlistDao(): WatchlistDao
}
