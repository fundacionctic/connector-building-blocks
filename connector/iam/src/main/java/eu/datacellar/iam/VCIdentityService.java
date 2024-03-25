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
import org.json.JSONObject;

import eu.datacellar.iam.WaltIDIdentityServices.MatchCredentialsResponse;
import eu.datacellar.iam.WaltIDIdentityServices.PresentationDefinition;
import io.jsonwebtoken.security.Jwk;

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
    private final String didTrustAnchor;
    private final KeyResolver keyResolver;

    /**
     * This class represents a VCIdentityService, which is responsible for managing
     * verifiable credentials and identities.
     *
     * @param monitor          The monitor for logging and monitoring purposes.
     * @param typeManager      The type manager for managing credential types.
     * @param clientId         The client ID for authentication purposes.
     * @param identityServices The identity services for interacting with identity
     *                         providers.
     * @param didTrustAnchor   The trust anchor for decentralized identifiers.
     * @param uniresolverUrl   The URL of the uniresolver service.
     */
    public VCIdentityService(Monitor monitor, TypeManager typeManager, String clientId,
            WaltIDIdentityServices identityServices, String didTrustAnchor, String uniresolverUrl) {
        this.monitor = monitor;
        this.typeManager = typeManager;
        this.clientId = clientId;
        this.identityServices = identityServices;
        this.didTrustAnchor = didTrustAnchor;
        this.keyResolver = new KeyResolver(uniresolverUrl, monitor);
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
            // ToDo: Refine the presentation definition
            matchCredentialsResponse = identityServices
                    .matchCredentials(presentationDefinition);
        } catch (IOException e) {
            return Result.failure("Failed to match credentials: %s".formatted(e.getMessage()));
        }

        String jwtEncodedVC = matchCredentialsResponse.getMostRecentJWTEncoded();
        monitor.debug("JWT-encoded Verifiable Credential: %s".formatted(jwtEncodedVC));

        Jwk<?> anchorJwk;

        try {
            anchorJwk = keyResolver.resolveDIDToPublicKeyJWK(didTrustAnchor);
        } catch (IOException e) {
            return Result.failure("Failed to resolve DID trust anchor: %s".formatted(e.getMessage()));
        }

        PresentationBuilder presentationBuilder = new PresentationBuilder(anchorJwk, identityServices);

        presentationBuilder
                .addJwtCredential(jwtEncodedVC)
                .setAudience(parameters.getAudience());

        String jwtEncodedVP;

        try {
            jwtEncodedVP = presentationBuilder.buildPresentationJwt();
        } catch (IOException e) {
            return Result.failure("Failed to build presentation: %s".formatted(e.getMessage()));
        }

        monitor.debug("JWT-encoded Verifiable Presentation: %s".formatted(jwtEncodedVP));

        var token = new VerifiablePresentationToken();
        token.setAudience(parameters.getAudience());
        token.setClientId(clientId);
        token.setJwtVerifiablePresentation(jwtEncodedVP);
        token.setClientDid(presentationBuilder.getHolderDid());

        TokenRepresentation tokenRepresentation = TokenRepresentation.Builder.newInstance()
                .token(typeManager.writeValueAsString(token))
                .build();

        return Result.success(tokenRepresentation);
    }

    @Override
    public Result<ClaimToken> verifyJwtToken(TokenRepresentation tokenRepresentation, String audience) {
        monitor.debug("verifyJwtToken.tokenRepresentation: %s".formatted(tokenRepresentation.getToken()));
        monitor.debug("verifyJwtToken.audience: %s".formatted(audience));

        var token = typeManager.readValue(tokenRepresentation.getToken(), VerifiablePresentationToken.class);

        if (!Objects.equals(token.audience, audience)) {
            return Result.failure(format("Mismatched audience: expected %s, got %s", audience, token.audience));
        }

        Jwk<?> anchorJwk;

        try {
            anchorJwk = keyResolver.resolveDIDToPublicKeyJWK(didTrustAnchor);
        } catch (IOException e) {
            return Result.failure("Failed to resolve trust anchor DID: %s".formatted(e.getMessage()));
        }

        Jwk<?> counterPartyJwk;

        try {
            counterPartyJwk = keyResolver.resolveDIDToPublicKeyJWK(token.getClientDid());
        } catch (IOException e) {
            return Result.failure("Failed to resolve counter-party DID: %s".formatted(e.getMessage()));
        }

        // This VP should fulfill the following conditions:
        // 1. Both the subject and the issuer of this VP should be the same DID.
        // 2. The subjects of all the VC in the VP should be the issuer of the VP.
        // 3. The VC in the VP should be signed by the trust anchor.
        PresentationParser presentationParser = new PresentationParser(
                token.getJwtVerifiablePresentation(),
                anchorJwk,
                counterPartyJwk);

        try {
            presentationParser.validate();
        } catch (Exception e) {
            return Result.failure("Failed to validate presentation: %s".formatted(e.getMessage()));
        }

        JSONObject vpJsonObject = PresentationParser.vpJsonObjectFromClaims(presentationParser.getClaims());
        monitor.debug("Counter-party VP JSON object: %s".formatted(vpJsonObject.toString()));

        // ToDo: Add the claims extracted from the VP to the token
        return Result.success(ClaimToken.Builder.newInstance()
                .claim("region", token.region)
                .claim("client_id", token.clientId)
                // .claim("sub", jwtClaims.getSubject())
                // .claim("iss", jwtClaims.getIssuer())
                // .claim("exp", jwtClaims.getExpiration().getTime())
                // .claim("iat", jwtClaims.getIssuedAt().getTime())
                // .claim("nbf", jwtClaims.getNotBefore().getTime())
                // .claim("vc", vcJsonString)
                .build());
    }

    private static class VerifiablePresentationToken {
        private String region = "eu";
        private String audience;
        private String clientId;
        private String clientDid;
        private String jwtVerifiablePresentation;

        @SuppressWarnings("unused")
        public String getRegion() {
            return region;
        }

        @SuppressWarnings("unused")
        public void setRegion(String region) {
            this.region = region;
        }

        @SuppressWarnings("unused")
        public String getAudience() {
            return audience;
        }

        public void setAudience(String audience) {
            this.audience = audience;
        }

        @SuppressWarnings("unused")
        public String getClientId() {
            return clientId;
        }

        public void setClientId(String clientId) {
            this.clientId = clientId;
        }

        public String getJwtVerifiablePresentation() {
            return jwtVerifiablePresentation;
        }

        public void setJwtVerifiablePresentation(String jwtVP) {
            this.jwtVerifiablePresentation = jwtVP;
        }

        public String getClientDid() {
            return clientDid;
        }

        public void setClientDid(String clientDid) {
            this.clientDid = clientDid;
        }
    }
}