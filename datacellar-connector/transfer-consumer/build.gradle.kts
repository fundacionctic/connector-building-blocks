plugins {
    `java-library`
    id("application")
    id("com.github.johnrengelman.shadow") version "7.1.2"
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    implementation("$edcGroupId:control-plane-core:$edcVersion")
    implementation("$edcGroupId:api-observability:$edcVersion")
    implementation("$edcGroupId:configuration-filesystem:$edcVersion")
    implementation("$edcGroupId:iam-mock:$edcVersion")
    implementation("$edcGroupId:auth-tokenbased:$edcVersion")
    implementation("$edcGroupId:management-api:$edcVersion")
    implementation("$edcGroupId:ids:$edcVersion")
    implementation(project(":transfer-status-checker"))
}

application {
    mainClass.set("org.eclipse.edc.boot.system.runtime.BaseRuntime")
}

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    exclude("**/pom.properties", "**/pom.xml")
    mergeServiceFiles()
    archiveFileName.set("consumer.jar")
    dependsOn("distTar", "distZip")
}
