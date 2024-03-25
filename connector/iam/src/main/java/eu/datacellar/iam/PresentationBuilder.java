package eu.datacellar.iam;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import org.json.JSONArray;
import org.json.JSONObject;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Jwk;
import io.jsonwebtoken.security.Jwks;

/**
 * The PresentationBuilder class is responsible for building verifiable
 * presentations using JSON Web Tokens (JWTs) and JSON Web Keys (JWKs).
 */
public class PresentationBuilder {
    /**
     * The key used to retrieve the "vp" claim from a JWT.
     */
    public static final String JWT_VP_KEY = "vp";

    private List<String> jwtCredentials = new ArrayList<>();
    private Jwk<?> credentialsIssuerJwk;
    private int presentationExpirationSeconds = 300;
    private String audience = null;
    private WaltIDIdentityServices identityServices;

    /**
     * Constructs a new PresentationBuilder object.
     *
     * @param credentialsIssuerJwk the Jwk representing the credentials issuer
     * @param identityServices     the WaltIDIdentityServices object for identity
     *                             services
     */
    public PresentationBuilder(Jwk<?> credentialsIssuerJwk, WaltIDIdentityServices identityServices) {
        this.credentialsIssuerJwk = credentialsIssuerJwk;
        this.identityServices = identityServices;
    }

    /**
     * Adds a JWT credential to the presentation.
     * 
     * @param jwtCredential the JWT credential to add
     * @return the PresentationBuilder object
     */
    public PresentationBuilder addJwtCredential(String jwtCredential) {
        this.jwtCredentials.add(jwtCredential);
        return this;
    }

    /**
     * Sets the expiration time for the presentation.
     * 
     * @param presentationExpirationSeconds the expiration time in seconds
     * @return the PresentationBuilder object
     */
    public PresentationBuilder setPresentationExpirationSeconds(int presentationExpirationSeconds) {
        this.presentationExpirationSeconds = presentationExpirationSeconds;
        return this;
    }

    /**
     * Sets the audience for the presentation.
     *
     * @param audience the audience for the presentation
     * @return the PresentationBuilder object
     */
    public PresentationBuilder setAudience(String audience) {
        this.audience = audience;
        return this;
    }

    /**
     * Converts a JWT credential into a set of claims.
     *
     * @param jwtCredential The JWT credential to convert.
     * @return The claims extracted from the JWT credential.
     */
    public Claims jwtCredentialToClaims(String jwtCredential) {
        return new CredentialParser(jwtCredential, credentialsIssuerJwk).getClaims();
    }

    /**
     * Retrieves the credential subject from a JWT credential.
     *
     * @param jwtCredential the JWT credential
     * @return the credential subject as a String
     */
    public String getCredentialSubject(String jwtCredential) {
        return jwtCredentialToClaims(jwtCredential).getSubject();
    }

    /**
     * Returns the holder DID (Decentralized Identifier) associated with the
     * presentation.
     *
     * @return The holder DID as a string.
     * @throws IllegalArgumentException if the credential subjects in the
     *                                  presentation are not the same.
     */
    public String getHolderDid() {
        Set<String> holderDidSet = jwtCredentials.stream()
                .map(this::getCredentialSubject)
                .collect(Collectors.toSet());

        if (holderDidSet.size() != 1) {
            throw new IllegalArgumentException(
                    "All the credential subjects in the presentation must be the same");
        }

        return holderDidSet.iterator().next();
    }

    /**
     * Retrieves the JWK (JSON Web Key) for the holder.
     *
     * @return The JWK for the holder.
     * @throws IOException If an I/O error occurs while retrieving the JWK.
     */
    public Jwk<?> getHolderJwk() throws IOException {
        JSONObject holderJwkJsonObj = identityServices.getKeyAsJWK(getHolderDid());
        return Jwks.parser().build().parse(holderJwkJsonObj.toString());
    }

    private Map<String, ?> buildPresentationClaims() {
        JSONObject jsonObject = new JSONObject();

        JSONArray contextArray = new JSONArray();
        contextArray.put("https://www.w3.org/2018/credentials/v1");
        jsonObject.put("@context", contextArray);

        JSONArray typeArray = new JSONArray();
        typeArray.put("VerifiablePresentation");
        jsonObject.put("type", typeArray);

        jsonObject.put("id", "urn:uuid:%s".formatted(UUID.randomUUID().toString()));
        jsonObject.put("holder", getHolderDid());

        JSONArray verifiableCredentialArray = new JSONArray();
        verifiableCredentialArray.putAll(jwtCredentials);
        jsonObject.put("verifiableCredential", verifiableCredentialArray);

        return jsonObject.toMap();
    }

    /**
     * Builds a presentation as a JSON Web Token (JWT) string.
     *
     * @return The JWT string representing the built presentation.
     * @throws IOException If an I/O error occurs while building the presentation.
     */
    public String buildPresentationJwt() throws IOException {
        Jwk<?> holderJwk = getHolderJwk();
        String holderDid = getHolderDid();
        Instant now = Instant.now();
        Instant expiration = now.plus(Duration.ofSeconds(presentationExpirationSeconds));
        KeyWrapper holderJwkWrapper = new KeyWrapper(holderJwk);

        return Jwts.builder()
                .header().keyId(holderDid).and()
                .audience().add(audience).and()
                .issuer(holderDid)
                .subject(holderDid)
                .issuedAt(Date.from(now))
                .expiration(Date.from(expiration))
                .id(UUID.randomUUID().toString())
                .claim(JWT_VP_KEY, buildPresentationClaims())
                .signWith(holderJwkWrapper.getRSAPrivateKey())
                .compact();
    }
}