package com.shelfmapper.data

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

/** Retrofit binding for the ShelfMapper backend (docs/api-contract.md). */
interface ApiService {

    @GET("v1/stores")
    suspend fun listStores(): List<Store>

    @POST("v1/stores")
    suspend fun createStore(@Body body: StoreCreate): Store

    @GET("v1/stores/{id}")
    suspend fun getStore(@Path("id") storeId: String): Store

    /**
     * Multipart upload: `meta` is a JSON form field, `video` an optional file.
     * Matches the FastAPI handler which reads `meta` via `Form(...)`.
     */
    @Multipart
    @POST("v1/stores/{id}/sessions")
    suspend fun uploadSession(
        @Path("id") storeId: String,
        @Part("meta") meta: RequestBody,
        @Part video: MultipartBody.Part?,
    ): Session

    @GET("v1/sessions/{id}")
    suspend fun getSession(@Path("id") sessionId: String): Session

    @GET("v1/stores/{id}/map")
    suspend fun getStoreMap(@Path("id") storeId: String): StoreMap

    @POST("v1/stores/{id}/optimize")
    suspend fun optimize(@Path("id") storeId: String, @Body body: OptimizeRequest): OptimizedRoute
}
