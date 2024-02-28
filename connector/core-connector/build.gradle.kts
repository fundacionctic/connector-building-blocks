plugins {
    `java-library`
    id("application")
    alias(libs.plugins.shadow)
}

dependencies {
    implementation(libs.edc.control.plane.api.client)
    implementation(libs.edc.control.plane.api)
    implementation(libs.edc.control.plane.core)
    implementation(libs.edc.dsp)
    implementation(libs.edc.configuration.filesystem)
    implementation(libs.edc.vault.filesystem)
    implementation(libs.edc.management.api)
    implementation(libs.edc.transfer.data.plane)
    implementation(libs.edc.transfer.pull.http.receiver)

    implementation(libs.edc.data.plane.selector.api)
    implementation(libs.edc.data.plane.selector.core)
    implementation(libs.edc.data.plane.selector.client)

    implementation(libs.edc.data.plane.api)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.data.plane.http)

    implementation(libs.swaggerParser)
    implementation(libs.slugify)

    if (
        project.hasProperty("useOauthIdentity") &&
        project.property("useOauthIdentity").toString().toBoolean()
    ) {
        implementation(libs.edc.oauth2.client)
        implementation(libs.edc.oauth2.core)
    } else if (
        project.hasProperty("useSSI") &&
        project.property("useSSI").toString().toBoolean()
    ) {
        api(project(":iam"))
    } else {
        implementation(libs.edc.iam.mock)
    }
}

application {
    mainClass.set("org.eclipse.edc.boot.system.runtime.BaseRuntime")
}

var distTar = tasks.getByName("distTar")
var distZip = tasks.getByName("distZip")

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    exclude("**/pom.properties", "**/pom.xm")
    mergeServiceFiles()
    archiveFileName.set("core-connector.jar")
    dependsOn(distTar, distZip)
}
