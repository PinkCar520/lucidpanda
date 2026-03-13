package com.alphasignal.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "watchlist_items")
data class WatchlistEntity(
    @PrimaryKey val id: String,
    val fundCode: String,
    val fundName: String,
    val groupId: String?,
    val sortIndex: Int,
    val createdAt: String,
    val updatedAt: String,
    val isDeleted: Boolean = false
)

@Entity(tableName = "watchlist_groups")
data class WatchlistGroupEntity(
    @PrimaryKey val id: String,
    val name: String,
    val icon: String,
    val color: String,
    val sortIndex: Int,
    val createdAt: String,
    val updatedAt: String
)
