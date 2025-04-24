package eu.datacellar.iam;

import java.io.IOException;

import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Provider;
import org.eclipse.edc.runtime.metamodel.annotation.Provides;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.iam.AudienceResolver;
import org.eclipse.edc.spi.iam.IdentityService;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.TypeManager;
import org.eclipse.edc.spi.types.domain.message.RemoteMessage;

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

    @Setting
    private static final String TRUST_ANCHOR_DID = "eu.datacellar.trust.did";

    @Setting
    private static final String UNIVERSAL_RESOLVER_URL = "eu.datacellar.uniresolver.url";

    @Setting
    private static final String VC_TYPE = "eu.datacellar.vc.type";

    private static final String DEV_UNIRESOLVER_URL = "https://dev.uniresolver.io/1.0/identifiers";

    private static final String DEFAULT_VC_TYPE = "DataCellarCredential";

    @Inject
    private TypeManager typeManager;

    @Override
    public String name() {
        return NAME;
    }

    /**
     * Builds the WaltIDIdentityServices object based on the provided context
     * settings.
     *
     * @param context the ServiceExtensionContext object containing the settings
     * @return the WaltIDIdentityServices object
     * @throws IOException          if an I/O error occurs
     * @throws InterruptedException if the operation is interrupted
     */
    public WaltIDIdentityServices buildIdentityServices(ServiceExtensionContext context)
            throws IOException, InterruptedException {
        String walletUrl = context.getSetting(WALLET_URL, null);
        String walletEmail = context.getSetting(WALLET_EMAIL, null);
        String walletPassword = context.getSetting(WALLET_PASSWORD, null);

        if (walletUrl == null || walletEmail == null || walletPassword == null) {
            throw new IllegalArgumentException(
                    "The following settings are required: %s, %s, %s".formatted(
                            WALLET_URL, WALLET_EMAIL, WALLET_PASSWORD));
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
        String didTrustAnchor = context.getSetting(TRUST_ANCHOR_DID, null);

        if (didTrustAnchor == null) {
            throw new IllegalArgumentException(
                    "The following setting is required: %s".formatted(TRUST_ANCHOR_DID));
        }

        String uniresolverUrl = context.getSetting(UNIVERSAL_RESOLVER_URL, DEV_UNIRESOLVER_URL);
        String vcType = context.getSetting(VC_TYPE, DEFAULT_VC_TYPE);

        var participantId = context.getParticipantId();
        var monitor = context.getMonitor();

        try {
            WaltIDIdentityServices identityServices = buildIdentityServices(context);

            context.registerService(
                    IdentityService.class,
                    new VCIdentityService(
                            monitor,
                            typeManager,
                            participantId,
                            identityServices,
                            didTrustAnchor,
                            uniresolverUrl,
                            vcType));
        } catch (IOException | InterruptedException e) {
            context.getMonitor().severe("Failed to initialize WaltIDIdentityServices", e);
            System.exit(1);
        }
    }

    /**
     * Resolves the audience for the remote message.
     *
     * @return The counter party address of the remote message.
     */
    @Provider
    public AudienceResolver audienceResolver() {
        return RemoteMessage::getCounterPartyAddress;
    }
}