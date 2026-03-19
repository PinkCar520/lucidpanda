package com.lucidpanda.android.data.model

import com.google.gson.annotations.SerializedName
import java.util.Date

data class IntelligenceMobileRead(
    val id: Int,
    val timestamp: String,
    val author: String,
    val summary: String,
    val content: String,
    @SerializedName("urgency_score") val urgencyScore: Int,
    @SerializedName("sentiment_label") val sentimentLabel: String,
    @SerializedName("gold_price_snapshot") val goldPriceSnapshot: Double?,
    @SerializedName("dxy_snapshot") val dxySnapshot: Double?,
    @SerializedName("us10y_snapshot") val us10ySnapshot: Double?,
    @SerializedName("oil_snapshot") val oilSnapshot: Double?,
    @SerializedName("corroboration_count") val corroborationCount: Int,
    @SerializedName("confidence_score") val confidenceScore: Double,
    @SerializedName("confidence_level") val confidenceLevel: String
)

data class MarketSnapshot(
    val gold: MarketItem?,
    val dxy: MarketItem?,
    val us10y: MarketItem?,
    val oil: MarketItem?
)

data class MarketItem(
    val price: Double,
    val change: Double,
    val changePercent: Double,
    val lastUpdated: String
)
