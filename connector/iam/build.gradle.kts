plugins {
    `java-library`
}

dependencies {
    implementation(libs.edc.connector.core)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.core.spi)

    implementation(libs.json)
    implementation(libs.okhttp3.okhttp)
    implementation(libs.jsonwebtoken.jjwt.api)
    runtimeOnly(libs.jsonwebtoken.jjwt.impl)
    runtimeOnly(libs.jsonwebtoken.jjwt.jackson)
}
