plugins {
    `java-library`
}

dependencies {
    implementation(libs.edc.boot)
    implementation(libs.edc.connector.core)
    implementation(libs.edc.http)
    implementation(libs.edc.control.plane.api.client)
    implementation(libs.edc.control.plane.api)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.dsp)
    implementation(libs.edc.configuration.filesystem)
    implementation(libs.edc.vault.filesystem)
    implementation(libs.edc.management.api)
    implementation(libs.edc.core.spi)
    implementation(libs.json)

    implementation(libs.edc.fc.spi.crawler)
    runtimeOnly(libs.edc.fc.core)
    runtimeOnly(libs.edc.fc.ext.api)
}