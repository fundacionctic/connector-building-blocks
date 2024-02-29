plugins {
    `java-library`
}

val okHttpVersion = "4.12.0"
val jwtVersion = "0.12.5"

dependencies {
    implementation(libs.edc.connector.core)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.core.spi)

    implementation(libs.json)
    implementation("com.squareup.okhttp3:okhttp:$okHttpVersion")
    implementation("io.jsonwebtoken:jjwt-api:$jwtVersion")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:$jwtVersion")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:$jwtVersion")
}
