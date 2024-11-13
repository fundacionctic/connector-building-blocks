package eu.datacellar.iam;

import java.io.IOException;
import java.time.ZonedDateTime;
import java.util.Arrays;
import java.util.Base64;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.IntStream;

import org.eclipse.edc.spi.monitor.Monitor;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import okhttp3.HttpUrl;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * The WaltIDIdentityServices class represents a set of services for interacting
 * with the WaltID identity system.
 * It provides methods for finding wallet ID, retrieving wallet token, and
 * matching credentials for a presentation definition.
 */
public class WaltIDIdentityServices {
    private Monitor monitor;
    private String walletUrl;
    private String walletEmail;
    private String walletPassword;
    private String walletId;
    private OkHttpClient client;

    /**
     * Represents the WaltIDIdentityServices class which provides functionality for
     * interacting with WaltID identity services.
     * This class is responsible for initializing the client, monitoring, wallet
     * URL, wallet email, wallet password, and wallet ID.
     *
     * @param monitor        The monitor object used for logging and monitoring.
     * @param walletUrl      The URL of the wallet.
     * @param walletEmail    The email associated with the wallet.
     * @param walletPassword The password for the wallet.
     * @throws IOException If an I/O error occurs while making the request.
     */
    public WaltIDIdentityServices(Monitor monitor, String walletUrl, String walletEmail, String walletPassword)
            throws IOException {
        this.client = buildClient();
        this.monitor = monitor;
        this.walletUrl = walletUrl;
        this.walletEmail = walletEmail;
        this.walletPassword = walletPassword;
        this.walletId = this.findWalletId();
    }

    /**
     * Represents the WaltIDIdentityServices class which provides functionality for
     * interacting with WaltID identity services.
     *
     * @param monitor        The monitor object used for logging and monitoring.
     * @param walletUrl      The URL of the wallet.
     * @param walletEmail    The email associated with the wallet.
     * @param walletPassword The password for the wallet.
     * @param walletId       The ID of the wallet.
     */
    public WaltIDIdentityServices(Monitor monitor, String walletUrl, String walletEmail, String walletPassword,
            String walletId) {
        this.client = buildClient();
        this.monitor = monitor;
        this.walletUrl = walletUrl;
        this.walletEmail = walletEmail;
        this.walletPassword = walletPassword;
        this.walletId = walletId;
    }

    private OkHttpClient buildClient() {
        return new OkHttpClient();
    }

    private String findWalletId() throws IOException {
        monitor.info("Finding wallet ID for wallet with email: " + this.walletEmail + " and URL: " + this.walletUrl);

        String url = this.walletUrl + "/wallet-api/wallet/accounts/wallets";
        String token = getWalletToken();

        monitor.debug(String.format("GET %s", url));

        Request request = new Request.Builder()
                .url(url)
                .get()
                .addHeader("Authorization", String.format("Bearer %s", token))
                .addHeader("Cache-Control", "no-cache")
                .addHeader("Accept", "*/*")
                .build();

        Response response = client.newCall(request).execute();

        if (!response.isSuccessful()) {
            monitor.warning("Failed to find wallet ID. HTTP request failed with status code: " + response.code());

            throw new RuntimeException(
                    String.format(
                            "HTTP request to find Wallet ID failed with status code: %s",
                            response.code()));
        }

        String responseBody = response.body().string();
        monitor.debug("Raw response: " + responseBody);

        JSONObject obj = new JSONObject(responseBody);

        String walletId = obj.getJSONArray("wallets").getJSONObject(0).getString("id");
        monitor.info("Found wallet ID: " + walletId);

        return walletId;
    }

    /**
     * Retrieves the wallet token for the specified wallet.
     *
     * @return The wallet token as a String.
     * @throws IOException If an I/O error occurs while making the request.
     */
    public String getWalletToken() throws IOException {
        monitor.debug(
                "Getting wallet token for wallet with email: " + this.walletEmail + " and URL: " + this.walletUrl);

        String url = this.walletUrl + "/wallet-api/auth/login";

        String json = new JSONObject()
                .put("type", "email")
                .put("email", this.walletEmail)
                .put("password", this.walletPassword)
                .toString();

        RequestBody body = RequestBody.create(json, MediaType.parse("application/json; charset=utf-8"));

        monitor.debug(String.format("POST %s", url));

        Request request = new Request.Builder()
                .url(url)
                .post(body)
                .addHeader("Content-Type", "application/json")
                .build();

        Response response = client.newCall(request).execute();

        if (!response.isSuccessful()) {
            throw new RuntimeException(
                    String.format(
                            "HTTP request to get Wallet token failed with status code: %s",
                            response.code()));
        }

        String responseBody = response.body().string();
        monitor.debug("Raw response: " + responseBody);

        JSONObject obj = new JSONObject(responseBody);
        String token = obj.getString("token");

        monitor.debug("Got wallet token: " + token);

        return token;
    }

    /**
     * Retrieves the key as a JWK (JSON Web Key) for the specified DID holder.
     *
     * @param didHolder The DID holder to retrieve the key for.
     * @return The key in JWK format.
     * @throws IOException If an I/O error occurs while making the request.
     */
    public JSONObject getKeyAsJWK(String didHolder) throws IOException {
        String token = getWalletToken();

        String keyId = null;

        if (didHolder.contains("#")) {
            String[] parts = didHolder.split("#");
            keyId = parts[parts.length - 1];
            monitor.debug("Key ID is already contained in DID: %s".formatted(didHolder));
        }

        if (keyId == null) {
            String urlListDids = walletUrl + "/wallet-api/wallet/" + walletId + "/dids";

            Request reqListDids = new Request.Builder()
                    .url(urlListDids)
                    .get()
                    .addHeader("Authorization", String.format("Bearer %s", token))
                    .build();

            monitor.debug("Looking for DID: %s".formatted(didHolder));

            Response resListDids = client.newCall(reqListDids).execute();

            if (!resListDids.isSuccessful()) {
                String errMsg = "HTTP request to export key failed with status code: %s".formatted(resListDids.code());
                monitor.warning(errMsg);
                throw new RuntimeException(errMsg);
            }

            String resBodyListDids = resListDids.body().string();
            monitor.debug("List DIDs raw response: %s".formatted(resBodyListDids));
            JSONArray didsArr = new JSONArray(resBodyListDids);

            Optional<JSONObject> latestObject = IntStream.range(0, didsArr.length())
                    .mapToObj(didsArr::getJSONObject)
                    .filter(obj -> obj.getString("did").equals(didHolder))
                    .max(Comparator.comparing(obj -> ZonedDateTime.parse(obj.getString("createdOn"))));

            if (!latestObject.isPresent()) {
                String errMsg = "DID not found: %s".formatted(didHolder);
                monitor.warning(errMsg);
                throw new RuntimeException(errMsg);
            }

            JSONObject selectedDid = latestObject.get();
            keyId = selectedDid.getString("keyId");
        }

        monitor.info("Exporting key with ID: %s".formatted(keyId));

        String baseUrl = walletUrl + "/wallet-api/wallet/" + walletId + "/keys/" + keyId + "/export";
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl).newBuilder();
        urlBuilder.addQueryParameter("format", "JWK");
        urlBuilder.addQueryParameter("loadPrivateKey", "true");
        String urlGetKey = urlBuilder.build().toString();

        Request reqKey = new Request.Builder()
                .url(urlGetKey)
                .get()
                .addHeader("Authorization", String.format("Bearer %s", token))
                .build();

        Response resKey = client.newCall(reqKey).execute();

        if (!resKey.isSuccessful()) {
            String errMsg = "HTTP request to export key failed with status code: %s".formatted(resKey.code());
            monitor.warning(errMsg);
            throw new RuntimeException(errMsg);
        }

        String resBodyKey = resKey.body().string();
        monitor.debug("Export key raw response: %s".formatted(resBodyKey));

        return new JSONObject(resBodyKey);
    }

    /**
     * Represents the response of the matchCredentials method in the
     * WaltIDIdentityServices class.
     * It contains the matched credentials in the form of a JSONArray.
     *
     * @param presentationDefinition The presentation definition to match
     *                               credentials for.
     * @return The response containing the matched credentials.
     * @throws IOException If an I/O error occurs while making the request.
     */
    public MatchCredentialsResponse matchCredentials(PresentationDefinition presentationDefinition)
            throws IOException {
        String urlMatch = walletUrl + "/wallet-api/wallet/" + walletId
                + "/exchange/matchCredentialsForPresentationDefinition";

        String token = getWalletToken();
        JSONObject presDefJsonObj = presentationDefinition.getJsonObject();
        String jsonBody = presDefJsonObj.toString();
        RequestBody body = RequestBody.create(jsonBody, MediaType.parse("application/json; charset=utf-8"));

        monitor.debug(String.format("POST %s", urlMatch));
        monitor.debug("Using presentation definition: %s".formatted(jsonBody));

        Request request = new Request.Builder()
                .url(urlMatch)
                .addHeader("Authorization", "Bearer " + token)
                .addHeader("Content-Type", "application/json")
                .post(body)
                .build();

        Response response = client.newCall(request).execute();

        if (!response.isSuccessful()) {
            throw new RuntimeException(
                    String.format(
                            "HTTP request to match credentials failed with status code: %s",
                            response.code()));
        }

        String responseBody = response.body().string();
        monitor.debug("Raw response: " + responseBody);

        try {
            JSONArray jsonArr = new JSONArray(responseBody);
            return new MatchCredentialsResponse(jsonArr);
        } catch (JSONException e) {
            monitor.warning("Error decoding JSON array", e);
            return null;
        }
    }

    /**
     * Represents a response containing matching credentials.
     */
    public static class MatchCredentialsResponse {
        JSONArray matchingCredentials;

        /**
         * Constructs a new MatchCredentialsResponse object.
         *
         * @param matchingCredentials The array of matching credentials.
         */
        public MatchCredentialsResponse(JSONArray matchingCredentials) {
            this.matchingCredentials = matchingCredentials;
        }

        /**
         * Checks if the response is empty.
         *
         * @return True if the response is empty, false otherwise.
         */
        public boolean isEmpty() {
            return matchingCredentials == null || matchingCredentials.isEmpty();
        }

        private JSONObject parseVCFromJWTDocument(String jwtCredential) {
            String[] parts = jwtCredential.split("\\.");
            String payload = parts[1];
            String decodedPayload = new String(Base64.getUrlDecoder().decode(payload));
            JSONObject jwtCredentialObj = new JSONObject(decodedPayload);
            return jwtCredentialObj.getJSONObject("vc");
        }

        private boolean isActive(String jwtCredential) {
            try {
                JSONObject vcObj = parseVCFromJWTDocument(jwtCredential);
                
                if (!vcObj.has("expirationDate")) {
                    return true;
                }

                return ZonedDateTime.parse(vcObj.getString("expirationDate")).isAfter(ZonedDateTime.now());
            } catch (Exception e) {
                return false;
            }
        }

        private ZonedDateTime getIssuanceDate(String jwtCredential) {
            try {
                JSONObject vcObj = parseVCFromJWTDocument(jwtCredential);
                return ZonedDateTime.parse(vcObj.getString("issuanceDate"));
            } catch (Exception e) {
                return null;
            }
        }

        /**
         * Retrieves a list of active JWT tokens encoded as strings.
         *
         * @return A list of active JWT tokens encoded as strings, or null if there are
         *         no matching credentials.
         */
        public String getLatestActiveAsJWT() {
            if (isEmpty()) {
                return null;
            }

            return IntStream.range(0, matchingCredentials.length())
                    .mapToObj(i -> matchingCredentials.getJSONObject(i).getString("document"))
                    .filter(this::isActive)
                    .max(Comparator.comparing(this::getIssuanceDate))
                    .orElse(null);
        }
    }

    /**
     * Represents a presentation definition for a verifiable credential.
     */
    public static class PresentationDefinition {
        /**
         * The default VC (Verifiable Credential) type for WaltIDIdentityServices.
         */
        public static final String DEFAULT_VC_TYPE = "VerifiableCredential";

        private String vcType = DEFAULT_VC_TYPE;

        /**
         * Represents a presentation definition for a verifiable credential.
         * A presentation definition specifies the required attributes and constraints
         * for a presentation request.
         *
         * @param vcType the type of verifiable credential associated with this
         *               presentation definition
         */
        public PresentationDefinition(String vcType) {
            this.vcType = vcType;
        }

        /**
         * Represents the definition of a presentation request.
         */
        public PresentationDefinition() {
        }

        /**
         * Returns a JSONObject representation of the data.
         *
         * @return The JSONObject representation of the data.
         */
        public JSONObject getJsonObject() {
            Map<String, Object> map = new HashMap<>();

            map.put("id", UUID.randomUUID().toString());

            HashMap<String, Object> constraints = new HashMap<String, Object>() {
                {
                    put("fields", Arrays.asList(
                            new HashMap<String, Object>() {
                                {
                                    put("path", Arrays.asList("$.type"));
                                    put("filter", new HashMap<String, Object>() {
                                        {
                                            put("type", "string");
                                            put("pattern", "^%s$".formatted(vcType));
                                        }
                                    });
                                }
                            }));
                }
            };

            map.put("input_descriptors", Arrays.asList(
                    new HashMap<String, Object>() {
                        {
                            put("id", "A specific type of VC");
                            put("name", "A specific type of VC");
                            put("purpose", "We want a VC of this type");
                            put("constraints", constraints);
                        }
                    }));

            JSONObject jsonObject = new JSONObject(map);

            return jsonObject;
        }
    }
}
