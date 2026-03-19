package com.lucidpanda.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import com.lucidpanda.android.ui.auth.AuthUiState
import com.lucidpanda.android.ui.auth.AuthViewModel
import com.lucidpanda.android.ui.auth.LoginScreen
import com.lucidpanda.android.ui.dashboard.DashboardViewModel
import com.lucidpanda.android.ui.dashboard.MarketPulseScreen
import com.lucidpanda.android.ui.feed.IntelligenceFeedScreen
import com.lucidpanda.android.ui.feed.IntelligenceViewModel
import com.lucidpanda.android.ui.theme.LucidPandaTheme
import com.lucidpanda.android.ui.watchlist.SearchScreen
import com.lucidpanda.android.ui.watchlist.SearchViewModel
import com.lucidpanda.android.ui.watchlist.WatchlistScreen
import com.lucidpanda.android.ui.watchlist.WatchlistViewModel
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            LucidPandaTheme {
                val authViewModel: AuthViewModel = hiltViewModel()
                val authState by authViewModel.uiState.collectAsState()

                when (val state = authState) {
                    is AuthUiState.Authenticated -> {
                        MainAppContent()
                    }
                    else -> {
                        LoginScreen(viewModel = authViewModel)
                    }
                }
            }
        }
    }
}

@Composable
fun MainAppContent() {
    var selectedTab by remember { mutableIntStateOf(0) }
    var isSearching by remember { mutableStateOf(false) }
    
    if (isSearching) {
        val searchViewModel: SearchViewModel = hiltViewModel()
        SearchScreen(
            viewModel = searchViewModel,
            onBack = { isSearching = false }
        )
    } else {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            bottomBar = {
                NavigationBar {
                    NavigationBarItem(
                        selected = selectedTab == 0,
                        onClick = { selectedTab = 0 },
                        icon = { Icon(Icons.Default.Notifications, contentDescription = "Feed") },
                        label = { Text("Feed") }
                    )
                    NavigationBarItem(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        icon = { Icon(Icons.Default.List, contentDescription = "Watchlist") },
                        label = { Text("Watchlist") }
                    )
                    NavigationBarItem(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        icon = { Icon(Icons.Default.Info, contentDescription = "Pulse") },
                        label = { Text("Pulse") }
                    )
                }
            }
        ) { innerPadding ->
            Box(modifier = Modifier.padding(innerPadding)) {
                when (selectedTab) {
                    0 -> {
                        val viewModel: IntelligenceViewModel = hiltViewModel()
                        IntelligenceFeedScreen(viewModel = viewModel)
                    }
                    1 -> {
                        val viewModel: WatchlistViewModel = hiltViewModel()
                        WatchlistScreen(
                            viewModel = viewModel,
                            onNavigateToSearch = { isSearching = true }
                        )
                    }
                    2 -> {
                        val viewModel: DashboardViewModel = hiltViewModel()
                        MarketPulseScreen(viewModel = viewModel)
                    }
                }
            }
        }
    }
}
