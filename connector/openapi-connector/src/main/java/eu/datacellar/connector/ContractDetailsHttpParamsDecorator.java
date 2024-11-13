package eu.datacellar.connector;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.eclipse.edc.connector.controlplane.contract.spi.negotiation.store.ContractNegotiationStore;
import org.eclipse.edc.connector.controlplane.contract.spi.types.agreement.ContractAgreement;
import org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress;
import org.eclipse.edc.connector.dataplane.http.spi.HttpParamsDecorator;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParams.Builder;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowStartMessage;

import okhttp3.HttpUrl;

/**
 * Decorator class for adding contract details to the proxied HTTP requests.
 */
public class ContractDetailsHttpParamsDecorator implements HttpParamsDecorator {

    private final Monitor monitor;
    private final ContractNegotiationStore contractNegotiationStore;
    private static final String QUERY_PARAM_CONTRACT_ID = "contractId";
    private static final String HEADER_CONNECTOR_EXT = "X-Connector-Extension";
    private static final String HEADER_ASSET_ID = "X-Connector-Asset-Id";
    private static final String HEADER_CONSUMER_ID = "X-Connector-Consumer-Id";
    private static final String HEADER_CONTRACT_SIGNING_DATE = "X-Connector-Contract-Signing-Date";
    private static final String PROP_QUERY_PARAMS = "queryParams";

    /**
     * Constructs a new instance of the ContractDetailsHttpParamsDecorator class.
     *
     * @param monitor                  The monitor object used for monitoring.
     * @param contractNegotiationStore The contract negotiation store object used
     *                                 for storing contract details.
     */
    public ContractDetailsHttpParamsDecorator(Monitor monitor, ContractNegotiationStore contractNegotiationStore) {
        this.monitor = monitor;
        this.contractNegotiationStore = contractNegotiationStore;
    }

    private Map<String, List<String>> queryParamsStringToMap(String queryParams) {
        Map<String, List<String>> queryMap = new HashMap<>();

        HttpUrl url = HttpUrl.parse("https://example.com?%s".formatted(queryParams));

        for (int i = 0, size = url.querySize(); i < size; i++) {
            String key = url.queryParameterName(i);
            String value = url.queryParameterValue(i);

            if (queryMap.containsKey(key)) {
                queryMap.get(key).add(value);
            } else {
                queryMap.put(key, List.of(value));
            }
        }

        return queryMap;
    }

    private String mapToQueryParamsString(Map<String, List<String>> queryMap) {
        HttpUrl.Builder urlBuilder = new HttpUrl.Builder()
                .scheme("https")
                .host("example.com");

        for (Map.Entry<String, List<String>> entry : queryMap.entrySet()) {
            for (String value : entry.getValue()) {
                urlBuilder.addQueryParameter(entry.getKey(), value);
            }
        }

        HttpUrl url = urlBuilder.build();

        return url.query();
    }

    /**
     * Add contract details to the proxied request.
     */
    @Override
    public Builder decorate(DataFlowStartMessage request, HttpDataAddress address, Builder builder) {
        Package pkg = ContractDetailsHttpParamsDecorator.class.getPackage();
        String packageName = pkg.getName();
        builder.header(HEADER_CONNECTOR_EXT, packageName);

        String queryParams = request.getProperties().getOrDefault(PROP_QUERY_PARAMS, null);

        if (queryParams == null || queryParams.isEmpty()) {
            monitor.debug("Query parameters not found in request properties");
            return builder;
        }

        monitor.debug("Request properties: %s".formatted(request.getProperties()));
        Map<String, List<String>> queryMap = queryParamsStringToMap(queryParams);
        monitor.debug("Parsed query map: %s".formatted(queryMap));

        String contractId = Optional.ofNullable(queryMap.get(QUERY_PARAM_CONTRACT_ID))
                .map(list -> list.get(0))
                .orElse(null);

        if (contractId == null) {
            monitor.debug("Contract ID not found in query parameters");
            return builder;
        }

        monitor.debug("Contract ID: %s".formatted(contractId));
        ContractAgreement contractAgreement = contractNegotiationStore.findContractAgreement(contractId);

        if (contractAgreement == null) {
            monitor.debug("Contract agreement with id '%s' not found in store".formatted(contractId));
            return builder;
        }

        monitor.debug("Contract agreement: %s".formatted(contractAgreement));

        builder.header(HEADER_ASSET_ID, contractAgreement.getAssetId());
        builder.header(HEADER_CONSUMER_ID, contractAgreement.getConsumerId());

        String contractSigningDate = DateTimeFormatter.ISO_INSTANT
                .withZone(ZoneOffset.UTC)
                .format(Instant.ofEpochSecond(contractAgreement.getContractSigningDate()));

        builder.header(HEADER_CONTRACT_SIGNING_DATE, contractSigningDate);

        queryMap.remove(QUERY_PARAM_CONTRACT_ID);
        String updatedQueryString = mapToQueryParamsString(queryMap);
        monitor.debug("Updated query string: %s".formatted(updatedQueryString));
        builder.queryParams(updatedQueryString);

        return builder;
    }
}
