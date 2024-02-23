package eu.datacellar.iam;

import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Provides;
import org.eclipse.edc.spi.iam.IdentityService;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.TypeManager;

/**
 * This class represents the VCIdentityExtension, which is an implementation of
 * the ServiceExtension interface.
 * It provides functionality related to the IAM extension.
 */
@Provides(IdentityService.class)
@Extension(value = VCIdentityExtension.NAME)
public class VCIdentityExtension implements ServiceExtension {

    /**
     * The name of the IAM extension.
     */
    public static final String NAME = "VC-based IAM";

    @Inject
    private TypeManager typeManager;

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        var region = context.getSetting("edc.mock.region", "eu");
        var participantId = context.getParticipantId();
        var monitor = context.getMonitor();
        context.registerService(IdentityService.class,
                new VCIdentityService(monitor, typeManager, region, participantId));
    }
}