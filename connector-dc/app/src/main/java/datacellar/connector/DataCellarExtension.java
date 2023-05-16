package datacellar.connector;

import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.web.spi.WebService;

public class DataCellarExtension implements ServiceExtension {
    @Inject
    WebService webService;

    private static final String LOG_PREFIX_SETTING = "datacellar.connector.logprefix";

    @Override
    public void initialize(ServiceExtensionContext context) {
        String logPrefix = context.getSetting(LOG_PREFIX_SETTING, "DataCellar");
        webService.registerResource(new DataCellarController(context.getMonitor(), logPrefix));
    }
}
