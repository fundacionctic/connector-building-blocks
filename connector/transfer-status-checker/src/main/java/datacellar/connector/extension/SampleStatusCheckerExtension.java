package datacellar.connector.extension;

import org.eclipse.edc.connector.transfer.spi.status.StatusCheckerRegistry;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;

/**
 * Sample implementation of a ServiceExtension that registers a
 * StatusChecker for the destination type.
 */
@Extension(value = SampleStatusCheckerExtension.NAME)
public class SampleStatusCheckerExtension implements ServiceExtension {

    /**
     * The destination type for which the SampleStatusChecker is registered.
     */
    public static final String DESTINATION_TYPE = "jsonfile";

    /**
     * The name of the extension.
     */
    public static final String NAME = "Proof-of-concept status checker extension";

    @Inject
    private StatusCheckerRegistry checkerRegistry;

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        checkerRegistry.register(DESTINATION_TYPE, new SampleStatusChecker());
    }
}