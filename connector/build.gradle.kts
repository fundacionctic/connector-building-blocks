plugins {
    `java-library`
}

repositories {
    mavenCentral()
}

val edcVersion: String by project
val edcGroupId: String by project

buildscript {
    dependencies {
        val edcVersion: String by project
        classpath("org.eclipse.edc.edc-build:org.eclipse.edc.edc-build.gradle.plugin:$edcVersion")
    }
}

allprojects {

    apply(plugin = "$edcGroupId.edc-build")

    // configure which version of the annotation processor to use. defaults to the same version as the plugin
    configure<org.eclipse.edc.plugins.autodoc.AutodocExtension> {
        processorVersion.set(edcVersion)
        outputDirectory.set(project.buildDir)
    }

    configure<org.eclipse.edc.plugins.edcbuild.extensions.BuildExtension> {
        versions {
            // override default dependency versions here
            projectVersion.set(edcVersion)
            metaModel.set(edcVersion)
        }
        publish.set(false)
    }

    // Disable the default style enforcer from the edc-build plugin to avoid unnecessary noise.
    gradle.projectsEvaluated {
        tasks.withType<Checkstyle> {
            enabled = false
        }
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
