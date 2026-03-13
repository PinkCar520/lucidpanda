package com.alphasignal.android.ui.watchlist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.alphasignal.android.data.model.WatchlistGroup
import com.alphasignal.android.data.model.WatchlistItem
import com.alphasignal.android.data.repository.WatchlistRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class WatchlistUiState {
    object Loading : WatchlistUiState()
    data class Success(
        val items: List<WatchlistItem>,
        val groups: List<WatchlistGroup>,
        val syncTime: String
    ) : WatchlistUiState()
    data class Error(val message: String) : WatchlistUiState()
}

@HiltViewModel
class WatchlistViewModel @Inject constructor(
    private val repository: WatchlistRepository
) : ViewModel() {

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    val uiState: StateFlow<WatchlistUiState> = combine(
        repository.watchlistItems,
        repository.watchlistGroups,
        _isRefreshing,
        _error
    ) { items, groups, refreshing, error ->
        if (error != null && items.isEmpty()) {
            WatchlistUiState.Error(error)
        } else if (items.isEmpty() && refreshing) {
            WatchlistUiState.Loading
        } else {
            WatchlistUiState.Success(
                items = items,
                groups = groups,
                syncTime = ""
            )
        }
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = WatchlistUiState.Loading
    )

    init {
        refreshWatchlist()
    }

    fun refreshWatchlist(groupId: String? = null) {
        viewModelScope.launch {
            _isRefreshing.value = true
            _error.value = null
            repository.refreshWatchlist(groupId).onFailure { error ->
                _error.value = error.message ?: "Sync Failed"
            }
            _isRefreshing.value = false
        }
    }

    suspend fun getFundAiAnalysis(fundCode: String): Result<Map<String, Any>> {
        return repository.getFundAiAnalysis(fundCode)
    }
}
