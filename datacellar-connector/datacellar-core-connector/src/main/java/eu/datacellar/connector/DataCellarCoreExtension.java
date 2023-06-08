package eu.datacellar.connector;

import static org.eclipse.edc.spi.query.Criterion.criterion;

import java.util.List;

import org.eclipse.edc.connector.contract.spi.offer.store.ContractDefinitionStore;
import org.eclipse.edc.connector.contract.spi.types.offer.ContractDefinition;
import org.eclipse.edc.connector.core.CoreServicesExtension;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParamsProvider;
import org.eclipse.edc.connector.dataplane.selector.spi.instance.DataPlaneInstance;
import org.eclipse.edc.connector.dataplane.selector.spi.store.DataPlaneInstanceStore;
import org.eclipse.edc.connector.policy.spi.PolicyDefinition;
import org.eclipse.edc.connector.policy.spi.store.PolicyDefinitionStore;
import org.eclipse.edc.connector.transfer.dataplane.spi.TransferDataPlaneConstants;
import org.eclipse.edc.policy.model.Policy;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.asset.AssetIndex;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.domain.HttpDataAddress;
import org.eclipse.edc.spi.types.domain.asset.Asset;
import org.eclipse.edc.web.jetty.JettyConfiguration;

import io.swagger.parser.OpenAPIParser;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.servers.Server;
import io.swagger.v3.parser.core.models.SwaggerParseResult;

/**
 * An extension that acts as a thin layer between the Data Cellar data space
 * and an existing HTTP API in a private backend accessible by the connector.
 */
@Extension(value = DataCellarCoreExtension.NAME)
public class DataCellarCoreExtension implements ServiceExtension {

    private static final String WEB_HTTP_PORT = "web.http.port";
    private static final String DEFAULT_HTTP_SCHEME = "http";

    /**
     * The name of the extension.
     */
    public static final String NAME = "Data Cellar Core Connector";

    /**
     * The ID of the data plane instance.
     */
    public static final String DATA_PLANE_ID = "datacellar-data-plane";

    /**
     * The ID of the policy definition.
     */
    public static final String POLICY_DEFINITION_ID = "datacellar-policy-definition";

    /**
     * The URL of the OpenAPI specification of the backend API.
     */
    public String openapiUrl;

    @Setting
    private static final String OPENAPI_URL = "eu.datacellar.openapiurl";

    @Setting
    private static final String HTTP_SCHEME = "eu.datacellar.httpscheme";

    @Inject
    private HttpRequestParamsProvider paramsProvider;

    @Inject
    private PolicyDefinitionStore policyStore;

    @Inject
    private AssetIndex assetIndex;

    @Inject
    private ContractDefinitionStore contractStore;

    @Inject
    private DataPlaneInstanceStore dataPlaneStore;

    @Override
    public String name() {
        return NAME;
    }

    private String getHostname(ServiceExtensionContext context) {
        return context.getSetting(CoreServicesExtension.HOSTNAME_SETTING, "localhost");
    }

    private DataPlaneInstance createDataPlaneInstance(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        String hostname = getHostname(context);
        String httpPort = context.getSetting(WEB_HTTP_PORT, String.valueOf(JettyConfiguration.DEFAULT_PORT));
        String scheme = context.getSetting(HTTP_SCHEME, DEFAULT_HTTP_SCHEME);

        DataPlaneInstance dataPlaneInstance = DataPlaneInstance.Builder.newInstance()
                .id(DATA_PLANE_ID)
                .url(String.format("%s://%s:%s/control/transfer", scheme, hostname, httpPort))
                .allowedSourceType(HttpDataAddress.HTTP_DATA)
                .allowedDestType(HttpDataAddress.HTTP_DATA)
                .allowedDestType(TransferDataPlaneConstants.HTTP_PROXY)
                .property("publicApiUrl", String.format("%s://%s:%s/public/", scheme, hostname, httpPort))
                .build();

        monitor.debug(String.format("Created data plane instance: %s", DATA_PLANE_ID));

        return dataPlaneInstance;
    }

    private PolicyDefinition createPolicyDefinition() {
        return PolicyDefinition.Builder.newInstance()
                .id(POLICY_DEFINITION_ID)
                .policy(Policy.Builder.newInstance().build())
                .build();
    }

    private void saveContractDefinition(String policyUid, String assetId) {
        String contractDefinitionId = String.format("contract-def-%s", assetId);

        var contractDefinition = ContractDefinition.Builder.newInstance()
                .id(contractDefinitionId)
                .accessPolicyId(policyUid)
                .contractPolicyId(policyUid)
                .assetsSelectorCriterion(criterion(Asset.PROPERTY_ID, "=", assetId))
                .build();

        contractStore.save(contractDefinition);
    }

    private void createAssets(ServiceExtensionContext context, String policyUid) {
        Monitor monitor = context.getMonitor();
        OpenAPI openAPI = readOpenAPISchema(context.getMonitor());

        openAPI.getPaths().forEach((path, pathItem) -> {
            pathItem.readOperationsMap().forEach((method, operation) -> {
                String operationId = operation.getOperationId();
                String assetId = String.format("%s-%s", path, operationId);

                HttpDataAddress dataAddress = HttpDataAddress.Builder.newInstance()
                        .name(String.format("data-address-%s", assetId))
                        .baseUrl("http://host.docker.internal:9090")
                        .path(path)
                        .method(method.name())
                        .contentType("application/json")
                        .build();

                Asset asset = Asset.Builder.newInstance().id(assetId).build();
                assetIndex.create(asset, dataAddress);

                monitor.debug(String.format("Created asset '%s' with data address: %s", assetId,
                        dataAddress.getProperties()));

                saveContractDefinition(policyUid, assetId);

                monitor.debug(String.format("Created contract definition for asset '%s'", assetId));
            });
        });
    }

    /**
     * Reads the OpenAPI schema from the URL specified in the settings.
     * 
     * @param monitor the EDC monitor
     * @return the OpenAPI schema
     */
    public OpenAPI readOpenAPISchema(Monitor monitor) {
        SwaggerParseResult result = new OpenAPIParser().readLocation(openapiUrl, null, null);
        OpenAPI openAPI = result.getOpenAPI();

        if (result.getMessages() != null) {
            result.getMessages().forEach((msg) -> monitor.warning(msg));
        }

        if (openAPI == null) {
            throw new IllegalStateException(String.format("Failed to read OpenAPI schema from URL '%s'", openapiUrl));
        }

        return openAPI;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        openapiUrl = context.getSetting(OPENAPI_URL, null);

        if (openapiUrl == null) {
            throw new IllegalStateException(String.format("OpenAPI URL (property '%s') is not set", OPENAPI_URL));
        }

        Package pkg = DataCellarCoreExtension.class.getPackage();
        String pkgVersion = pkg.getImplementationVersion();

        paramsProvider.registerSourceDecorator((request, address, builder) -> {
            if (pkgVersion != null) {
                builder.header("X-Data-Cellar-Source-Version", pkgVersion);
            }

            return builder;
        });

        paramsProvider.registerSinkDecorator((request, address, builder) -> {
            if (pkgVersion != null) {
                builder.header("X-Data-Cellar-Sink-Version", pkgVersion);
            }

            return builder;
        });

        createDataPlaneInstance(context);
        PolicyDefinition policy = createPolicyDefinition();
        createAssets(context, policy.getUid());

        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }
}