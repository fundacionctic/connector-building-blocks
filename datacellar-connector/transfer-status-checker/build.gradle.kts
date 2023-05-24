plugins {
    `java-library`
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    api("$edcGroupId:control-plane-spi:$edcVersion")
}
