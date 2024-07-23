package eu.datacellar.connector;

import static org.eclipse.edc.connector.contract.spi.validation.ContractValidationService.NEGOTIATION_SCOPE;
import static org.eclipse.edc.connector.contract.spi.validation.ContractValidationService.TRANSFER_SCOPE;
import static org.eclipse.edc.dataaddress.httpdata.spi.HttpDataAddressSchema.HTTP_DATA_TYPE;
import static org.eclipse.edc.jsonld.spi.PropertyAndTypeNames.ODRL_USE_ACTION_ATTRIBUTE;
import static org.eclipse.edc.policy.engine.spi.PolicyEngine.ALL_SCOPES;
import static org.eclipse.edc.spi.query.Criterion.criterion;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.util.Map;
import java.util.UUID;

import javax.sql.DataSource;

import org.eclipse.edc.connector.contract.spi.negotiation.store.ContractNegotiationStore;
import org.eclipse.edc.connector.contract.spi.offer.store.ContractDefinitionStore;
import org.eclipse.edc.connector.contract.spi.types.offer.ContractDefinition;
import org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParamsProvider;
import org.eclipse.edc.connector.dataplane.selector.spi.instance.DataPlaneInstance;
import org.eclipse.edc.connector.dataplane.selector.spi.store.DataPlaneInstanceStore;
import org.eclipse.edc.connector.policy.spi.PolicyDefinition;
import org.eclipse.edc.connector.policy.spi.store.PolicyDefinitionStore;
import org.eclipse.edc.connector.transfer.dataplane.spi.TransferDataPlaneConstants;
import org.eclipse.edc.policy.engine.spi.PolicyEngine;
import org.eclipse.edc.policy.engine.spi.RuleBindingRegistry;
import org.eclipse.edc.policy.model.Action;
import org.eclipse.edc.policy.model.AtomicConstraint;
import org.eclipse.edc.policy.model.LiteralExpression;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.policy.model.Policy;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.asset.AssetIndex;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.domain.asset.Asset;
import org.eclipse.edc.transaction.datasource.spi.DataSourceRegistry;
import org.json.JSONArray;
import org.json.JSONObject;
import org.postgresql.ds.PGSimpleDataSource;

import com.github.slugify.Slugify;

import io.swagger.parser.OpenAPIParser;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.parser.core.models.SwaggerParseResult;

/**
 * An extension that acts as a thin layer between the data space
 * and an existing HTTP API in a private backend accessible by the connector.
 */
@Extension(value = OpenAPICoreExtension.NAME)
public class OpenAPICoreExtension implements ServiceExtension {

    private static final String OPENAPI_PRESENTATION_DEFINITION_EXT_KEY = "x-connector-presentation-definition";
    private static final String WEB_HTTP_CONTROL_PORT = "web.http.control.port";
    private static final int DEFAULT_WEB_HTTP_CONTROL_PORT = 9192;
    private static final String WEB_HTTP_PUBLIC_PORT = "web.http.public.port";
    private static final int DEFAULT_WEB_HTTP_PUBLIC_PORT = 9291;
    private static final String DEFAULT_HTTP_SCHEME = "http";
    private static final String PUBLIC_API_URL_KEY = "publicApiUrl";
    private static final String DEFAULT_HOSTNAME = "localhost";
    private static final String WEB_HTTP_PUBLIC_URL = "web.http.public.url";
    private static final String DATASOURCE_URL = "edc.datasource.default.url";
    private static final String DATASOURCE_USER = "edc.datasource.default.user";
    private static final String DATASOURCE_PASSWORD = "edc.datasource.default.password";
    private static final String EDC_HOSTNAME = "edc.hostname";

    /**
     * The name of the extension.
     */
    public static final String NAME = "Core Connector";

    /**
     * The ID of the data plane instance.
     */
    public static final String DATA_PLANE_ID = "core-data-plane";

    /**
     * The URL of the OpenAPI specification of the backend API.
     */
    public String openapiUrl;

    @Setting
    private static final String OPENAPI_URL = "eu.datacellar.openapi.url";

    @Setting
    private static final String HTTP_SCHEME = "eu.datacellar.http.scheme";

    @Setting
    private static final String API_BASE_URL = "eu.datacellar.base.url";

    @Inject
    private HttpRequestParamsProvider paramsProvider;

    @Inject
    private PolicyDefinitionStore policyStore;

    @Inject
    private AssetIndex assetIndex;

    @Inject
    private ContractDefinitionStore contractStore;

    @Inject
    private ContractNegotiationStore contractNegotiationStore;

    @Inject
    private DataPlaneInstanceStore dataPlaneStore;

    @Inject
    private RuleBindingRegistry ruleBindingRegistry;

    @Inject
    private PolicyEngine policyEngine;

    @Inject
    private DataSourceRegistry dataSourceRegistry;

    @Override
    public String name() {
        return NAME;
    }

    private DataPlaneInstance buildDataPlaneInstance(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        String hostname = context.getSetting(EDC_HOSTNAME, DEFAULT_HOSTNAME);
        String controlPort = context.getSetting(WEB_HTTP_CONTROL_PORT, String.valueOf(DEFAULT_WEB_HTTP_CONTROL_PORT));
        String publicPort = context.getSetting(WEB_HTTP_PUBLIC_PORT, String.valueOf(DEFAULT_WEB_HTTP_PUBLIC_PORT));
        String scheme = context.getSetting(HTTP_SCHEME, DEFAULT_HTTP_SCHEME);

        String publicEndpoint = context.getSetting(WEB_HTTP_PUBLIC_URL,
                String.format("%s://%s:%s/public/", scheme, hostname, publicPort));

        DataPlaneInstance dataPlaneInstance = DataPlaneInstance.Builder.newInstance()
                .id(DATA_PLANE_ID)
                .url(String.format("%s://%s:%s/control/transfer", scheme, hostname, controlPort))
                .allowedSourceType(HTTP_DATA_TYPE)
                .allowedDestType(HTTP_DATA_TYPE)
                .allowedDestType(TransferDataPlaneConstants.HTTP_PROXY)
                .property(PUBLIC_API_URL_KEY, publicEndpoint)
                .build();

        monitor.debug(String.format("Built data plane instance: %s", dataPlaneInstance.getProperties()));

        return dataPlaneInstance;
    }

    private String extractCredentialTypePattern(Map<String, Object> presentationDefinition) {
        JSONObject presDefJsonObj = new JSONObject(presentationDefinition);
        JSONArray inputDescriptors = presDefJsonObj.optJSONArray("input_descriptors");

        if (inputDescriptors == null || inputDescriptors.length() == 0) {
            throw new IllegalArgumentException(
                    "Invalid presentation definition: input_descriptors is missing or empty");
        }

        JSONObject inputDescriptor = inputDescriptors.getJSONObject(0);
        JSONObject constraints = inputDescriptor.optJSONObject("constraints");

        if (constraints == null) {
            throw new IllegalArgumentException("Invalid presentation definition: constraints is missing");
        }

        JSONArray fields = constraints.optJSONArray("fields");

        if (fields == null || fields.length() == 0) {
            throw new IllegalArgumentException("Invalid presentation definition: fields is missing or empty");
        }

        JSONObject field = fields.getJSONObject(0);
        JSONArray paths = field.optJSONArray("path");

        if (paths == null || paths.length() == 0) {
            throw new IllegalArgumentException("Invalid presentation definition: path is missing or empty");
        }

        String credentialType = paths.getString(0);

        if (!credentialType.equals("$.type")) {
            throw new IllegalArgumentException("Invalid presentation definition: path is not equal to $.type");
        }

        JSONObject filter = field.optJSONObject("filter");

        if (filter == null) {
            throw new IllegalArgumentException("Invalid presentation definition: filter is missing");
        }

        return filter.getString("pattern");
    }

    /**
     * Builds a policy definition based on the given presentation definition.
     * Please check the following reference to learn more about presentation
     * definitions:
     * https://identity.foundation/presentation-exchange/spec/v2.0.0/#presentation-definition
     * Note that we only support a very limited subset of presentation definition
     * schemas (basically, only the VC type filter).
     *
     * @param presentationDefinition The presentation definition.
     * @return The policy definition.
     */
    private PolicyDefinition buildPolicyDefinition(Map<String, Object> presentationDefinition, Monitor monitor) {
        PolicyDefinition.Builder policyDefBuilder = PolicyDefinition.Builder.newInstance()
                .id(UUID.randomUUID().toString());

        if (presentationDefinition == null) {
            return policyDefBuilder.policy(Policy.Builder.newInstance().build()).build();
        }

        String credentialTypePattern = extractCredentialTypePattern(presentationDefinition);

        AtomicConstraint credentialConstraint = AtomicConstraint.Builder.newInstance()
                .leftExpression(new LiteralExpression(CredentialConstraintFunction.KEY))
                .operator(Operator.IN)
                .rightExpression(new LiteralExpression(credentialTypePattern))
                .build();

        Action useAction = Action.Builder.newInstance().type(ODRL_USE_ACTION_ATTRIBUTE).build();

        Permission permission = Permission.Builder.newInstance()
                .action(useAction)
                .constraint(credentialConstraint)
                .build();

        return policyDefBuilder
                .policy(Policy.Builder.newInstance().permission(permission).build())
                .build();
    }

    private void saveContractDefinition(String policyUid, String assetId) {
        String contractDefinitionId = String.format("contractdef-%s", assetId);

        var contractDefinition = ContractDefinition.Builder.newInstance()
                .id(contractDefinitionId)
                .accessPolicyId(policyUid)
                .contractPolicyId(policyUid)
                .assetsSelectorCriterion(criterion(Asset.PROPERTY_ID, "=", assetId))
                .build();

        contractStore.save(contractDefinition);
    }

    /**
     * Takes a URL that may contain a path and query parameters and returns the
     * base URL, namely the scheme, host and port only.
     * 
     * @param fullUrl The full URL.
     * @return The base URL.
     */
    private String extractBaseUrl(String fullUrl) {
        try {
            URL url = new URL(fullUrl);
            return String.format("%s://%s:%s", url.getProtocol(), url.getHost(), url.getPort());
        } catch (MalformedURLException e) {
            throw new RuntimeException(e);
        }
    }

    @SuppressWarnings("unchecked")
    private void createAssets(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();
        Slugify slg = Slugify.builder().lowerCase(false).build();
        OpenAPI openAPI = readOpenAPISchema(context.getMonitor());
        String baseUrl = context.getSetting(API_BASE_URL, extractBaseUrl(openapiUrl));

        openAPI.getPaths().forEach((path, pathItem) -> {
            pathItem.readOperationsMap().forEach((method, operation) -> {
                String operationId = operation.getOperationId();
                String assetId = slg.slugify(String.format("%s-%s", method, path));

                HttpDataAddress dataAddress = HttpDataAddress.Builder.newInstance()
                        .name(String.format("data-address-%s", assetId))
                        .baseUrl(baseUrl)
                        .path(path)
                        .method(method.name())
                        .contentType("application/json")
                        .proxyBody(Boolean.toString(true))
                        .proxyQueryParams(Boolean.toString(true))
                        .build();

                Asset asset = Asset.Builder.newInstance().id(assetId)
                        .name(String.format("%s %s (%s)", method, path, operationId))
                        .dataAddress(dataAddress)
                        .build();

                assetIndex.create(asset);

                monitor.debug(String.format("Created asset '%s' with data address: %s", assetId,
                        dataAddress.getProperties()));

                Map<String, Object> extensions = operation.getExtensions();
                Map<String, Object> presentationDefinition = null;

                if (extensions != null && extensions.containsKey(OPENAPI_PRESENTATION_DEFINITION_EXT_KEY)) {
                    presentationDefinition = (Map<String, Object>) extensions
                            .get(OPENAPI_PRESENTATION_DEFINITION_EXT_KEY);
                }

                monitor.debug("Building Policy for Presentation Definition: %s".formatted(presentationDefinition));
                PolicyDefinition policy = buildPolicyDefinition(presentationDefinition, monitor);
                policyStore.create(policy);
                saveContractDefinition(policy.getUid(), assetId);

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

    private void ensureDefaultDataSource(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        String pgUrl = context.getSetting(DATASOURCE_URL, null);
        String pgUser = context.getSetting(DATASOURCE_USER, null);
        String pgPass = context.getSetting(DATASOURCE_PASSWORD, null);

        if (pgUrl == null || pgUser == null || pgPass == null) {
            monitor.info("Undefined PostgreSQL connection properties: Skipping data source registration");
            return;
        }

        DataSource resolvedSource = dataSourceRegistry.resolve(DataSourceRegistry.DEFAULT_DATASOURCE);

        if (resolvedSource != null) {
            monitor.info("Data source '%s' is already registered".formatted(DataSourceRegistry.DEFAULT_DATASOURCE));
            return;
        }

        URI uri;

        try {
            uri = new URI(pgUrl.substring(5)); // remove "jdbc:"
        } catch (URISyntaxException e) {
            e.printStackTrace();
            monitor.warning("Invalid PostgreSQL URL: Skipping data source registration");
            return;
        }

        String host = uri.getHost();
        int port = uri.getPort();
        String dbName = uri.getPath().substring(1);

        PGSimpleDataSource dataSource = new PGSimpleDataSource();
        dataSource.setServerNames(new String[] { host });
        dataSource.setPortNumbers(new int[] { port });
        dataSource.setDatabaseName(dbName);
        dataSource.setUser(pgUser);
        dataSource.setPassword(pgPass);

        monitor.info("Manually registering data source '%s' to '%s:%s/%s' with username %s"
                .formatted(DataSourceRegistry.DEFAULT_DATASOURCE, host, port, dbName, pgUser));

        dataSourceRegistry.register(DataSourceRegistry.DEFAULT_DATASOURCE, dataSource);
    }

    private void registerPolicyFunctions(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        ruleBindingRegistry.bind(ODRL_USE_ACTION_ATTRIBUTE, ALL_SCOPES);
        ruleBindingRegistry.bind(CredentialConstraintFunction.KEY, NEGOTIATION_SCOPE);
        ruleBindingRegistry.bind(CredentialConstraintFunction.KEY, TRANSFER_SCOPE);

        CredentialConstraintFunction atomConstraintFunction = new CredentialConstraintFunction(monitor);

        monitor.info("Registering policy function: %s".formatted(CredentialConstraintFunction.KEY));

        policyEngine.registerFunction(
                ALL_SCOPES,
                Permission.class,
                CredentialConstraintFunction.KEY,
                atomConstraintFunction);
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        DataPlaneInstance dataPlane = buildDataPlaneInstance(context);
        dataPlaneStore.create(dataPlane);

        // ToDo: Review this
        // Data sources should be registered automatically, but I keep getting this:
        // "java.lang.NullPointerException: DataSource <name> could not be resolved"
        // So I'm registering the default data source manually for now.
        ensureDefaultDataSource(context);

        registerPolicyFunctions(context);

        openapiUrl = context.getSetting(OPENAPI_URL, null);

        if (openapiUrl != null) {
            createAssets(context);
        } else {
            monitor.warning(String.format("OpenAPI URL (property '%s') is not set", OPENAPI_URL));
        }

        paramsProvider
                .registerSourceDecorator(new ContractDetailsHttpParamsDecorator(monitor, contractNegotiationStore));

        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }
}