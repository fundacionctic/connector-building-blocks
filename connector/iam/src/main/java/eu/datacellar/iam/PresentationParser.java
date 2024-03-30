package eu.datacellar.iam;

import java.util.Map;

import org.json.JSONArray;
import org.json.JSONObject;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Jwk;

/**
 * The PresentationParser class is responsible for parsing and validating JSON
 * Web Token (JWT) presentations.
 * It provides methods to retrieve claims from the presentation, convert claims
 * into a JSONObject, and validate the presentation's structure and credentials.
 */
public class PresentationParser {
    private static final String JWT_VP_KEY = "vp";
    private static final String JWT_VP_VC_KEY = "verifiableCredential";
    private static final long CLOCK_SKEW_SECONDS = 300;
    private String jwtPresentation;
    private Jwk<?> issuerJwk;
    private Jwk<?> holderJwk;

    /**
     * Constructs a new PresentationParser object with the specified parameters.
     *
     * @param jwtPresentation the JWT presentation string to be parsed
     * @param issuerJwk       the JWK of the issuer
     * @param holderJwk       the JWK of the holder
     */
    public PresentationParser(String jwtPresentation, Jwk<?> issuerJwk, Jwk<?> holderJwk) {
        this.jwtPresentation = jwtPresentation;
        this.issuerJwk = issuerJwk;
        this.holderJwk = holderJwk;
        validateKeys();
    }

    private void validateKeys() {
        KeyWrapper holderJwkWrapper = new KeyWrapper(holderJwk);

        if (!holderJwkWrapper.isRSA()) {
            throw new IllegalArgumentException("Unexpected key type: %s".formatted(holderJwk.getType()));
        }

        KeyWrapper issuerJwkWrapper = new KeyWrapper(issuerJwk);

        if (!issuerJwkWrapper.isRSA()) {
            throw new IllegalArgumentException("Unexpected key type: %s".formatted(issuerJwk.getType()));
        }
    }

    /**
     * Retrieves the claims from the JSON Web Token (JWT) presentation.
     *
     * @return The claims extracted from the JWT presentation.
     * @throws JwtException If an error occurs while parsing or verifying the JWT.
     */
    public Claims getClaims() throws JwtException {
        KeyWrapper holderJwkWrapper = new KeyWrapper(holderJwk);

        Claims jwtClaims = Jwts.parser()
                .verifyWith(holderJwkWrapper.getRSAPublicKey())
                .clockSkewSeconds(CLOCK_SKEW_SECONDS)
                .build()
                .parseSignedClaims(jwtPresentation)
                .getPayload();

        return jwtClaims;
    }

    /**
     * Converts the claims of a Verifiable Presentation (VP) into a JSONObject.
     * 
     * @param vpClaims the claims of the Verifiable Presentation
     * @return a JSONObject representation of the Verifiable Presentation
     */
    public static JSONObject vpJsonObjectFromClaims(Claims vpClaims) {
        @SuppressWarnings("unchecked")
        Map<String, Object> vpMap = (Map<String, Object>) vpClaims.get(JWT_VP_KEY);
        JSONObject vpJsonObject = new JSONObject(vpMap);
        return vpJsonObject;
    }

    private void validatePresentationSchema(Claims vpClaims) {
        if (vpClaims.getSubject() == null) {
            throw new PresentationException("Missing subject claim in VP JWT");
        }

        if (vpClaims.getIssuer() == null) {
            throw new PresentationException("Missing issuer claim in VP JWT");
        }

        if (!vpClaims.containsKey(JWT_VP_KEY)) {
            throw new PresentationException(
                    "VP JWT does not contain the VP key (%s)".formatted(JWT_VP_KEY));
        }
    }

    private void validateCredential(String jwtCredential, String vpIssuer) {
        CredentialParser credentialParser = new CredentialParser(jwtCredential, issuerJwk);

        Claims vcClaims;

        try {
            vcClaims = credentialParser.getClaims();
        } catch (JwtException e) {
            throw new PresentationException("Failed to parse VC JWT: %s".formatted(e.getMessage()));
        }

        if (!vcClaims.getSubject().equals(vpIssuer)) {
            throw new PresentationException("VC subject is not the VP issuer");
        }
    }

    private void validateCredentialsSignatureAndSubject(Claims vpClaims) {
        JSONObject vpJsonObject = vpJsonObjectFromClaims(vpClaims);

        if (!vpJsonObject.has(JWT_VP_VC_KEY)) {
            throw new PresentationException(
                    "VP JWT does not contain the VCs key (%s)".formatted(JWT_VP_VC_KEY));
        }

        JSONArray jwtCredentials = vpJsonObject.getJSONArray(JWT_VP_VC_KEY);

        for (int i = 0; i < jwtCredentials.length(); i++) {
            String jwtCredential = jwtCredentials.getString(i);
            validateCredential(jwtCredential, vpClaims.getIssuer());
        }
    }

    private void validatePresentationHolderIsIssuer(Claims vpClaims) {
        if (!vpClaims.getIssuer().equals(vpClaims.getSubject())) {
            throw new PresentationException("VP subject is not the VP issuer");
        }

        JSONObject vpJsonObject = vpJsonObjectFromClaims(vpClaims);
        String vpHolder = vpJsonObject.getString("holder");

        if (!vpClaims.getIssuer().equals(vpHolder)) {
            throw new PresentationException("VP holder is not the VP issuer");
        }
    }

    /**
     * Validates the presentation by performing the following checks:
     * 1. Validates the presentation schema.
     * 2. Validates that the presentation holder is the issuer.
     * 3. Validates the credentials signature and subject.
     *
     * @throws PresentationException if the presentation is invalid.
     * @throws JwtException          if there is an error with the JWT.
     */
    public void validate() throws PresentationException, JwtException {
        Claims vpClaims = getClaims();
        validatePresentationSchema(vpClaims);
        validatePresentationHolderIsIssuer(vpClaims);
        validateCredentialsSignatureAndSubject(vpClaims);
    }

    /**
     * Converts the Verifiable Presentation (VP) into a JSONObject.
     *
     * @return a JSONObject representation of the Verifiable Presentation.
     */
    public JSONObject toJsonObject() {
        JSONObject vpJsonObject = vpJsonObjectFromClaims(getClaims());
        JSONArray vcsJwt = vpJsonObject.getJSONArray(JWT_VP_VC_KEY);
        JSONArray vcs = new JSONArray();

        for (int i = 0; i < vcsJwt.length(); i++) {
            String jwtCredential = vcsJwt.getString(i);
            CredentialParser credParser = new CredentialParser(jwtCredential, issuerJwk);
            Claims vcClaims = credParser.getClaims();
            JSONObject vcJsonObject = CredentialParser.vcJsonObjectFromClaims(vcClaims);
            vcs.put(vcJsonObject);
        }

        vpJsonObject.put(JWT_VP_VC_KEY, vcs);

        return vpJsonObject;
    }

    /**
     * Represents an exception that occurs during the presentation parsing process.
     */
    public static class PresentationException extends RuntimeException {
        /**
         * Constructs a new PresentationException with the specified detail message.
         *
         * @param message the detail message
         */
        public PresentationException(String message) {
            super(message);
        }
    }
}
