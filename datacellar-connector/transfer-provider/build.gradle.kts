plugins {
    `java-library`
    id("application")
    id("com.github.johnrengelman.shadow") version "7.1.2"
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.data.plane.selector.core)
    implementation(libs.edc.api.observability)
    implementation(libs.edc.configuration.filesystem)
    implementation(libs.edc.iam.mock)
    implementation(libs.edc.auth.tokenbased)
    implementation(libs.edc.management.api)
    implementation(libs.edc.dsp)
    implementation(project(":transfer-json"))
}

application {
    mainClass.set("org.eclipse.edc.boot.system.runtime.BaseRuntime")
}

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    exclude("**/pom.properties", "**/pom.xml")
    mergeServiceFiles()
    archiveFileName.set("provider.jar")
    dependsOn("distTar", "distZip")
}
