package com.lucidpanda.android.data.model

import com.google.gson.annotations.SerializedName

data class MarketPulseResponse(
    @SerializedName("market_snapshot") val marketSnapshot: MarketSnapshot,
    @SerializedName("top_alerts") val topAlerts: List<TopAlert>,
    @SerializedName("upcoming_events") val upcomingEvents: List<MacroEvent>,
    @SerializedName("overall_sentiment") val overallSentiment: String,
    @SerializedName("overall_sentiment_zh") val overallSentimentZh: String,
    @SerializedName("sentiment_score") val sentimentScore: Double,
    @SerializedName("sentiment_trend") val sentimentTrend: List<SentimentPoint>,
    @SerializedName("alert_count_24h") val alertCount24h: Int
)

data class TopAlert(
    val id: Int,
    val timestamp: String,
    @SerializedName("urgency_score") val urgencyScore: Int,
    val summary: String,
    val sentiment: String
)

data class MacroEvent(
    val id: String,
    val title: String,
    val country: String,
    val date: String,
    val time: String,
    val impact: String, // high, medium, low
    val forecast: String?,
    val previous: String?
)

data class SentimentPoint(
    val hour: String,
    val score: Double
)
