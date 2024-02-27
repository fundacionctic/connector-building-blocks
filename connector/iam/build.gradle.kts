plugins {
    `java-library`
}

val waltIdVersion = "1.0.2402271122-SNAPSHOT"

dependencies {
    implementation(libs.edc.connector.core)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.core.spi)

    implementation("javax.json:javax.json-api:1.1.4")
    implementation("id.walt.did:waltid-did:$waltIdVersion")
    implementation("id.walt.credentials:waltid-verifiable-credentials:$waltIdVersion")
}
