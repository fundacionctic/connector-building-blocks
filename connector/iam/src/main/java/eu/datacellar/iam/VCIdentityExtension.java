package eu.datacellar.iam;

import java.io.IOException;

import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Provides;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.iam.IdentityService;
import org.eclipse.edc.spi.monitor.Monitor;
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

    @Setting
    private static final String WALLET_URL = "eu.datacellar.wallet.url";

    @Setting
    private static final String WALLET_EMAIL = "eu.datacellar.wallet.email";

    @Setting
    private static final String WALLET_PASSWORD = "eu.datacellar.wallet.password";

    @Setting
    private static final String WALLET_ID = "eu.datacellar.wallet.id";

    @Inject
    private TypeManager typeManager;

    @Override
    public String name() {
        return NAME;
    }

    public WaltIDIdentityServices buildIdentityServices(ServiceExtensionContext context)
            throws IOException, InterruptedException {
        String walletUrl = context.getSetting(WALLET_URL, null);
        String walletEmail = context.getSetting(WALLET_EMAIL, null);
        String walletPassword = context.getSetting(WALLET_PASSWORD, null);

        if (walletUrl == null || walletEmail == null || walletPassword == null) {
            throw new IllegalArgumentException("Wallet URL, email, and password must be provided");
        }

        String walletId = context.getSetting(WALLET_ID, null);
        Monitor monitor = context.getMonitor();

        if (walletId == null) {
            return new WaltIDIdentityServices(monitor, walletUrl, walletEmail, walletPassword);
        } else {
            return new WaltIDIdentityServices(monitor, walletUrl, walletEmail, walletPassword, walletId);
        }
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        var participantId = context.getParticipantId();
        var monitor = context.getMonitor();

        try {
            WaltIDIdentityServices identityServices = buildIdentityServices(context);

            context.registerService(IdentityService.class,
                    new VCIdentityService(monitor, typeManager, participantId, identityServices));
        } catch (IOException | InterruptedException e) {
            context.getMonitor().severe("Failed to initialize WaltIDIdentityServices", e);
            System.exit(1);
        }

    }
}