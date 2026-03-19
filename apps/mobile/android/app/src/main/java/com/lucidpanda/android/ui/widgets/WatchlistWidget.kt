package com.lucidpanda.android.ui.widgets

import android.content.Context
import androidx.compose.ui.unit.dp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.*
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.lucidpanda.android.ui.theme.BluePrimary
import com.lucidpanda.android.ui.theme.White

class WatchlistWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        // In a real app, we'd fetch from Room here
        provideContent {
            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(BluePrimary)
                    .padding(12.dp)
            ) {
                Text(
                    text = "LucidPanda Watchlist",
                    style = TextStyle(
                        color = ColorProvider(White),
                        fontWeight = FontWeight.Bold
                    )
                )
                Spacer(modifier = GlanceModifier.height(8.dp))
                
                // Placeholder rows
                WidgetRow("华夏有色金属", "+1.24%")
                WidgetRow("南方原油", "-0.45%")
            }
        }
    }

    @androidx.compose.runtime.Composable
    private fun WidgetRow(name: String, change: String) {
        Row(
            modifier = GlanceModifier
                .fillMaxWidth()
                .padding(vertical = 4.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = name,
                modifier = GlanceModifier.defaultWeight(),
                style = TextStyle(color = ColorProvider(White))
            )
            Text(
                text = change,
                style = TextStyle(
                    color = ColorProvider(White),
                    fontWeight = FontWeight.Bold
                )
            )
        }
    }
}
