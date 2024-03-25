package eu.datacellar.iam;

import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.util.Arrays;
import java.util.List;

import io.jsonwebtoken.security.Jwk;
import io.jsonwebtoken.security.RsaPrivateJwk;
import io.jsonwebtoken.security.RsaPublicJwk;

/**
 * The KeyWrapper class represents a wrapper for a Jwk object, providing utility
 * methods to work with RSA keys.
 */
public class KeyWrapper {
    /**
     * Represents the key type for RSA encryption.
     */
    public static final String KTY_RSA = "RSA";

    private Jwk<?> jwk;

    /**
     * Constructs a new KeyWrapper object with the provided Jwk.
     * 
     * @param jwk the Jwk object to be wrapped
     */
    public KeyWrapper(Jwk<?> jwk) {
        this.jwk = jwk;
        validateKeyType();
    }

    private void validateKeyType() {
        List<String> supportedKeyTypes = Arrays.asList(KTY_RSA);

        if (!supportedKeyTypes.contains(jwk.getType())) {
            String errMsg = "Key type '%s' is not supported".formatted(jwk.getType());
            throw new IllegalArgumentException(errMsg);
        }
    }

    /**
     * Returns the Jwk object associated with this KeyWrapper.
     *
     * @return the Jwk object
     */
    public Jwk<?> getJwk() {
        return jwk;
    }

    /**
     * Checks if the key type is RSA.
     *
     * @return true if the key type is RSA, false otherwise.
     */
    public boolean isRSA() {
        return jwk.getType().equalsIgnoreCase(KTY_RSA);
    }

    /**
     * Retrieves the RSA public key from the KeyWrapper.
     *
     * @return The RSA public key.
     * @throws IllegalArgumentException if the key type is not RSA.
     */
    public RSAPublicKey getRSAPublicKey() {
        if (!jwk.getType().equalsIgnoreCase(KTY_RSA)) {
            throw new IllegalArgumentException(
                    "Expected RSA public key, got: '%s' instead.".formatted(jwk.getType()));
        }

        RsaPublicJwk rsaPublicJwk = (RsaPublicJwk) jwk;
        RSAPublicKey rsaPublicKey = rsaPublicJwk.toKey();

        return rsaPublicKey;
    }

    /**
     * Retrieves the RSA private key.
     *
     * @return The RSA private key.
     * @throws IllegalArgumentException if the key type is not RSA.
     */
    public RSAPrivateKey getRSAPrivateKey() {
        if (!jwk.getType().equalsIgnoreCase(KTY_RSA)) {
            throw new IllegalArgumentException(
                    "Expected RSA public key, got: '%s' instead.".formatted(jwk.getType()));
        }

        RsaPrivateJwk rsaPrivateJwk = (RsaPrivateJwk) jwk;
        RSAPrivateKey rsaPrivateKey = rsaPrivateJwk.toKeyPair().getPrivate();

        return rsaPrivateKey;
    }
}
