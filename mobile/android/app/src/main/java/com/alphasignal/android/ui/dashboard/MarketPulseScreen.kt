package com.alphasignal.android.ui.dashboard

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.alphasignal.android.data.model.MacroEvent
import com.alphasignal.android.data.model.MarketPulseResponse
import com.alphasignal.android.data.model.SentimentPoint

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MarketPulseScreen(viewModel: DashboardViewModel) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Market Pulse", fontWeight = FontWeight.Bold) }
            )
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding).fillMaxSize()) {
            when (val state = uiState) {
                is DashboardUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is DashboardUiState.Success -> {
                    MarketPulseContent(state.data)
                }
                is DashboardUiState.Error -> {
                    Text(
                        text = state.message,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
            }
        }
    }
}

@Composable
fun MarketPulseContent(data: MarketPulseResponse) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        SentimentSection(data)
        Spacer(modifier = Modifier.height(24.dp))
        SentimentTrendChart(data.sentimentTrend)
        Spacer(modifier = Modifier.height(24.dp))
        UpcomingEventsSection(data.upcomingEvents)
    }
}

@Composable
fun SentimentSection(data: MarketPulseResponse) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("Overall Sentiment", style = MaterialTheme.typography.labelMedium, color = Color.Gray)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = data.overallSentimentZh,
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.ExtraBold,
                color = if (data.sentimentScore > 0) Color(0xFF34C759) else Color(0xFFFF3B30)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Score: ${String.format("%.3f", data.sentimentScore)}",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
        }
    }
}

@Composable
fun SentimentTrendChart(points: List<SentimentPoint>) {
    Text("24h Sentiment Trend", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    Spacer(modifier = Modifier.height(12.dp))
    Card(
        modifier = Modifier.fillMaxWidth().height(150.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        if (points.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No data available")
            }
        } else {
            Canvas(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                val width = size.width
                val height = size.height
                val maxPoints = points.size
                val stepX = width / (maxPoints - 1)
                
                val path = Path()
                points.forEachIndexed { index, point ->
                    // Map score (-1 to 1) to height
                    val y = height / 2 - (point.score * (height / 2)).toFloat()
                    val x = index * stepX
                    
                    if (index == 0) path.moveTo(x, y)
                    else path.lineTo(x, y)
                }
                
                drawPath(
                    path = path,
                    color = Color(0xFF007AFF),
                    style = Stroke(width = 3.dp.toPx())
                )
                
                // Draw zero line
                drawLine(
                    color = Color.Gray.copy(alpha = 0.3f),
                    start = Offset(0f, height / 2),
                    end = Offset(width, height / 2),
                    strokeWidth = 1.dp.toPx()
                )
            }
        }
    }
}

@Composable
fun UpcomingEventsSection(events: List<MacroEvent>) {
    Text("Upcoming Macro Events", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    Spacer(modifier = Modifier.height(12.dp))
    events.forEach { event ->
        MacroEventItem(event)
        Spacer(modifier = Modifier.height(8.dp))
    }
}

@Composable
fun MacroEventItem(event: MacroEvent) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(event.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                Text("${event.country} • ${event.time}", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
            }
            ImpactBadge(event.impact)
        }
    }
}

@Composable
fun ImpactBadge(impact: String) {
    val color = when (impact.lowercase()) {
        "high" -> Color(0xFFFF3B30)
        "medium" -> Color(0xFFFFCC00)
        else -> Color(0xFF34C759)
    }
    Surface(
        color = color.copy(alpha = 0.1f),
        shape = CircleShape
    ) {
        Text(
            text = impact.uppercase(),
            color = color,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold
        )
    }
}
