plugins {
    application
    `java-library`
    id("com.github.johnrengelman.shadow") version "7.1.2"
}

val groupId: String by project
val edcVersion: String by project

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.9.1")
    implementation("$groupId:configuration-filesystem:$edcVersion")
    implementation("$groupId:control-plane-core:$edcVersion")
    implementation("$groupId:api-observability:$edcVersion")
    implementation("$groupId:iam-mock:$edcVersion")
    implementation("$groupId:auth-tokenbased:$edcVersion")
    implementation("$groupId:management-api:$edcVersion")
    implementation("$groupId:ids:$edcVersion")
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}

application {
    mainClass.set("org.eclipse.edc.boot.system.runtime.BaseRuntime")
}

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    exclude("**/pom.properties", "**/pom.xm")
    mergeServiceFiles()
    archiveFileName.set("consumer.jar")
}
