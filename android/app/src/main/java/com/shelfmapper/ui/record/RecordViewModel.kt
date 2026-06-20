package com.shelfmapper.ui.record

import android.app.Application
import androidx.camera.view.PreviewView
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.shelfmapper.ShelfMapperApp
import com.shelfmapper.capture.PathRecorder
import com.shelfmapper.capture.VideoRecorder
import com.shelfmapper.data.SessionMeta
import com.shelfmapper.data.ShelfMapperRepository
import com.shelfmapper.ui.shelfApp
import java.io.File
import java.time.Instant
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class RecordPhase { Idle, Recording, Uploading, Processing, Done, Error }

data class RecordUiState(
    val phase: RecordPhase = RecordPhase.Idle,
    val selectedStoreId: String? = null,
    val selectedStoreName: String? = null,
    val message: String? = null,
    val detectionCount: Int = 0,
    /** Wall-clock start of the current recording, for the elapsed timer; null when idle. */
    val recordingStartedAt: Long? = null,
)

class RecordViewModel(
    app: Application,
    private val repo: ShelfMapperRepository,
) : AndroidViewModel(app) {

    private val video = VideoRecorder(app)
    private val path = PathRecorder(app)
    private var currentFile: File? = null

    private val _state = MutableStateFlow(RecordUiState())
    val state: StateFlow<RecordUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            repo.selectedStoreId.collect { id -> _state.update { it.copy(selectedStoreId = id) } }
        }
        viewModelScope.launch {
            repo.selectedStoreName.collect { name -> _state.update { it.copy(selectedStoreName = name) } }
        }
    }

    suspend fun bindCamera(owner: LifecycleOwner, preview: PreviewView) {
        runCatching { video.bind(owner, preview) }
            .onFailure { e -> _state.update { it.copy(phase = RecordPhase.Error, message = e.message) } }
    }

    fun toggle() {
        when (_state.value.phase) {
            RecordPhase.Recording -> stopAndUpload()
            RecordPhase.Idle, RecordPhase.Done, RecordPhase.Error -> startRecording()
            else -> Unit // busy uploading/processing
        }
    }

    private fun startRecording() {
        val storeId = _state.value.selectedStoreId
        if (storeId == null) {
            _state.update { it.copy(phase = RecordPhase.Error, message = "Select a store first (Stores tab).") }
            return
        }
        val file = File(getApplication<ShelfMapperApp>().cacheDir, "session_${System.currentTimeMillis()}.mp4")
        currentFile = file
        runCatching {
            video.start(file)
            path.start()
        }.onSuccess {
            _state.update {
                it.copy(
                    phase = RecordPhase.Recording,
                    message = "Walk slowly • slow down near prices",
                    detectionCount = 0,
                    recordingStartedAt = System.currentTimeMillis(),
                )
            }
        }.onFailure { e ->
            _state.update { it.copy(phase = RecordPhase.Error, message = e.message ?: "Could not start recording") }
        }
    }

    private fun stopAndUpload() {
        val storeId = _state.value.selectedStoreId ?: return
        viewModelScope.launch {
            video.stop()
            val recording = path.stop()
            val file = currentFile
            _state.update {
                it.copy(phase = RecordPhase.Uploading, message = "Uploading session…", recordingStartedAt = null)
            }

            val meta = SessionMeta(
                recordedAt = Instant.now().toString(),
                durationMs = recording.durationMs,
                path = recording.path,
            )
            runCatching { repo.uploadSession(storeId, meta, file) }
                .onSuccess { session -> pollUntilMapped(session.id) }
                .onFailure { e -> _state.update { it.copy(phase = RecordPhase.Error, message = e.message ?: "Upload failed") } }
        }
    }

    private suspend fun pollUntilMapped(sessionId: String) {
        _state.update { it.copy(phase = RecordPhase.Processing, message = "Processing video…") }
        repeat(MAX_POLLS) {
            val session = runCatching { repo.getSession(sessionId) }.getOrNull()
            when (session?.status) {
                "mapped" -> {
                    currentFile?.delete()
                    _state.update {
                        it.copy(
                            phase = RecordPhase.Done,
                            message = "Mapped ${session.detectionCount} products",
                            detectionCount = session.detectionCount,
                        )
                    }
                    return
                }
                "failed" -> {
                    _state.update { it.copy(phase = RecordPhase.Error, message = "Processing failed") }
                    return
                }
            }
            delay(POLL_INTERVAL_MS)
        }
        _state.update { it.copy(phase = RecordPhase.Error, message = "Timed out waiting for processing") }
    }

    private companion object {
        const val MAX_POLLS = 30
        const val POLL_INTERVAL_MS = 1_000L
    }

    companion object {
        val Factory = viewModelFactory {
            initializer {
                val app = shelfApp()
                RecordViewModel(app, app.container.repository)
            }
        }
    }
}
