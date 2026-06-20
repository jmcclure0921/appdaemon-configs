package com.shelfmapper.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Wire models for the ShelfMapper API. These mirror docs/api-contract.md exactly;
 * `@SerialName` maps Kotlin camelCase to the API's snake_case.
 */

@Serializable
data class Point(val x: Double, val y: Double)

@Serializable
data class PathPoint(
    @SerialName("t_ms") val tMs: Long,
    val lat: Double? = null,
    val lon: Double? = null,
    @SerialName("heading_deg") val headingDeg: Double? = null,
    val step: Int? = null,
)

@Serializable
data class StoreCreate(val name: String, val address: String? = null)

@Serializable
data class Store(
    val id: String,
    val name: String,
    val address: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class SessionMeta(
    @SerialName("recorded_at") val recordedAt: String,
    @SerialName("duration_ms") val durationMs: Long,
    val path: List<PathPoint>,
)

@Serializable
data class Session(
    val id: String,
    @SerialName("store_id") val storeId: String,
    val status: String,
    @SerialName("recorded_at") val recordedAt: String? = null,
    @SerialName("duration_ms") val durationMs: Long = 0,
    val path: List<PathPoint> = emptyList(),
    @SerialName("detection_count") val detectionCount: Int = 0,
)

@Serializable
data class MapEntry(
    val label: String,                       // store section, e.g. "Dairy & Eggs"
    val category: String? = null,
    val keywords: List<String> = emptyList(), // example items in the section
    val position: Point,
    @SerialName("path_distance_m") val pathDistanceM: Double = 0.0,
    @SerialName("observation_count") val observationCount: Int = 0,
)

@Serializable
data class StoreMap(
    @SerialName("store_id") val storeId: String,
    val entries: List<MapEntry> = emptyList(),
)

@Serializable
data class OptimizeRequest(
    val items: List<String>,
    val start: Point? = null,
    @SerialName("round_trip") val roundTrip: Boolean = false,
)

@Serializable
data class RouteStop(
    val order: Int,
    val query: String,
    val label: String,
    val position: Point,
    @SerialName("path_distance_m") val pathDistanceM: Double,
    val matched: Boolean = true,
)

@Serializable
data class OptimizedRoute(
    val stops: List<RouteStop> = emptyList(),
    val unmatched: List<String> = emptyList(),
    @SerialName("total_distance_m") val totalDistanceM: Double = 0.0,
    @SerialName("ordered_query_list") val orderedQueryList: List<String> = emptyList(),
)
