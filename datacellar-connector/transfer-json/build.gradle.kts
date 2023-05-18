plugins {
    application
    `java-library`
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    api("$edcGroupId:control-plane-spi:$edcVersion")
    api("$edcGroupId:data-plane-spi:$edcVersion")
    implementation("$edcGroupId:control-plane-core:$edcVersion")
    implementation("$edcGroupId:data-plane-core:$edcVersion")
    implementation("$edcGroupId:data-plane-util:$edcVersion")
    implementation("$edcGroupId:data-plane-client:$edcVersion")
    implementation("$edcGroupId:data-plane-selector-client:$edcVersion")
    implementation("$edcGroupId:data-plane-selector-core:$edcVersion")
    implementation("$edcGroupId:transfer-data-plane:$edcVersion")
    implementation("org.json:json:20230227")
    implementation(libs.opentelemetry.annotations)
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}
