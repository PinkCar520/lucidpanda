package com.alphasignal.android.ui.feed

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.alphasignal.android.data.model.IntelligenceMobileRead
import com.alphasignal.android.data.repository.IntelligenceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

import com.alphasignal.android.data.model.MarketSnapshot
import com.alphasignal.android.data.repository.MarketRepository
import kotlinx.coroutines.async

sealed class FeedUiState {
    object Loading : FeedUiState()
    data class Success(
        val items: List<IntelligenceMobileRead>,
        val marketSnapshot: MarketSnapshot? = null
    ) : FeedUiState()
    data class Error(val message: String) : FeedUiState()
}

import com.alphasignal.android.data.repository.SseRepository
import kotlinx.coroutines.flow.collectLatest

@HiltViewModel
class IntelligenceViewModel @Inject constructor(
    private val repository: IntelligenceRepository,
    private val marketRepository: MarketRepository,
    private val sseRepository: SseRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<FeedUiState>(FeedUiState.Loading)
    val uiState: StateFlow<FeedUiState> = _uiState.asStateFlow()

    init {
        refreshAll()
        observeSseUpdates()
    }

    private fun observeSseUpdates() {
        viewModelScope.launch {
            sseRepository.listenToIntelligenceUpdates().collectLatest {
                // When a new intelligence update event is received, refresh the list
                // In a more advanced implementation, we could parse the data and surgically insert the item
                refreshAll(isBackground = true)
            }
        }
    }

    fun refreshAll(isBackground: Boolean = false) {
        viewModelScope.launch {
            if (!isBackground) {
                _uiState.value = FeedUiState.Loading
            }
            
            val intelligenceDeferred = async { repository.getIntelligence(30) }
            val marketDeferred = async { marketRepository.getMarketSnapshot() }

            val intelResult = intelligenceDeferred.await()
            val marketResult = marketDeferred.await()

            intelResult.fold(
                onSuccess = { items ->
                    _uiState.value = FeedUiState.Success(
                        items = items,
                        marketSnapshot = marketResult.getOrNull()
                    )
                },
                onFailure = { error ->
                    if (!isBackground) {
                        _uiState.value = FeedUiState.Error(error.message ?: "Unknown Error")
                    }
                }
            )
        }
    }

    suspend fun getAiSummary(id: Int): Result<String> {
        return repository.getAiSummary(id)
    }
}
