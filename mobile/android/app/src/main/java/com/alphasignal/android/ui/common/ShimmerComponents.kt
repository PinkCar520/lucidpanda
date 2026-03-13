package com.alphasignal.android.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.valentinilk.shimmer.shimmer

@Composable
fun ShimmerLoadingList(itemCount: Int = 5) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .shimmer()
    ) {
        repeat(itemCount) {
            ShimmerItem()
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}

@Composable
fun ShimmerItem() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(100.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(Color.LightGray.copy(alpha = 0.3f))
    )
}

@Composable
fun ShimmerLoadingGrid(itemCount: Int = 4) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .shimmer(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        repeat(itemCount) {
            Box(
                modifier = Modifier
                    .width(150.dp)
                    .height(80.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.LightGray.copy(alpha = 0.3f))
            )
        }
    }
}
