# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in /opt/hostedtoolcache/AndroidSDK/tools/proguard/proguard-android.txt
# You can edit the include path and order by changing the proguardFiles
# directive in build.gradle.kts.

# For Hilt/Dagger
-keep class dagger.hilt.android.internal.managers.ViewComponentManager$ObjerViewComponentManager$ViewComponentBuilder { *; }
-keep class * extends androidx.lifecycle.ViewModel { *; }

# For Retrofit/Gson
-keepattributes Signature, InnerClasses, EnclosingMethod
-keepclassmembers class ** {
    @com.google.gson.annotations.SerializedName <fields>;
}
-keep class com.lucidpanda.android.data.model.** { *; }
