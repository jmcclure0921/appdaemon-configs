# kotlinx.serialization keeps generated serializers; the plugin emits the rules
# needed, but keep our @Serializable models' companion serializers to be safe.
-keepclassmembers,allowshrinking,allowobfuscation class com.shelfmapper.data.** {
    *** Companion;
}
-keepclasseswithmembers class com.shelfmapper.data.** {
    kotlinx.serialization.KSerializer serializer(...);
}
