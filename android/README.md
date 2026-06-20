# ShelfMapper Android app

Native Kotlin + Jetpack Compose app for the record → map → optimize loop. Talks
to the backend over the API in [`../docs/api-contract.md`](../docs/api-contract.md).

## Build & run

You need the Android SDK (Android Studio, or the command-line tools with a
`local.properties` pointing at the SDK). Then:

```bash
cd android
./gradlew assembleDebug          # build the APK
./gradlew installDebug           # install on a connected device/emulator
```

The backend base URL is a `buildConfigField` in `app/build.gradle.kts`. It
defaults to `http://10.0.2.2:8000/` (the host machine as seen from the Android
emulator). For a physical device, change it to your machine's LAN address and
rebuild. Cleartext HTTP is enabled for local development.

## What it does

Three tabs:

- **Stores** — create the store you're about to map, or pick an existing one.
  The selection is remembered across launches.
- **Record** — live camera preview with a record button. Shows which store
  you're mapping, an elapsed timer while recording, and capture guidance (walk
  slowly, hold steady, slow down near prices). Captures at FHD with video
  stabilization so shelf tags survive a normal walking pace. While recording it
  captures the walking path (fused location + step counter), then on stop it
  uploads the video + path and polls until the backend has mapped it.
- **Shop** — a local shopping list. "Optimize route" sends the list to the
  backend and shows the stops in walking order with cumulative distance, plus
  any items not found in that store's map.

## Structure

```
app/src/main/java/com/shelfmapper/
  ShelfMapperApp.kt        Application; builds the AppContainer (manual DI)
  AppContainer.kt          Retrofit + repository singletons
  MainActivity.kt          Compose entry point
  capture/
    VideoRecorder.kt       CameraX preview + video capture (no audio)
    PathRecorder.kt        Fused location + step-counter path capture
  data/
    Dto.kt                 @Serializable wire models (match the API contract)
    ApiService.kt          Retrofit interface
    Network.kt             Retrofit/OkHttp/kotlinx.serialization setup
    ShelfMapperRepository.kt  Backend calls + local shopping list + selection
    local/                 Room: shopping list persistence
  ui/
    ShelfMapperNav.kt      Bottom-nav scaffold
    stores/ record/ shop/  Screens + ViewModels
    theme/                 Material 3 theme
```

## Notes / next steps

- Dependency injection is a hand-rolled `AppContainer` to keep the scaffold
  light; swap for Hilt if it grows.
- Indoor stretches without GPS already record a step count; the backend does the
  dead reckoning. Fusing the magnetometer heading on-device would tighten it.
- The optimized route is shown as a list. A 2-D map overlay of the store, drawn
  from `GET /v1/stores/{id}/map` positions, is the natural next screen.
