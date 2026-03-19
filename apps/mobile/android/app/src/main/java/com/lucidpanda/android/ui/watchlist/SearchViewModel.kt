package com.lucidpanda.android.ui.watchlist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lucidpanda.android.data.model.FundSearchResult
import com.lucidpanda.android.data.model.SyncOperation
import com.lucidpanda.android.data.repository.SearchRepository
import com.lucidpanda.android.data.repository.WatchlistRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject

sealed class SearchUiState {
    object Idle : SearchUiState()
    object Loading : SearchUiState()
    data class Success(val results: List<FundSearchResult>) : SearchUiState()
    data class Error(val message: String) : SearchUiState()
}

@OptIn(FlowPreview::class)
@HiltViewModel
class SearchViewModel @Inject constructor(
    private val searchRepository: SearchRepository,
    private val watchlistRepository: WatchlistRepository
) : ViewModel() {

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _uiState = MutableStateFlow<SearchUiState>(SearchUiState.Idle)
    val uiState: StateFlow<SearchUiState> = _uiState.asStateFlow()

    init {
        _searchQuery
            .debounce(500)
            .filter { it.length >= 2 }
            .onEach { query ->
                performSearch(query)
            }
            .launchIn(viewModelScope)
    }

    fun onQueryChange(query: String) {
        _searchQuery.value = query
        if (query.length < 2) {
            _uiState.value = SearchUiState.Idle
        }
    }

    private fun performSearch(query: String) {
        viewModelScope.launch {
            _uiState.value = SearchUiState.Loading
            searchRepository.searchFunds(query).fold(
                onSuccess = { _uiState.value = SearchUiState.Success(it) },
                onFailure = { _uiState.value = SearchUiState.Error(it.message ?: "Search failed") }
            )
        }
    }

    fun addToWatchlist(fund: FundSearchResult) {
        viewModelScope.launch {
            val timestamp = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(Date())
            val operation = SyncOperation(
                operationType = "ADD",
                fundCode = fund.fundCode,
                fundName = fund.fundName,
                clientTimestamp = timestamp
            )
            // We'll call sync directly for now. In production, we'd add to local queue.
            watchlistRepository.syncWatchlist(listOf(operation), null)
            // Refresh local data
            watchlistRepository.refreshWatchlist()
        }
    }
}
