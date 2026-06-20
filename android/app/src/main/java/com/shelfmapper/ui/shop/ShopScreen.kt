package com.shelfmapper.ui.shop

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.shelfmapper.data.RouteStop
import kotlin.math.roundToInt

@Composable
fun ShopScreen(vm: ShopViewModel = viewModel(factory = ShopViewModel.Factory)) {
    val items by vm.items.collectAsStateWithLifecycle()
    val routeState by vm.routeState.collectAsStateWithLifecycle()
    var entry by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Shopping list", style = MaterialTheme.typography.headlineSmall)

        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = entry,
                onValueChange = { entry = it },
                label = { Text("Add an item") },
                modifier = Modifier.weight(1f),
                singleLine = true,
            )
            IconButton(onClick = { vm.add(entry); entry = "" }) {
                Icon(Icons.Filled.Add, contentDescription = "Add")
            }
        }

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            items(items, key = { it.id }) { item ->
                Row(
                    Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Checkbox(checked = item.checked, onCheckedChange = { vm.toggle(item) })
                    Text(
                        item.text,
                        modifier = Modifier.weight(1f),
                        textDecoration = if (item.checked) TextDecoration.LineThrough else null,
                    )
                    IconButton(onClick = { vm.remove(item) }) {
                        Icon(Icons.Filled.Close, contentDescription = "Remove")
                    }
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { vm.optimize(roundTrip = false) }, modifier = Modifier.weight(1f)) {
                Text("Optimize route")
            }
            OutlinedButton(onClick = { vm.optimize(roundTrip = true) }, modifier = Modifier.weight(1f)) {
                Text("Round trip")
            }
        }

        if (!routeState.hasStore) {
            Text(
                "No store selected — pick one on the Stores tab.",
                color = MaterialTheme.colorScheme.error,
            )
        }
        routeState.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (routeState.loading) CircularProgressIndicator()

        routeState.route?.let { route -> RouteCard(route.stops, route.totalDistanceM, route.unmatched) }
    }
}

@Composable
private fun RouteCard(stops: List<RouteStop>, totalDistanceM: Double, unmatched: List<String>) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                "Optimized route · ${totalDistanceM.roundToInt()} m",
                style = MaterialTheme.typography.titleMedium,
            )
            HorizontalDivider()
            stops.forEach { stop ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("${stop.order + 1}. ${stop.label}")
                    Text("${stop.pathDistanceM.roundToInt()} m", style = MaterialTheme.typography.bodySmall)
                }
            }
            if (unmatched.isNotEmpty()) {
                HorizontalDivider()
                Text(
                    "Not found in this store: ${unmatched.joinToString(", ")}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}
