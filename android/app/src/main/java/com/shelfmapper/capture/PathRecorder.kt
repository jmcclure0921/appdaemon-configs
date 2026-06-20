package com.shelfmapper.capture

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Looper
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.shelfmapper.data.PathPoint

/**
 * Records the walking path while a session is being filmed: GPS fixes plus a
 * step count (for indoor dead reckoning the backend can fall back to). All
 * samples are timestamped relative to [start].
 */
class PathRecorder(context: Context) : SensorEventListener {

    private val appContext = context.applicationContext
    private val fused = LocationServices.getFusedLocationProviderClient(appContext)
    private val sensorManager =
        appContext.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val stepSensor: Sensor? =
        sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)

    private val points = mutableListOf<PathPoint>()
    private var startedAtMs = 0L
    private var baselineSteps: Float? = null
    private var lastSteps = 0
    private var lastHeading: Double? = null
    private var recording = false

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val loc = result.lastLocation ?: return
            synchronized(points) {
                points += PathPoint(
                    tMs = now(),
                    lat = loc.latitude,
                    lon = loc.longitude,
                    headingDeg = if (loc.hasBearing()) loc.bearing.toDouble() else lastHeading,
                    step = lastSteps,
                )
            }
        }
    }

    @SuppressLint("MissingPermission") // Caller gates on location + activity permissions.
    fun start() {
        if (recording) return
        recording = true
        startedAtMs = System.currentTimeMillis()
        points.clear()
        baselineSteps = null
        lastSteps = 0

        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 1_000L)
            .setMinUpdateIntervalMillis(500L)
            .build()
        fused.requestLocationUpdates(request, locationCallback, Looper.getMainLooper())
        stepSensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL) }
    }

    /** Stops recording and returns the captured path together with its duration. */
    fun stop(): Recording {
        if (!recording) return Recording(emptyList(), 0)
        recording = false
        fused.removeLocationUpdates(locationCallback)
        stepSensor?.let { sensorManager.unregisterListener(this) }
        val captured = synchronized(points) { points.toList() }
        return Recording(captured, System.currentTimeMillis() - startedAtMs)
    }

    private fun now() = System.currentTimeMillis() - startedAtMs

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_STEP_COUNTER) return
        val total = event.values.firstOrNull() ?: return
        val base = baselineSteps ?: total.also { baselineSteps = it }
        lastSteps = (total - base).toInt()
        synchronized(points) {
            points += PathPoint(tMs = now(), step = lastSteps, headingDeg = lastHeading)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    data class Recording(val path: List<PathPoint>, val durationMs: Long)
}
