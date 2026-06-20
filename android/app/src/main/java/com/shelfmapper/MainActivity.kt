package com.shelfmapper

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.shelfmapper.ui.theme.ShelfMapperTheme
import com.shelfmapper.ui.ShelfMapperApp as ShelfMapperNavApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ShelfMapperTheme {
                ShelfMapperNavApp()
            }
        }
    }
}
