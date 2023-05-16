package connector.dc;

import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.web.spi.WebService;

public class DataCellarExtension implements ServiceExtension {
    @Inject
    WebService webService;

    @Override
    public void initialize(ServiceExtensionContext context) {
        webService.registerResource(new DataCellarController(context.getMonitor()));
    }
}
