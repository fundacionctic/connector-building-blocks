plugins {
    `java-library`
}

dependencies {
    implementation(libs.edc.boot)
    implementation(libs.edc.connector.core)
    implementation(libs.edc.core.spi)
    implementation(libs.edc.data.plane.spi)
    implementation(libs.edc.data.plane.http)
    implementation(libs.edc.http)
    implementation(libs.jakarta.rsApi)
    implementation(libs.okhttp3.okhttp)
}
