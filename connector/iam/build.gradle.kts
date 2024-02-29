plugins {
    `java-library`
}

val waltIdVersion = "1.0.2402271122-SNAPSHOT"
val okHttpVersion = "4.12.0"
val jwtVersion = "4.4.0"

dependencies {
    implementation(libs.edc.connector.core)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.core.spi)

    implementation(libs.json)
    implementation("com.squareup.okhttp3:okhttp:$okHttpVersion")
    implementation("id.walt.did:waltid-did:$waltIdVersion")
    implementation("id.walt.credentials:waltid-verifiable-credentials:$waltIdVersion")
    implementation("com.auth0:java-jwt:$jwtVersion")
}
