plugins {
    application
    `java-library`
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    api(libs.edc.control.plane.spi)
    api(libs.edc.data.plane.spi)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.data.plane.util)
    implementation(libs.edc.data.plane.client)
    implementation(libs.edc.data.plane.selector.client)
    implementation(libs.edc.data.plane.selector.core)
    implementation(libs.edc.transfer.data.plane)
    implementation(libs.opentelemetry.annotations)
    implementation(libs.json)
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}
