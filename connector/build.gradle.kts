plugins {
    `java-library`
}

allprojects {
    repositories {
        mavenCentral()
        maven { url = uri("https://maven.walt.id/repository/waltid/") }
    }
}

buildscript {
    dependencies {
        classpath(libs.edc.build.plugin)
    }
}

val edcVersion = libs.versions.edc

allprojects {
    apply(plugin = "$group.edc-build")

    // configure which version of the annotation processor to use. defaults to the same version as the plugin
    configure<org.eclipse.edc.plugins.autodoc.AutodocExtension> {
        processorVersion.set(edcVersion)
        outputDirectory.set(project.layout.buildDirectory.asFile.get())
    }

    configure<org.eclipse.edc.plugins.edcbuild.extensions.BuildExtension> {
        versions {
            // override default dependency versions here
            metaModel.set(edcVersion)
        }
        publish.set(false)
    }

    gradle.projectsEvaluated {
        tasks.withType<Checkstyle> {
            enabled = false
        }
    }
}
