plugins {
    `java-library`
    id("application")
    id("com.github.johnrengelman.shadow") version "7.1.2"
}

repositories {
    mavenCentral()
    maven {
        url = uri("https://maven.iais.fraunhofer.de/artifactory/eis-ids-public/")
    }
}

val edcGroupId: String by project

dependencies {
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.dsp)
    implementation(libs.edc.iam.mock)
    implementation(libs.edc.management.api)
    implementation(libs.edc.data.plane.core)

    implementation(libs.edc.data.plane.api)
    implementation(libs.edc.data.plane.http)

    implementation(libs.edc.configuration.filesystem)
    implementation(libs.edc.vault.filesystem)
    implementation(libs.edc.transfer.data.plane)
    implementation(libs.edc.transfer.pull.http.receiver)
    implementation(libs.edc.data.plane.selector.api)
    implementation(libs.edc.data.plane.selector.core)
    implementation(libs.edc.data.plane.selector.client)
}

application {
    mainClass.set("$edcGroupId.boot.system.runtime.BaseRuntime")
}

var distTar = tasks.getByName("distTar")
var distZip = tasks.getByName("distZip")

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    exclude("**/pom.properties", "**/pom.xm")
    mergeServiceFiles()
    archiveFileName.set("datacellar-openapi-adapter.jar")
    dependsOn(distTar, distZip)
}
