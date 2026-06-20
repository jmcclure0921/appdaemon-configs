package com.shelfmapper.ui.record

import android.Manifest
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberMultiplePermissionsState

private val REQUIRED = listOf(
    Manifest.permission.CAMERA,
    Manifest.permission.ACCESS_FINE_LOCATION,
    Manifest.permission.ACTIVITY_RECOGNITION,
)

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
            Button(onClick = { permissions.launchMultiplePermissionRequest() }, modifier = Modifier.padding(top = 16.dp)) {
                Text("Grant permissions")
            }
        }
        return
    }

    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val previewView = remember { PreviewView(context) }

    LaunchedEffect(Unit) { vm.bindCamera(lifecycleOwner, previewView) }

    Box(Modifier.fillMaxSize()) {
        AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

        Column(
            Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            state.message?.let {
                Text(it, color = MaterialTheme.colorScheme.onPrimary, style = MaterialTheme.typography.titleMedium)
            }
            when (state.phase) {
                RecordPhase.Uploading, RecordPhase.Processing -> CircularProgressIndicator()
                else -> {
                    val recording = state.phase == RecordPhase.Recording
                    Button(onClick = vm::toggle, modifier = Modifier.fillMaxWidth()) {
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
}
