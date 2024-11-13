plugins {
    `java-library`
    id("application")
    alias(libs.plugins.shadow)
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
    implementation(libs.edc.transfer.data.plane)
    implementation(libs.edc.transfer.pull.http.receiver)
    implementation(libs.edc.core.spi)

    implementation(libs.edc.data.plane.selector.api)
    implementation(libs.edc.data.plane.selector.core)

    implementation(libs.edc.data.plane.control.api)
    implementation(libs.edc.data.plane.public.api)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.data.plane.http)

    api(libs.edc.data.plane.spi)
    api(libs.edc.json.ld.spi)

    implementation(libs.swaggerParser)
    implementation(libs.slugify)
    implementation(libs.json)
    implementation(libs.okhttp3.okhttp)

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

    implementation(libs.postgresql.postgresql)
    implementation(libs.edc.transaction.datasource.spi)
    implementation(libs.edc.transaction.local)

    if (
        project.hasProperty("useSQLStore") &&
        project.property("useSQLStore").toString().toBoolean()
    ) {
        // https://github.com/eclipse-edc/Connector/discussions/3242
        implementation(libs.edc.sql.control.plane.sql)
        implementation(libs.edc.sql.pool.apache.commons)
    }

    if (
        !project.hasProperty("disableAuth") ||
        !project.property("disableAuth").toString().toBoolean()
    ) {
        implementation(libs.edc.auth.tokenbased)
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
    archiveFileName.set("openapi-connector.jar")
    dependsOn(distTar, distZip)
}
