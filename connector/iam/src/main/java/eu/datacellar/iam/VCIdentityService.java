package eu.datacellar.iam;

import static java.lang.String.format;

import java.io.IOException;
import java.util.Objects;

import org.eclipse.edc.spi.iam.ClaimToken;
import org.eclipse.edc.spi.iam.IdentityService;
import org.eclipse.edc.spi.iam.TokenParameters;
import org.eclipse.edc.spi.iam.TokenRepresentation;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.result.Result;
import org.eclipse.edc.spi.types.TypeManager;

import eu.datacellar.iam.WaltIDIdentityServices.MatchCredentialsResponse;
import eu.datacellar.iam.WaltIDIdentityServices.PresentationDefinition;

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

    /**
     * This class represents a VCIdentityService, which is responsible for managing
     * identity services
     * for a specific client.
     *
     * @param monitor          The monitor object used for monitoring the service.
     * @param typeManager      The type manager object used for managing types.
     * @param clientId         The ID of the client.
     * @param identityServices The identity services associated with the client.
     */
    public VCIdentityService(Monitor monitor, TypeManager typeManager, String clientId,
            WaltIDIdentityServices identityServices) {
        this.monitor = monitor;
        this.typeManager = typeManager;
        this.clientId = clientId;
        this.identityServices = identityServices;
    }

    @Override
    public Result<TokenRepresentation> obtainClientCredentials(TokenParameters parameters) {
        monitor.info(
                String.format("obtainClientCredentials: (scope=%s) (audience=%s)",
                        parameters.getScope(),
                        parameters.getAudience()));

        PresentationDefinition presentationDefinition = new PresentationDefinition();
        MatchCredentialsResponse matchCredentialsResponse;

        try {
            matchCredentialsResponse = identityServices
                    .matchCredentials(presentationDefinition);
        } catch (IOException e) {
            monitor.warning("Failed to match credentials", e);
            return Result.failure("Failed to match credentials: " + e.getMessage());
        }

        String jwtEncodedVC = matchCredentialsResponse.getMostRecentJWTEncoded();

        monitor.debug("JWT-encoded Verifiable Credential: %s".formatted(jwtEncodedVC));

        var token = new VerifiableCredentialsToken();
        token.setAudience(parameters.getAudience());
        token.setClientId(clientId);
        token.setJwtEncodedVC(jwtEncodedVC);

        TokenRepresentation tokenRepresentation = TokenRepresentation.Builder.newInstance()
                .token(typeManager.writeValueAsString(token))
                .build();

        return Result.success(tokenRepresentation);
    }

    @Override
    public Result<ClaimToken> verifyJwtToken(TokenRepresentation tokenRepresentation, String audience) {
        monitor.info(String.format("verifyJwtToken: %s", tokenRepresentation.getToken()));

        var token = typeManager.readValue(tokenRepresentation.getToken(), VerifiableCredentialsToken.class);

        if (!Objects.equals(token.audience, audience)) {
            return Result.failure(format("Mismatched audience: expected %s, got %s", audience, token.audience));
        }

        return Result.success(ClaimToken.Builder.newInstance()
                .claim("region", token.region)
                .claim("client_id", token.clientId)
                .build());
    }

    private static class VerifiableCredentialsToken {
        private String region = "eu";
        private String audience;
        private String clientId;
        private String jwtEncodedVC;

        public String getRegion() {
            return region;
        }

        public void setRegion(String region) {
            this.region = region;
        }

        public String getAudience() {
            return audience;
        }

        public void setAudience(String audience) {
            this.audience = audience;
        }

        public String getClientId() {
            return clientId;
        }

        public void setClientId(String clientId) {
            this.clientId = clientId;
        }

        public String getJwtEncodedVC() {
            return jwtEncodedVC;
        }

        public void setJwtEncodedVC(String jwtEncodedVC) {
            this.jwtEncodedVC = jwtEncodedVC;
        }

    }
}