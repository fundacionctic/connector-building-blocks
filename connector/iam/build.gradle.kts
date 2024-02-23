plugins {
    `java-library`
}

dependencies {
    implementation(libs.edc.connector.core)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.core.spi)
}
