package eu.datacellar.connector;

import java.util.Optional;

import org.eclipse.edc.spi.monitor.Monitor;
import org.json.JSONObject;

/**
 * Client for interacting with an external Policy Decision Point API.
 * The Policy Decision Point is responsible for making authorization decisions
 * based on policies, contract agreements, and verifiable presentations.
 */
public class PolicyDecisionPointAPI {

    /** Monitor for logging */
    private final Monitor monitor;

    /** Base URL of the Policy Decision Point API */
    private final String apiUrl;

    /** API key for authenticating requests */
    private final Optional<String> apiKey;

    /**
     * Creates a new Policy Decision Point API client.
     *
     * @param monitor The EDC monitor for logging
     * @param apiUrl  Base URL of the Policy Decision Point API
     * @param apiKey  API key for authentication
     */
    public PolicyDecisionPointAPI(Monitor monitor, String apiUrl, Optional<String> apiKey) {
        this.monitor = monitor;
        this.apiUrl = apiUrl;
        this.apiKey = apiKey;
    }

    /**
     * Creates a new Policy Decision Point API client without authentication.
     *
     * @param monitor The EDC monitor for logging
     * @param apiUrl  Base URL of the Policy Decision Point API
     */
    public PolicyDecisionPointAPI(Monitor monitor, String apiUrl) {
        this(monitor, apiUrl, Optional.empty());
    }

    /**
     * Requests an authorization decision from the Policy Decision Point.
     *
     * @param policyJsonString JSON string representation of the policy to evaluate
     * @param agreementId      ID of the contract agreement
     * @param vpJsonString     JSON string representation of the verifiable
     *                         presentation
     * @return true if authorization is granted, false otherwise
     */
    public boolean requestAuthorizationDecision(String policyJsonString, String agreementId, String vpJsonString) {
        if (!apiKey.isPresent()) {
            monitor.debug("Undefined PDP API Key: Requests will be sent without authentication");
        }

        JSONObject requestBody = new JSONObject()
                .put("policy", policyJsonString)
                .put("contractAgreementId", agreementId)
                .put("verifiablePresentation", vpJsonString);

        monitor.debug("Sending authorization request to PDP (%s) with arguments: %s"
                .formatted(apiUrl, requestBody.toString()));

        // ToDo: Implement the request to the Policy Decision Point API
        monitor.warning("PDP is not implemented: Returning positive authorization");
        return true;
    }
}
