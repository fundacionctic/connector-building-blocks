package eu.datacellar.iam;

import java.io.IOException;
import java.io.StringReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import javax.json.Json;
import javax.json.JsonArray;
import javax.json.JsonObject;
import javax.json.JsonReader;
import javax.json.JsonValue;

import org.eclipse.edc.spi.monitor.Monitor;

public class WaltIDIdentityServices {
    private Monitor monitor;
    private String walletUrl;
    private String walletEmail;
    private String walletPassword;
    private String walletId;

    public WaltIDIdentityServices(Monitor monitor, String walletUrl, String walletEmail, String walletPassword)
            throws IOException, InterruptedException {
        this.monitor = monitor;
        this.walletUrl = walletUrl;
        this.walletEmail = walletEmail;
        this.walletPassword = walletPassword;
        this.walletId = this.findWalletId();
    }

    public WaltIDIdentityServices(Monitor monitor, String walletUrl, String walletEmail, String walletPassword,
            String walletId) {
        this.monitor = monitor;
        this.walletUrl = walletUrl;
        this.walletEmail = walletEmail;
        this.walletPassword = walletPassword;
        this.walletId = walletId;
    }

    private String findWalletId() throws IOException, InterruptedException {
        monitor.info("Finding wallet ID for wallet with email: " + this.walletEmail + " and URL: " + this.walletUrl);

        HttpClient client = HttpClient.newHttpClient();
        String url = this.walletUrl + "/wallet-api/wallet/accounts/wallets";
        String token = getWalletToken();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .GET()
                .header("Authorization", "Bearer " + token)
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() >= 400) {
            monitor.warning("Failed to find wallet ID. HTTP request failed with status code: " + response.statusCode());

            throw new RuntimeException(
                    String.format("HTTP request failed with status code: %s", response.statusCode()));
        }

        monitor.debug("Raw response: " + response.body());

        JsonReader jsonReader = Json.createReader(new StringReader(response.body()));
        JsonObject obj = jsonReader.readObject();
        jsonReader.close();

        String walletId = obj.getJsonArray("wallets").getJsonObject(0).getString("id");

        monitor.info("Found wallet ID: " + walletId);

        return walletId;
    }

    public String getWalletToken() throws IOException, InterruptedException {
        monitor.debug(
                "Getting wallet token for wallet with email: " + this.walletEmail + " and URL: " + this.walletUrl);

        HttpClient client = HttpClient.newHttpClient();
        String url = this.walletUrl + "/wallet-api/auth/login";

        String json = Json.createObjectBuilder()
                .add("type", "email")
                .add("email", this.walletEmail)
                .add("password", this.walletPassword)
                .build()
                .toString();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .header("Content-Type", "application/json")
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() >= 400) {
            throw new RuntimeException(
                    String.format("HTTP request failed with status code: %s", response.statusCode()));
        }

        JsonReader jsonReader = Json.createReader(new StringReader(response.body()));
        JsonObject obj = jsonReader.readObject();
        jsonReader.close();

        String token = obj.getString("token");

        monitor.debug("Got wallet token: " + token);

        return token;
    }

    public MatchCredentialsResponse matchCredentials(PresentationDefinition presentationDefinition)
            throws IOException, InterruptedException {
        String urlMatch = walletUrl + "/wallet-api/wallet/" + walletId
                + "/exchange/matchCredentialsForPresentationDefinition";

        HttpClient client = HttpClient.newHttpClient();
        String token = getWalletToken();

        String jsonBody = presentationDefinition.getJsonObject().toString();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(urlMatch))
                .header("Authorization", "Bearer " + token)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() >= 400) {
            throw new RuntimeException(
                    String.format("HTTP request failed with status code: %s", response.statusCode()));
        }

        JsonReader jsonReader = Json.createReader(new StringReader(response.body()));
        JsonArray jsonArr = jsonReader.readArray();
        jsonReader.close();

        if (jsonArr == JsonValue.NULL) {
            return null;
        }

        return new MatchCredentialsResponse(jsonArr);
    }

    public class MatchCredentialsResponse {
        JsonArray matchingCredentials;

        public MatchCredentialsResponse(JsonArray matchingCredentials) {
            this.matchingCredentials = matchingCredentials;
        }
    }

    public class PresentationDefinition {
        public static final String DEFAULT_VC_TYPE = "gx:LegalParticipant";

        private String vcType = DEFAULT_VC_TYPE;

        public PresentationDefinition(String vcType) {
            this.vcType = vcType;
        }

        public PresentationDefinition() {
        }

        public JsonObject getJsonObject() {
            Map<String, Object> map = new HashMap<>();

            map.put("id", "first simple example");

            HashMap<String, Object> constraints = new HashMap<String, Object>() {
                {
                    put("fields", Arrays.asList(
                            new HashMap<String, Object>() {
                                {
                                    put("path", Arrays.asList("$.type"));
                                    put("filter", new HashMap<String, Object>() {
                                        {
                                            put("type", "array");
                                            put("contains", new HashMap<String, Object>() {
                                                {
                                                    put("type", "string");
                                                    put("pattern",
                                                            String.format("^%s$", vcType));
                                                }
                                            });
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

            JsonObject jsonObject = Json.createObjectBuilder(map).build();

            return jsonObject;
        }
    }
}
