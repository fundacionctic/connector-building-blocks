plugins {
    `java-library`
}

repositories {
    mavenCentral()
    gradlePluginPortal()
}

val javaVersion: String by project
val groupId: String by project
val defaultVersion: String by project
val annotationProcessorVersion: String by project
val metaModelVersion: String by project

val actualVersion: String = (project.findProperty("version") ?: defaultVersion) as String

buildscript {
    dependencies {
        val edcGradlePluginsVersion: String by project
        classpath("org.eclipse.edc.edc-build:org.eclipse.edc.edc-build.gradle.plugin:${edcGradlePluginsVersion}")
    }
}

allprojects {
    // Disable the default style enforcer from the edc-build plugin to avoid unnecessary noise.
    gradle.projectsEvaluated {
        tasks.withType<Checkstyle> {
            enabled = false
        }
    }

    apply(plugin = "${groupId}.edc-build")

    // Configure which version of the annotation processor to use. Defaults to the same version as the plugin.
    configure<org.eclipse.edc.plugins.autodoc.AutodocExtension> {
        processorVersion.set(annotationProcessorVersion)
        outputDirectory.set(project.buildDir)
    }

    configure<org.eclipse.edc.plugins.edcbuild.extensions.BuildExtension> {
        versions {
            // Override default dependency versions here.
            projectVersion.set(actualVersion)
            metaModel.set(metaModelVersion)
        }
        javaLanguageVersion.set(JavaLanguageVersion.of(javaVersion))
        publish.set(false)
    }

    // EdcRuntimeExtension uses this to determine the runtime classpath of the module to run.
    tasks.register("printClasspath") {
        doLast {
            println(sourceSets["main"].runtimeClasspath.asPath)
        }
    }
}

tasks.named<Test>("test") {
    // Use JUnit Platform for unit tests.
    useJUnitPlatform()
}