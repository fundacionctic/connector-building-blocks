package eu.datacellar.iam;

import java.io.IOException;

import org.eclipse.edc.spi.iam.ClaimToken;
import org.eclipse.edc.spi.iam.IdentityService;
import org.eclipse.edc.spi.iam.TokenParameters;
import org.eclipse.edc.spi.iam.TokenRepresentation;
import org.eclipse.edc.spi.iam.VerificationContext;
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
    // This is the type of Verifiable Credential that the connector will search for
    // in the wallet and then present to the counter-party.
    private final String presentedVcType;

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
     * @param presentedVcType  The type of Verifiable Credential to present.
     */
    public VCIdentityService(Monitor monitor, TypeManager typeManager, String clientId,
            WaltIDIdentityServices identityServices, String didTrustAnchor, String uniresolverUrl, String presentedVcType) {
        this.monitor = monitor;
        this.typeManager = typeManager;
        this.clientId = clientId;
        this.identityServices = identityServices;
        this.didTrustAnchor = didTrustAnchor;
        this.keyResolver = new KeyResolver(uniresolverUrl, monitor);
        this.presentedVcType = presentedVcType;
    }

    @Override
    public Result<TokenRepresentation> obtainClientCredentials(TokenParameters parameters) {
        String audience = parameters.getStringClaim("aud");

        monitor.info(
                String.format("obtainClientCredentials: (audience=%s)", audience));

        PresentationDefinition presentationDefinition = new PresentationDefinition(presentedVcType);
        MatchCredentialsResponse matchCredentialsResponse;

        try {
            matchCredentialsResponse = identityServices
                    .matchCredentials(presentationDefinition);
        } catch (IOException e) {
            String errMsg = "Failed to match credentials: %s".formatted(e.getMessage());
            monitor.warning(errMsg);
            return Result.failure(errMsg);
        }

        String jwtEncodedVC = matchCredentialsResponse.getLatestActiveAsJWT();
        monitor.debug("JWT-encoded Verifiable Credentials: %s".formatted(jwtEncodedVC));

        if (jwtEncodedVC == null) {
            String errMsg = "No active credentials found";
            monitor.warning(errMsg);
            return Result.failure(errMsg);
        }

        Jwk<?> anchorJwk;

        try {
            anchorJwk = keyResolver.resolveDIDToPublicKeyJWK(didTrustAnchor);
        } catch (IOException e) {
            String errMsg = "Failed to resolve DID trust anchor: %s".formatted(e.getMessage());
            monitor.warning(errMsg);
            return Result.failure(errMsg);
        }

        PresentationBuilder presentationBuilder = new PresentationBuilder(anchorJwk, identityServices);
        presentationBuilder.addJwtCredential(jwtEncodedVC).setAudience(audience);

        String jwtEncodedVP;

        try {
            jwtEncodedVP = presentationBuilder.buildPresentationJwt();
        } catch (IOException e) {
            String errMsg = "Failed to build presentation: %s".formatted(e.getMessage());
            monitor.warning(errMsg);
            return Result.failure(errMsg);
        }

        var token = new VerifiablePresentationToken();
        token.setAudience(audience);
        token.setClientId(clientId);
        token.setJwtVerifiablePresentation(jwtEncodedVP);
        token.setClientDid(presentationBuilder.getHolderDid());

        TokenRepresentation tokenRepresentation = TokenRepresentation.Builder.newInstance()
                .token(typeManager.writeValueAsString(token))
                .build();

        monitor.debug("TokenRepresentation: %s".formatted(tokenRepresentation.getToken()));

        return Result.success(tokenRepresentation);
    }

    @Override
    public Result<ClaimToken> verifyJwtToken(TokenRepresentation tokenRepresentation, VerificationContext context) {
        monitor.debug("verifyJwtToken.tokenRepresentation: %s".formatted(tokenRepresentation.getToken()));

        var token = typeManager.readValue(tokenRepresentation.getToken(), VerifiablePresentationToken.class);

        Jwk<?> anchorJwk;

        try {
            anchorJwk = keyResolver.resolveDIDToPublicKeyJWK(didTrustAnchor);
        } catch (IOException e) {
            return Result.failure("Failed to resolve trust anchor DID: %s".formatted(e.getMessage()));
        }

        Jwk<?> counterPartyJwk;

        try {
            counterPartyJwk = keyResolver.resolveDIDToPublicKeyJWK(token.clientDid);
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

        JSONObject vpJsonObject = presentationParser.toJsonObject();
        String vpJsonString = vpJsonObject.toString();
        monitor.debug("Counter-party VP JSON: %s".formatted(vpJsonString));

        return Result.success(ClaimToken.Builder.newInstance()
                .claim("region", token.region)
                .claim("client_id", token.clientId)
                .claim("client_did", token.clientDid)
                .claim("vp", vpJsonString)
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

        @SuppressWarnings("unused")
        public String getClientDid() {
            return clientDid;
        }

        public void setClientDid(String clientDid) {
            this.clientDid = clientDid;
        }
    }
}