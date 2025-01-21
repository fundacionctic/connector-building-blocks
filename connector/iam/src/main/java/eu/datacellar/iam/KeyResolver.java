package eu.datacellar.iam;

import java.io.IOException;
import java.util.Map;

import org.eclipse.edc.spi.monitor.Monitor;
import org.json.JSONObject;

import io.jsonwebtoken.security.Jwk;
import io.jsonwebtoken.security.Jwks;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

/**
 * The KeyResolver class is responsible for resolving Decentralized Identifiers
 * (DIDs) to their corresponding JSON objects
 * and public key representations.
 */
public class KeyResolver {
    private static final String ACCEPT_DID_LD_JSON = "application/ld+json";
    private static final long DID_CACHE_TTL_SECONDS = 60 * 5;
    private final String uniresolverUrl;
    private final Monitor monitor;
    private final Map<String, DIDCacheEntry> didCache = new java.util.HashMap<>();

    /**
     * Constructs a new KeyResolver with the specified uniresolver URL and monitor.
     *
     * @param uniresolverUrl the URL of the uniresolver
     * @param monitor        the monitor to track the resolver's activity
     */
    public KeyResolver(String uniresolverUrl, Monitor monitor) {
        this.uniresolverUrl = uniresolverUrl;
        this.monitor = monitor;
    }

    /**
     * Resolves a DID (Decentralized Identifier) to a JSON object.
     *
     * @param theDid the DID to resolve.
     * @return the JSON object representing the DID document.
     * @throws IOException if an I/O error occurs while resolving the DID.
     */
    public JSONObject resolveDIDToJson(String theDid) throws IOException {
        if (!theDid.startsWith("did:web:")) {
            throw new IllegalArgumentException("Only did:web is supported: " + theDid);
        }

        if (didCache.containsKey(theDid)) {
            DIDCacheEntry cacheEntry = didCache.get(theDid);

            if (!cacheEntry.isExpired()) {
                monitor.debug("Using cached DID document: %s".formatted(theDid));
                return cacheEntry.getDidJson();
            } else {
                monitor.debug("Cached DID document expired: %s".formatted(theDid));
            }
        }

        String urlDID = "%s/%s".formatted(uniresolverUrl.replaceAll("/+$", ""), theDid);

        OkHttpClient client = new OkHttpClient();

        Request request = new Request.Builder()
                .url(urlDID)
                .header("Accept", ACCEPT_DID_LD_JSON)
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

        if (didCache.containsKey(theDid)) {
            didCache.remove(theDid);
        }

        didCache.put(theDid, new DIDCacheEntry(didJsonObj, System.currentTimeMillis()));

        return didJsonObj;
    }

    /**
     * Resolves a DID (Decentralized Identifier) to a public key JWK (JSON Web Key).
     *
     * @param theDid the DID to resolve
     * @return the JWK representing the public key
     * @throws IOException if an I/O error occurs while resolving the DID
     */
    public Jwk<?> resolveDIDToPublicKeyJWK(String theDid) throws IOException {
        JSONObject didJsonObj = resolveDIDToJson(theDid);

        return Jwks.parser().build().parse(didJsonObj
                .getJSONArray("verificationMethod")
                .getJSONObject(0)
                .getJSONObject("publicKeyJwk")
                .toString());
    }

    private static class DIDCacheEntry {
        private JSONObject didJson;
        private long timestamp;

        public DIDCacheEntry(JSONObject didJson, long timestamp) {
            this.didJson = didJson;
            this.timestamp = timestamp;
        }

        public JSONObject getDidJson() {
            return didJson;
        }

        public boolean isExpired(long now) {
            return (now - timestamp) > (DID_CACHE_TTL_SECONDS * 1000);
        }

        public boolean isExpired() {
            return isExpired(System.currentTimeMillis());
        }
    }
}
