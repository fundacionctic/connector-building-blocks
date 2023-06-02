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
val edcVersion: String by project

dependencies {
    implementation("$edcGroupId:control-plane-core:$edcVersion")
    implementation("$edcGroupId:dsp:$edcVersion")
    implementation("$edcGroupId:iam-mock:$edcVersion")
    implementation("$edcGroupId:management-api:$edcVersion")
    implementation("$edcGroupId:data-plane-core:$edcVersion")

    implementation("$edcGroupId:data-plane-transfer-client:$edcVersion")
    implementation("$edcGroupId:data-plane-transfer-sync:$edcVersion")
    implementation("$edcGroupId:data-plane-api:$edcVersion")
    implementation("$edcGroupId:data-plane-http:$edcVersion")

    implementation("$edcGroupId:ids:$edcVersion")
    implementation("$edcGroupId:configuration-filesystem:$edcVersion")
    implementation("$edcGroupId:vault-filesystem:$edcVersion")
    implementation("$edcGroupId:transfer-data-plane:$edcVersion")
    implementation("$edcGroupId:transfer-pull-http-receiver:$edcVersion")
    implementation("$edcGroupId:data-plane-selector-api:$edcVersion")
    implementation("$edcGroupId:data-plane-selector-core:$edcVersion")
    implementation("$edcGroupId:data-plane-selector-client:$edcVersion")
}

application {
    mainClass.set("$edcGroupId.boot.system.runtime.BaseRuntime")
}

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    mergeServiceFiles()
    archiveFileName.set("datacellar-openapi-adapter.jar")
}
