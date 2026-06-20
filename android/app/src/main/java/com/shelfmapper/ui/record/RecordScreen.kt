package com.shelfmapper.ui.record

import android.Manifest
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FiberManualRecord
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberMultiplePermissionsState
import kotlinx.coroutines.delay

private val REQUIRED = listOf(
    Manifest.permission.CAMERA,
    Manifest.permission.ACCESS_FINE_LOCATION,
    Manifest.permission.ACTIVITY_RECOGNITION,
)

private val Scrim = Color(0x99000000)
private val RecordRed = Color(0xFFE53935)

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun RecordScreen(vm: RecordViewModel = viewModel(factory = RecordViewModel.Factory)) {
    val state by vm.state.collectAsStateWithLifecycle()
    val permissions = rememberMultiplePermissionsState(REQUIRED)

    if (!permissions.allPermissionsGranted) {
        Column(
            Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("Camera, location and activity permissions are needed to record a store walk.")
            Button(
                onClick = { permissions.launchMultiplePermissionRequest() },
                modifier = Modifier.padding(top = 16.dp),
            ) { Text("Grant permissions") }
        }
        return
    }

    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val previewView = remember { PreviewView(context) }

    LaunchedEffect(Unit) { vm.bindCamera(lifecycleOwner, previewView) }

    Box(Modifier.fillMaxSize()) {
        AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

        TargetStorePill(
            storeName = state.selectedStoreName,
            recording = state.phase == RecordPhase.Recording,
            recordingStartedAt = state.recordingStartedAt,
            modifier = Modifier.align(Alignment.TopStart).statusBarsPadding().padding(16.dp),
        )

        Controls(
            state = state,
            onToggle = vm::toggle,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(16.dp),
        )
    }
}

@Composable
private fun TargetStorePill(
    storeName: String?,
    recording: Boolean,
    recordingStartedAt: Long?,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(Scrim)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (recording && recordingStartedAt != null) {
            Box(Modifier.size(10.dp).clip(CircleShape).background(RecordRed))
            Spacer(Modifier.width(8.dp))
            Text(elapsed(recordingStartedAt), color = Color.White, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(8.dp))
        }
        Text(
            storeName?.let { "Mapping: $it" } ?: "No store selected — pick one on the Stores tab",
            color = Color.White,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}

@Composable
private fun Controls(
    state: RecordUiState,
    onToggle: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Scrim)
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        val isError = state.phase == RecordPhase.Error
        state.message?.let {
            Text(
                it,
                color = if (isError) RecordRed else Color.White,
                style = MaterialTheme.typography.titleMedium,
                textAlign = TextAlign.Center,
            )
        }

        if (state.phase == RecordPhase.Idle || state.phase == RecordPhase.Done) {
            Text(
                "Walk down each aisle at a normal pace, aiming the camera at the shelves. "
                    + "We map which sections are where — no need to stop or scan tags.",
                color = Color.White.copy(alpha = 0.85f),
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
            )
        }

        when (state.phase) {
            RecordPhase.Uploading, RecordPhase.Processing -> CircularProgressIndicator(color = Color.White)
            else -> {
                val recording = state.phase == RecordPhase.Recording
                Button(onClick = onToggle, modifier = Modifier.fillMaxWidth()) {
                    Icon(
                        if (recording) Icons.Filled.Stop else Icons.Filled.FiberManualRecord,
                        contentDescription = null,
                    )
                    Text(
                        if (recording) "  Stop & upload" else "  Start recording",
                        modifier = Modifier.padding(start = 4.dp),
                    )
                }
            }
        }
    }
}

/** Live mm:ss elapsed since [startedAt], ticking once a second. */
@Composable
private fun elapsed(startedAt: Long): String {
    var now by remember(startedAt) { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(startedAt) {
        while (true) {
            now = System.currentTimeMillis()
            delay(1000)
        }
    }
    val secs = ((now - startedAt) / 1000).coerceAtLeast(0)
    return "%d:%02d".format(secs / 60, secs % 60)
}
