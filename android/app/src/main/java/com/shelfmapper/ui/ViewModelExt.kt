package com.shelfmapper.ui

import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import com.shelfmapper.ShelfMapperApp
import com.shelfmapper.data.ShelfMapperRepository

/** Pulls the singleton repository out of [CreationExtras] inside a ViewModel factory. */
fun CreationExtras.shelfApp(): ShelfMapperApp = this[APPLICATION_KEY] as ShelfMapperApp

fun CreationExtras.repository(): ShelfMapperRepository = shelfApp().container.repository
