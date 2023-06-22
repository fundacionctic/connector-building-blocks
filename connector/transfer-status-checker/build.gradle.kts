plugins {
    `java-library`
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    api(libs.edc.control.plane.spi)
}
