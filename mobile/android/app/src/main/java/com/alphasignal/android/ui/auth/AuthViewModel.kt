package com.alphasignal.android.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.alphasignal.android.data.model.LoginRequest
import com.alphasignal.android.data.model.UserProfile
import com.alphasignal.android.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class AuthUiState {
    object Idle : AuthUiState()
    object Loading : AuthUiState()
    data class Authenticated(val user: UserProfile) : AuthUiState()
    data class Error(val message: String) : AuthUiState()
}

import android.content.Context

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            repository.login(LoginRequest(email, password)).fold(
                onSuccess = { user ->
                    _uiState.value = AuthUiState.Authenticated(user)
                },
                onFailure = { error ->
                    _uiState.value = AuthUiState.Error(error.message ?: "Login Failed")
                }
            )
        }
    }

    fun loginWithPasskey(context: Context) {
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            repository.loginWithPasskey(context).fold(
                onSuccess = { user ->
                    _uiState.value = AuthUiState.Authenticated(user)
                },
                onFailure = { error ->
                    _uiState.value = AuthUiState.Error(error.message ?: "Passkey Login Failed")
                }
            )
        }
    }

    fun logout() {
...        viewModelScope.launch {
            repository.logout()
            _uiState.value = AuthUiState.Idle
        }
    }
}
