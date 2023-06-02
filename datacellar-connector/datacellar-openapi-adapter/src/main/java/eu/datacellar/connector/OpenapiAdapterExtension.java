package eu.datacellar.connector;

import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;

/**
 * An extension that acts as a thin layer between the Data Cellar data space
 * and an existing HTTP API in a private backend accessible by the connector.
 */
@Extension(value = OpenapiAdapterExtension.NAME)
public class OpenapiAdapterExtension implements ServiceExtension {

    /**
     * The name of the extension.
     */
    public static final String NAME = "Data Cellar OpenAPI Adapter Extension";

    @Setting
    private static final String OPENAPI_URL = "eu.datacellar.openapiurl";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        var openapiUrl = context.getSetting(OPENAPI_URL, null);

        if (openapiUrl == null) {
            throw new IllegalStateException(String.format("OpenAPI URL '%s' is not set", OPENAPI_URL));
        }

        Monitor monitor = context.getMonitor();
        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }
}