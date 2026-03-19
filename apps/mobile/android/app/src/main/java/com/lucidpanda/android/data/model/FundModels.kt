package com.lucidpanda.android.data.model

import com.google.gson.annotations.SerializedName

data class FundSearchResult(
    @SerializedName("fund_code") val fundCode: String,
    @SerializedName("fund_name") val fundName: String,
    @SerializedName("pinyin_shorthand") val pinyin: String?,
    @SerializedName("investment_type") val investmentType: String?,
    @SerializedName("risk_level") val riskLevel: String?
)

data class SearchResponse(
    val data: List<FundSearchResult>
)
