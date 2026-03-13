package com.alphasignal.android.ui.feed

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.alphasignal.android.data.model.IntelligenceMobileRead
import com.alphasignal.android.data.model.MarketItem
import com.alphasignal.android.data.model.MarketSnapshot
import com.alphasignal.android.ui.common.ShimmerLoadingGrid
import com.alphasignal.android.ui.common.ShimmerLoadingList
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IntelligenceFeedScreen(viewModel: IntelligenceViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val sheetState = rememberModalBottomSheetState()
    var showBottomSheet by remember { mutableStateOf(false) }
    var selectedItem by remember { mutableStateOf<IntelligenceMobileRead?>(null) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("AlphaSignal Intelligence", fontWeight = FontWeight.Bold) }
            )
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding).fillMaxSize()) {
            when (val state = uiState) {
                is FeedUiState.Loading -> {
                    Column {
                        ShimmerLoadingGrid()
                        ShimmerLoadingList()
                    }
                }
                is FeedUiState.Success -> {
                    IntelligenceList(
                        items = state.items,
                        marketSnapshot = state.marketSnapshot,
                        onItemClick = { item ->
                            selectedItem = item
                            showBottomSheet = true
                        }
                    )
                }
                is FeedUiState.Error -> {
                    Text(
                        text = state.message,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
            }
        }

        if (showBottomSheet && selectedItem != null) {
            ModalBottomSheet(
                onDismissRequest = { showBottomSheet = false },
                sheetState = sheetState
            ) {
                IntelligenceDetailContent(selectedItem!!, viewModel)
            }
        }
    }
}

@Composable
fun IntelligenceList(
    items: List<IntelligenceMobileRead>,
    marketSnapshot: MarketSnapshot?,
    onItemClick: (IntelligenceMobileRead) -> Unit
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (marketSnapshot != null) {
            item {
                MarketSnapshotRow(marketSnapshot)
            }
        }
        
        items(items) { item ->
            Box(modifier = Modifier
                .padding(horizontal = 16.dp)
                .clickable { onItemClick(item) }
            ) {
                IntelligenceItem(item)
            }
        }
    }
}

@Composable
fun IntelligenceDetailContent(item: IntelligenceMobileRead, viewModel: IntelligenceViewModel) {
    var aiSummary by remember { mutableStateOf<String?>(null) }
    
    LaunchedEffect(item.id) {
        viewModel.getAiSummary(item.id).onSuccess {
            aiSummary = it
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp)
            .padding(bottom = 40.dp)
            .verticalScroll(rememberScrollState())
    ) {
        Text(
            text = item.author,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = item.summary,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(16.dp))
        
        Surface(
            color = MaterialTheme.colorScheme.surfaceVariant,
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "AI ANALYSIS",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.secondary,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))
                if (aiSummary == null) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                } else {
                    Text(
                        text = aiSummary!!,
                        style = MaterialTheme.typography.bodyMedium,
                        lineHeight = 22.sp
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = "ORIGINAL CONTENT",
            style = MaterialTheme.typography.labelSmall,
            color = Color.Gray,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = item.content,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            lineHeight = 18.sp
        )
    }
}

@Composable
fun MarketSnapshotRow(snapshot: MarketSnapshot) {
    LazyRow(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        snapshot.gold?.let { item { MarketCard("GOLD", it) } }
        snapshot.oil?.let { item { MarketCard("CRUDE OIL", it) } }
        snapshot.dxy?.let { item { MarketCard("DXY", it) } }
        snapshot.us10y?.let { item { MarketCard("US10Y", it) } }
    }
}

@Composable
fun MarketCard(label: String, item: MarketItem) {
    Card(
        modifier = Modifier.width(150.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = Color.Gray)
            Text(
                text = String.format("%.2f", item.price),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            val color = if (item.change >= 0) Color(0xFF34C759) else Color(0xFFFF3B30)
            Text(
                text = String.format("%+.2f (%.2f%%)", item.change, item.changePercent),
                style = MaterialTheme.typography.labelSmall,
                color = color,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
fun IntelligenceItem(item: IntelligenceMobileRead) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = item.author,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary
                )
                UrgencyBadge(item.urgencyScore)
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = item.summary,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = item.timestamp,
                style = MaterialTheme.typography.labelSmall,
                color = Color.Gray
            )
        }
    }
}

@Composable
fun UrgencyBadge(score: Int) {
    val color = when {
        score >= 8 -> Color(0xFFFF3B30) // Red
        score >= 5 -> Color(0xFFFFCC00) // Yellow
        else -> Color(0xFF34C759)      // Green
    }
    Surface(
        color = color.copy(alpha = 0.1f),
        shape = RoundedCornerShape(4.dp)
    ) {
        Text(
            text = "Urgency $score",
            color = color,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold
        )
    }
}
