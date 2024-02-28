package eu.datacellar.iam;

import static java.lang.String.format;

import java.util.Objects;

import org.eclipse.edc.spi.iam.ClaimToken;
import org.eclipse.edc.spi.iam.IdentityService;
import org.eclipse.edc.spi.iam.TokenParameters;
import org.eclipse.edc.spi.iam.TokenRepresentation;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.result.Result;
import org.eclipse.edc.spi.types.TypeManager;

/**
 * This class represents a VCIdentityService that implements the IdentityService
 * interface.
 * It provides methods for obtaining client credentials and verifying JWT
 * tokens.
 */
public class VCIdentityService implements IdentityService {
    private final Monitor monitor;
    private final TypeManager typeManager;
    private final String clientId;
    private final WaltIDIdentityServices identityServices;

    public VCIdentityService(Monitor monitor, TypeManager typeManager, String clientId,
            WaltIDIdentityServices identityServices) {
        this.monitor = monitor;
        this.typeManager = typeManager;
        this.clientId = clientId;
        this.identityServices = identityServices;
    }

    @Override
    public Result<TokenRepresentation> obtainClientCredentials(TokenParameters parameters) {
        monitor.warning(
                String.format("obtainClientCredentials: (scope=%s) (audience=%s)",
                        parameters.getScope(),
                        parameters.getAudience()));

        var token = new MockToken();
        token.setAudience(parameters.getAudience());
        token.setClientId(clientId);

        TokenRepresentation tokenRepresentation = TokenRepresentation.Builder.newInstance()
                .token(typeManager.writeValueAsString(token))
                .build();

        return Result.success(tokenRepresentation);
    }

    @Override
    public Result<ClaimToken> verifyJwtToken(TokenRepresentation tokenRepresentation, String audience) {
        monitor.warning(String.format("verifyJwtToken: %s", tokenRepresentation.getToken()));

        var token = typeManager.readValue(tokenRepresentation.getToken(), MockToken.class);

        if (!Objects.equals(token.audience, audience)) {
            return Result.failure(format("Mismatched audience: expected %s, got %s", audience, token.audience));
        }

        return Result.success(ClaimToken.Builder.newInstance()
                .claim("region", token.region)
                .claim("client_id", token.clientId)
                .build());
    }

    private static class MockToken {
        private String region = "eu";
        private String audience;
        private String clientId;
        private static final String AUTHOR = "CTIC";

        public String getAuthor() {
            return AUTHOR;
        }

        public String getAudience() {
            return audience;
        }

        public void setAudience(String audience) {
            this.audience = audience;
        }

        public String getRegion() {
            return region;
        }

        public void setRegion(String region) {
            this.region = region;
        }

        public String getClientId() {
            return clientId;
        }

        public void setClientId(String clientId) {
            this.clientId = clientId;
        }
    }
}