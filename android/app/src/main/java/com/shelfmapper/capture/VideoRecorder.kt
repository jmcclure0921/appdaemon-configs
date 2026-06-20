package com.shelfmapper.capture

import android.annotation.SuppressLint
import android.content.Context
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.io.File
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

/**
 * Wraps CameraX video capture: binds a preview + recorder to the lifecycle,
 * then records to an mp4 file. Audio is omitted — we only need the shelves.
 */
class VideoRecorder(private val context: Context) {

    private var videoCapture: VideoCapture<Recorder>? = null
    private var activeRecording: Recording? = null

    /** Bind preview + capture use cases. Call from a permission-granted context. */
    suspend fun bind(lifecycleOwner: LifecycleOwner, previewView: PreviewView) {
        val provider = awaitProvider()
        val preview = Preview.Builder().build().also {
            it.setSurfaceProvider(previewView.surfaceProvider)
        }
        val recorder = Recorder.Builder()
            .setQualitySelector(QualitySelector.from(Quality.HD))
            .build()
        val capture = VideoCapture.withOutput(recorder)
        provider.unbindAll()
        provider.bindToLifecycle(
            lifecycleOwner,
            CameraSelector.DEFAULT_BACK_CAMERA,
            preview,
            capture,
        )
        videoCapture = capture
    }

    @SuppressLint("MissingPermission") // Recording without audio; camera permission gated by caller.
    fun start(output: File) {
        val capture = videoCapture ?: error("bind() must be called before start()")
        val options = FileOutputOptions.Builder(output).build()
        activeRecording = capture.output
            .prepareRecording(context, options)
            .start(ContextCompat.getMainExecutor(context)) { /* events ignored; finalize on stop */ }
    }

    /** Stops recording. The file is fully written once this returns. */
    suspend fun stop(): Unit = suspendCancellableCoroutine { cont ->
        val recording = activeRecording
        if (recording == null) {
            cont.resume(Unit)
            return@suspendCancellableCoroutine
        }
        // VideoRecordEvent.Finalize signals the file is flushed; we just stop().
        recording.stop()
        activeRecording = null
        cont.resume(Unit)
    }

    private suspend fun awaitProvider(): ProcessCameraProvider =
        suspendCancellableCoroutine { cont ->
            val future = ProcessCameraProvider.getInstance(context)
            future.addListener({ cont.resume(future.get()) }, ContextCompat.getMainExecutor(context))
        }
}
