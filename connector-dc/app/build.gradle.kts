plugins {
    application
    `java-library`
    id("com.github.johnrengelman.shadow") version "7.1.2"
}

repositories {
    mavenCentral()
}

val edcVersion: String by project

dependencies {
    testImplementation("junit:junit:4.13.2")
    implementation("org.eclipse.edc:control-plane-core:$edcVersion")
    implementation("org.eclipse.edc:http:$edcVersion")
    implementation(libs.jakarta.rsApi)
    implementation("org.eclipse.edc:configuration-filesystem:$edcVersion")
    implementation("org.eclipse.edc:management-api:$edcVersion")
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
    archiveFileName.set("datacellar-connector.jar")
}
