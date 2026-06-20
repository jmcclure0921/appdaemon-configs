package com.shelfmapper.ui.shop

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.shelfmapper.data.OptimizedRoute
import com.shelfmapper.data.ShelfMapperRepository
import com.shelfmapper.data.local.ShoppingItem
import com.shelfmapper.ui.repository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RouteUiState(
    val route: OptimizedRoute? = null,
    val loading: Boolean = false,
    val error: String? = null,
    val hasStore: Boolean = false,
)

class ShopViewModel(private val repo: ShelfMapperRepository) : ViewModel() {

    val items: StateFlow<List<ShoppingItem>> = repo.observeShoppingList()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _route = MutableStateFlow(RouteUiState())
    val routeState: StateFlow<RouteUiState> = _route.asStateFlow()

    init {
        viewModelScope.launch {
            repo.selectedStoreId.collect { id -> _route.update { it.copy(hasStore = id != null) } }
        }
    }

    fun add(text: String) {
        if (text.isBlank()) return
        viewModelScope.launch { repo.addItem(text) }
    }

    fun toggle(item: ShoppingItem) {
        viewModelScope.launch { repo.setChecked(item, !item.checked) }
    }

    fun remove(item: ShoppingItem) {
        viewModelScope.launch { repo.removeItem(item.id) }
    }

    fun optimize(roundTrip: Boolean) {
        val storeId = repo.selectedStoreId.value
        if (storeId == null) {
            _route.update { it.copy(error = "Select a store on the Stores tab first.") }
            return
        }
        val queries = items.value.filter { !it.checked }.map { it.text }.filter { it.isNotBlank() }
        if (queries.isEmpty()) {
            _route.update { it.copy(error = "Add some items to optimize.") }
            return
        }
        viewModelScope.launch {
            _route.update { it.copy(loading = true, error = null) }
            runCatching { repo.optimize(storeId, queries, roundTrip) }
                .onSuccess { route -> _route.update { it.copy(route = route, loading = false) } }
                .onFailure { e -> _route.update { it.copy(loading = false, error = e.message ?: "Optimize failed") } }
        }
    }

    companion object {
        val Factory = viewModelFactory {
            initializer { ShopViewModel(repository()) }
        }
    }
}
