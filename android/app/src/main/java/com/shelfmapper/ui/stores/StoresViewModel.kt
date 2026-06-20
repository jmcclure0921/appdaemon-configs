package com.shelfmapper.ui.stores

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.shelfmapper.data.ShelfMapperRepository
import com.shelfmapper.data.Store
import com.shelfmapper.ui.repository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class StoresUiState(
    val stores: List<Store> = emptyList(),
    val selectedStoreId: String? = null,
    val loading: Boolean = false,
    val error: String? = null,
)

class StoresViewModel(private val repo: ShelfMapperRepository) : ViewModel() {
    private val _state = MutableStateFlow(StoresUiState())
    val state: StateFlow<StoresUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            repo.selectedStoreId.collect { id ->
                _state.update { it.copy(selectedStoreId = id) }
            }
        }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repo.listStores() }
                .onSuccess { stores -> _state.update { it.copy(stores = stores, loading = false) } }
                .onFailure { e -> _state.update { it.copy(loading = false, error = e.message ?: "Failed to load stores") } }
        }
    }

    fun createStore(name: String, address: String?) {
        if (name.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repo.createStore(name.trim(), address?.takeIf { it.isNotBlank() }) }
                .onSuccess { store ->
                    repo.selectStore(store.id)
                    refresh()
                }
                .onFailure { e -> _state.update { it.copy(loading = false, error = e.message ?: "Failed to create store") } }
        }
    }

    fun select(id: String) = repo.selectStore(id)

    companion object {
        val Factory = viewModelFactory {
            initializer { StoresViewModel(repository()) }
        }
    }
}
