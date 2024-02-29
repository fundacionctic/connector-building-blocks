package eu.datacellar.iam;

import static java.lang.String.format;

import java.io.IOException;
import java.security.interfaces.RSAPublicKey;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
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
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.JwtParserBuilder;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Jwk;
import io.jsonwebtoken.security.Jwks;
import io.jsonwebtoken.security.RsaPublicJwk;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

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
    private final String uniresolverUrl;

    private static final String KTY_RSA = "RSA";
    private static final String JWT_VC_KEY = "vc";

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
        this.uniresolverUrl = uniresolverUrl;
    }

    private JSONObject resolveTrustAnchorDIDToJson() throws IOException {
        if (!didTrustAnchor.startsWith("did:web:")) {
            throw new IllegalArgumentException("Only did:web is supported: " + didTrustAnchor);
        }

        String urlDID = "%s/%s".formatted(uniresolverUrl.replaceAll("/+$", ""), didTrustAnchor);

        OkHttpClient client = new OkHttpClient();

        Request request = new Request.Builder()
                .url(urlDID)
                .header("Accept", "application/did+json")
                .get()
                .build();

        Response response = client.newCall(request).execute();

        if (!response.isSuccessful()) {
            throw new RuntimeException(
                    String.format("HTTP request to resolve DID failed with status code: %s", response.code()));
        }

        String responseBody = response.body().string();
        monitor.debug("Raw response: " + responseBody);
        JSONObject didJsonObj = new JSONObject(responseBody);

        return didJsonObj;
    }

    private Jwk<?> resolveTrustAnchorDIDToPublicKeyJWK() throws IOException {
        JSONObject didJsonObj = resolveTrustAnchorDIDToJson();

        return Jwks.parser().build().parse(didJsonObj
                .getJSONArray("verificationMethod")
                .getJSONObject(0)
                .getJSONObject("publicKeyJwk")
                .toString());
    }

    private RSAPublicKey getRSAPublicKeyFromJWK(Jwk<?> jwk) {
        if (!jwk.getType().equalsIgnoreCase(KTY_RSA)) {
            throw new IllegalArgumentException("Expected RSA public key, got: '%s' instead.".formatted(jwk.getType()));
        }

        RsaPublicJwk rsaPublicJwk = (RsaPublicJwk) jwk;
        RSAPublicKey rsaPublicKey = rsaPublicJwk.toKey();

        return rsaPublicKey;
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
        token.setVcAsJwt(jwtEncodedVC);

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

        Jwk<?> anchorJwk;

        try {
            anchorJwk = resolveTrustAnchorDIDToPublicKeyJWK();
        } catch (IOException e) {
            return Result.failure("Failed to resolve DID trust anchor: %s".formatted(e.getMessage()));
        }

        List<String> supportedKeyTypes = Arrays.asList(KTY_RSA);
        String keyTypeErrorMsg = "Key type '%s' is not supported".formatted(anchorJwk.getType());

        if (!supportedKeyTypes.contains(anchorJwk.getType())) {
            return Result.failure(keyTypeErrorMsg);
        }

        Claims jwtClaims;

        try {
            JwtParserBuilder jwtParserBuilder = Jwts.parser();

            if (anchorJwk.getType().equalsIgnoreCase(KTY_RSA)) {
                jwtParserBuilder.verifyWith(getRSAPublicKeyFromJWK(anchorJwk));
            } else {
                return Result.failure(keyTypeErrorMsg);
            }

            jwtClaims = jwtParserBuilder
                    .build()
                    .parseSignedClaims(token.getVcAsJwt())
                    .getPayload();
        } catch (JwtException e) {
            return Result.failure("JWT exception: %s".formatted(e.getMessage()));
        }

        if (!jwtClaims.containsKey(JWT_VC_KEY)) {
            return Result.failure(
                    "JWT does not contain a Verifiable Credential (key=%s)".formatted(JWT_VC_KEY));
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> vcMap = (Map<String, Object>) jwtClaims.get(JWT_VC_KEY);
        JSONObject vcJsonObject = new JSONObject(vcMap);
        String vcJsonString = vcJsonObject.toString();

        monitor.debug("JSON-encoded counter-party Verifiable Credential: %s".formatted(vcJsonString));

        return Result.success(ClaimToken.Builder.newInstance()
                .claim("region", token.region)
                .claim("client_id", token.clientId)
                .claim("sub", jwtClaims.getSubject())
                .claim("iss", jwtClaims.getIssuer())
                .claim("exp", jwtClaims.getExpiration().getTime())
                .claim("iat", jwtClaims.getIssuedAt().getTime())
                .claim("nbf", jwtClaims.getNotBefore().getTime())
                .claim("vc", vcJsonString)
                .build());
    }

    private static class VerifiableCredentialsToken {
        private String region = "eu";
        private String audience;
        private String clientId;
        private String vcAsJwt;

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

        public String getVcAsJwt() {
            return vcAsJwt;
        }

        public void setVcAsJwt(String vcAsJwt) {
            this.vcAsJwt = vcAsJwt;
        }
    }
}