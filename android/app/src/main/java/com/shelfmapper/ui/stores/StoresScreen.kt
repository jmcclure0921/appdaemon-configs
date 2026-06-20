package com.shelfmapper.ui.stores

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun StoresScreen(vm: StoresViewModel = viewModel(factory = StoresViewModel.Factory)) {
    val state by vm.state.collectAsStateWithLifecycle()
    var name by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }

    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Stores", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Pick the store you're mapping, or add a new one.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Store name") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = address,
                    onValueChange = { address = it },
                    label = { Text("Address (optional)") },
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = { vm.createStore(name, address); name = ""; address = "" },
                    enabled = name.isNotBlank() && !state.loading,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Add store") }
            }
        }

        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (state.loading) CircularProgressIndicator()

        LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(state.stores, key = { it.id }) { store ->
                val selected = store.id == state.selectedStoreId
                ListItem(
                    headlineContent = {
                        Text(
                            store.name,
                            fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                        )
                    },
                    supportingContent = store.address?.let { addr -> { Text(addr) } },
                    trailingContent = {
                        if (selected) Icon(Icons.Filled.CheckCircle, contentDescription = "Selected")
                    },
                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
                        .clickable { vm.select(store.id) },
                )
            }
        }
    }
}
