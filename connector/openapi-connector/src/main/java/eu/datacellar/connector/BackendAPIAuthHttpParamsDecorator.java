package eu.datacellar.connector;

import org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress;
import org.eclipse.edc.connector.dataplane.http.spi.HttpParamsDecorator;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParams.Builder;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowStartMessage;

/**
 * Decorator class for adding API key authentication to proxied HTTP requests.
 * This decorator adds an API key header to each request for authentication with
 * the backend API.
 * 
 * The API key is retrieved from an environment variable specified during
 * construction.
 * If the environment variable is not found, a warning is logged and the request
 * proceeds
 * without authentication.
 */
public class BackendAPIAuthHttpParamsDecorator implements HttpParamsDecorator {

    private final Monitor monitor;
    private final String apiKeyHeaderName;
    private final String apiKeyEnvVar;

    /**
     * Constructs a new instance of the BackendAPIAuthHttpParamsDecorator.
     *
     * @param monitor          The monitor object used for logging warnings and
     *                         debug information
     * @param apiKeyHeaderName The name of the HTTP header that will contain the API
     *                         key
     * @param apiKeyEnvVar     The name of the environment variable containing the
     *                         API key value
     */
    public BackendAPIAuthHttpParamsDecorator(Monitor monitor, String apiKeyHeaderName, String apiKeyEnvVar) {
        this.monitor = monitor;
        this.apiKeyHeaderName = apiKeyHeaderName;
        this.apiKeyEnvVar = apiKeyEnvVar;
    }

    /**
     * Decorates the HTTP request by adding the API key authentication header.
     * The API key is retrieved from the environment variable specified during
     * construction.
     * If the environment variable is not found, a warning is logged and the request
     * proceeds without modification.
     *
     * @param request The data flow start message containing request details
     * @param address The HTTP data address for the request
     * @param builder The builder for HTTP request parameters
     * @return The modified builder with the added API key header, or the unmodified
     *         builder if the API key could not be retrieved
     */
    @Override
    public Builder decorate(DataFlowStartMessage request, HttpDataAddress address, Builder builder) {
        String apiKey = System.getenv(apiKeyEnvVar);

        if (apiKey == null) {
            monitor.warning(String.format("API key not found in environment variable: %s", apiKeyEnvVar));
            return builder;
        }

        monitor.debug(String.format("API key found in environment variable: %s", apiKeyEnvVar));
        builder.header(apiKeyHeaderName, System.getenv(apiKeyEnvVar));
        return builder;
    }
}
