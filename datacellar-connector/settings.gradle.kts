rootProject.name = "datacellar-connector"

pluginManagement {
    repositories {
        maven {
            url = uri("https://oss.sonatype.org/content/repositories/snapshots/")
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    // Apply the foojay-resolver plugin to allow automatic download of JDKs
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.4.0"
}

dependencyResolutionManagement {
    repositories {
        maven {
            url = uri("https://oss.sonatype.org/content/repositories/snapshots/")
        }
        mavenCentral()
        mavenLocal()
    }
    versionCatalogs {
        create("libs") {
            from("org.eclipse.edc:edc-versions:0.0.1-milestone-8")
            // this is not part of the published EDC Version Catalog, so we'll just "amend" it
            library(
                "dnsOverHttps",
                "com.squareup.okhttp3",
                "okhttp-dnsoverhttps",
            ).versionRef("okhttp")
        }
    }
}

include("app")
