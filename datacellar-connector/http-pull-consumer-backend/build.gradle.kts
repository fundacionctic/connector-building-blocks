plugins {
    id("java")
}

tasks.withType<Jar> {
    manifest {
        attributes["Main-Class"] = "datacellar.connector.ConsumerBackendService"
    }
}
