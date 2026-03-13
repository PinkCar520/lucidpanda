package com.alphasignal.android.data.model

import com.google.gson.annotations.SerializedName

data class WatchlistGroup(
    val id: String,
    val name: String,
    val icon: String,
    val color: String,
    @SerializedName("sort_index") val sortIndex: Int,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String
)

data class WatchlistItem(
    val id: String,
    @SerializedName("fund_code") val fundCode: String,
    @SerializedName("fund_name") val fundName: String,
    @SerializedName("group_id") val groupId: String?,
    @SerializedName("sort_index") val sortIndex: Int,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
    @SerializedName("is_deleted") val isDeleted: Boolean
)

data class WatchlistDataResponse(
    val data: List<WatchlistItem>,
    val groups: List<WatchlistGroup>,
    @SerializedName("sync_time") val syncTime: String
)

data class WatchlistGroupResponse(
    val data: List<WatchlistGroup>
)

data class WatchlistSyncRequest(
    val operations: List<SyncOperation>,
    @SerializedName("last_sync_time") val lastSyncTime: String?
)

data class SyncOperation(
    @SerializedName("operation_type") val operationType: String, // ADD, REMOVE, REORDER, MOVE_GROUP
    @SerializedName("fund_code") val fundCode: String,
    @SerializedName("fund_name") val fundName: String? = null,
    @SerializedName("group_id") val groupId: String? = null,
    @SerializedName("sort_index") val sortIndex: Int? = null,
    @SerializedName("client_timestamp") val clientTimestamp: String,
    @SerializedName("device_id") val deviceId: String = "Android"
)
