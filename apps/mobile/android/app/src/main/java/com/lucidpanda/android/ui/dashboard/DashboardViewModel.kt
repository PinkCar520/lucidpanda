package com.lucidpanda.android.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lucidpanda.android.data.model.MarketPulseResponse
import com.lucidpanda.android.data.repository.DashboardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class DashboardUiState {
    object Loading : DashboardUiState()
    data class Success(val data: MarketPulseResponse) : DashboardUiState()
    data class Error(val message: String) : DashboardUiState()
}

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repository: DashboardRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<DashboardUiState>(DashboardUiState.Loading)
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        fetchPulse()
    }

    fun fetchPulse() {
        viewModelScope.launch {
            _uiState.value = DashboardUiState.Loading
            repository.getMarketPulse().fold(
                onSuccess = { _uiState.value = DashboardUiState.Success(it) },
                onFailure = { _uiState.value = DashboardUiState.Error(it.message ?: "Failed to load dashboard") }
            )
        }
    }
}
