package eu.datacellar.iam;

import java.util.Map;

import org.json.JSONObject;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.JwtParserBuilder;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Jwk;

/**
 * The `CredentialParser` class is responsible for parsing and validating a JWT
 * credential.
 * It provides methods to retrieve the claims from the JWT and extract the
 * Verifiable Credential (VC) from the claims.
 */
public class CredentialParser {
    /**
     * The key used to retrieve the VC (Verifiable Credential) from a JWT (JSON Web
     * Token).
     */
    public static final String JWT_VC_KEY = "vc";

    private static final long CLOCK_SKEW_SECONDS = 300;
    private String jwtCredential;
    private Jwk<?> issuerJwk;

    /**
     * Parses the JWT credential and validates the key type using the provided
     * issuer JWK.
     *
     * @param jwtCredential the JWT credential to parse
     * @param issuerJwk     the JWK of the issuer
     */
    public CredentialParser(String jwtCredential, Jwk<?> issuerJwk) {
        this.jwtCredential = jwtCredential;
        this.issuerJwk = issuerJwk;
    }

    /**
     * Represents the claims extracted from a JSON Web Token (JWT).
     * Claims are key-value pairs that provide information about the JWT.
     * This class provides methods to access and manipulate the claims.
     *
     * @return the claims extracted from the JWT.
     * @throws JwtException if the JWT is invalid or expired.
     */
    public Claims getClaims() throws JwtException {
        JwtParserBuilder jwtParserBuilder = Jwts.parser();

        KeyWrapper issuerJwkWrapper = new KeyWrapper(issuerJwk);

        if (issuerJwkWrapper.isRSA()) {
            jwtParserBuilder.verifyWith(issuerJwkWrapper.getRSAPublicKey());
        } else {
            throw new RuntimeException("Unexpected key type: %s".formatted(issuerJwk.getType()));
        }

        Claims jwtClaims = jwtParserBuilder
                .clockSkewSeconds(CLOCK_SKEW_SECONDS)
                .build()
                .parseSignedClaims(jwtCredential)
                .getPayload();

        if (!jwtClaims.containsKey(JWT_VC_KEY)) {
            throw new IllegalArgumentException(
                    "JWT does not contain a Verifiable Credential (key=%s)".formatted(JWT_VC_KEY));
        }

        return jwtClaims;
    }

    /**
     * Retrieves a JSON object representing a Verifiable Credential (VC) from the
     * provided claims.
     *
     * @param claims The claims containing the Verifiable Credential.
     * @return The JSON object representing the Verifiable Credential.
     */
    public static JSONObject vcJsonObjectFromClaims(Claims claims) {
        @SuppressWarnings("unchecked")
        Map<String, Object> vcMap = (Map<String, Object>) claims.get(JWT_VC_KEY);
        JSONObject vcJsonObject = new JSONObject(vcMap);
        return vcJsonObject;
    }
}
