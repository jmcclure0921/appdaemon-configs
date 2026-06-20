package com.shelfmapper.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

/** A single line on the user's shopping list, persisted locally. */
@Entity(tableName = "shopping_items")
data class ShoppingItem(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val text: String,
    val checked: Boolean = false,
)
