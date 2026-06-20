package com.shelfmapper.data

import android.content.Context
import com.shelfmapper.data.local.AppDatabase
import com.shelfmapper.data.local.ShoppingItem
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.serialization.encodeToString
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

/** Single entry point the UI uses for data: backend calls + local shopping list. */
class ShelfMapperRepository(
    context: Context,
    private val api: ApiService,
) {
    private val dao = AppDatabase.get(context).shoppingDao()
    private val prefs = context.getSharedPreferences("shelfmapper", Context.MODE_PRIVATE)

    /** Currently selected store, persisted across launches. */
    val selectedStoreId = MutableStateFlow(prefs.getString(KEY_STORE, null))
    val selectedStoreName = MutableStateFlow(prefs.getString(KEY_STORE_NAME, null))

    fun selectStore(id: String?, name: String? = null) {
        prefs.edit().putString(KEY_STORE, id).putString(KEY_STORE_NAME, name).apply()
        selectedStoreId.value = id
        selectedStoreName.value = name
    }

    // ---- stores ----------------------------------------------------------
    suspend fun listStores(): List<Store> = api.listStores()

    suspend fun createStore(name: String, address: String?): Store =
        api.createStore(StoreCreate(name = name, address = address))

    // ---- sessions --------------------------------------------------------
    suspend fun uploadSession(storeId: String, meta: SessionMeta, videoFile: File?): Session {
        val metaPart = Network.json.encodeToString(meta)
            .toRequestBody("application/json".toMediaType())
        val videoPart = videoFile?.let {
            MultipartBody.Part.createFormData(
                name = "video",
                filename = it.name,
                body = it.asRequestBody("video/mp4".toMediaType()),
            )
        }
        return api.uploadSession(storeId, metaPart, videoPart)
    }

    suspend fun getSession(id: String): Session = api.getSession(id)

    // ---- map & optimize --------------------------------------------------
    suspend fun getStoreMap(storeId: String): StoreMap = api.getStoreMap(storeId)

    suspend fun optimize(storeId: String, items: List<String>, roundTrip: Boolean): OptimizedRoute =
        api.optimize(storeId, OptimizeRequest(items = items, roundTrip = roundTrip))

    // ---- shopping list (local) ------------------------------------------
    fun observeShoppingList(): Flow<List<ShoppingItem>> = dao.observeAll()
    suspend fun addItem(text: String) = dao.insert(ShoppingItem(text = text.trim()))
    suspend fun setChecked(item: ShoppingItem, checked: Boolean) =
        dao.update(item.copy(checked = checked))
    suspend fun removeItem(id: Long) = dao.delete(id)

    private companion object {
        const val KEY_STORE = "selected_store_id"
        const val KEY_STORE_NAME = "selected_store_name"
    }
}
