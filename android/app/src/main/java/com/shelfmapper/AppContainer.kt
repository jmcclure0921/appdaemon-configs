package com.shelfmapper

import android.content.Context
import com.shelfmapper.data.Network
import com.shelfmapper.data.ShelfMapperRepository

/** Tiny manual DI container; created once in [ShelfMapperApp]. */
class AppContainer(context: Context) {
    private val api = Network.create(BuildConfig.BASE_URL)
    val repository = ShelfMapperRepository(context, api)
}
