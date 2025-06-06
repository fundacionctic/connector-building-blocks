package eu.datacellar.connector;

import static org.eclipse.edc.dataaddress.httpdata.spi.HttpDataAddressSchema.HTTP_DATA_TYPE;
import static org.eclipse.edc.jsonld.spi.PropertyAndTypeNames.ODRL_USE_ACTION_ATTRIBUTE;
import static org.eclipse.edc.policy.engine.spi.PolicyEngine.ALL_SCOPES;
import static org.eclipse.edc.spi.query.Criterion.criterion;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import javax.sql.DataSource;

import org.eclipse.edc.connector.controlplane.asset.spi.domain.Asset;
import org.eclipse.edc.connector.controlplane.asset.spi.index.AssetIndex;
import org.eclipse.edc.connector.controlplane.contract.spi.negotiation.store.ContractNegotiationStore;
import org.eclipse.edc.connector.controlplane.contract.spi.offer.store.ContractDefinitionStore;
import org.eclipse.edc.connector.controlplane.contract.spi.types.offer.ContractDefinition;
import org.eclipse.edc.connector.controlplane.policy.spi.PolicyDefinition;
import org.eclipse.edc.connector.controlplane.policy.spi.store.PolicyDefinitionStore;
import org.eclipse.edc.connector.controlplane.transfer.dataplane.spi.TransferDataPlaneConstants;
import org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParamsProvider;
import org.eclipse.edc.connector.dataplane.selector.spi.instance.DataPlaneInstance;
import org.eclipse.edc.connector.dataplane.selector.spi.store.DataPlaneInstanceStore;
import org.eclipse.edc.policy.engine.spi.PolicyEngine;
import org.eclipse.edc.policy.engine.spi.RuleBindingRegistry;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.TypeManager;
import org.eclipse.edc.transaction.datasource.spi.DataSourceRegistry;
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
    private static final String DIDS_SEPARATOR = ",";
    // It would be more elegant and future-proof to reference the constants from
    // the appropriate edc modules.
    private static final String NEGOTIATION_SCOPE = "contract.negotiation";
    private static final String TRANSFER_SCOPE = "transfer.process";

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

    @Setting
    private static final String BACKEND_API_AUTH_KEY_HEADER = "es.ctic.backend.auth.key.header";

    @Setting
    private static final String BACKEND_API_AUTH_KEY_ENVVAR = "es.ctic.backend.auth.key.envvar";

    // Controls whether authorization constraints are added to policies.
    // When enabled (true), the connector will enforce authorization checks using:
    // 1. A list of implicitly trusted DIDs (Decentralized Identifiers)
    // 2. A Policy Decision Point (PDP) API for authorization decisions
    // When disabled (false), no authorization constraints are added to the
    // policies.
    // Default value is "false" for backward compatibility.
    @Setting
    private static final String ENABLE_AUTHORIZATION_CONSTRAINT = "es.ctic.enable.authorization.constraint";

    @Setting
    private static final String IMPLICITLY_TRUSTED_DIDS = "es.ctic.implicitly.trusted.dids";

    @Setting
    private static final String POLICY_DECISION_POINT_API_URL = "es.ctic.policy.decision.point.api.url";

    @Setting
    private static final String POLICY_DECISION_POINT_API_KEY = "es.ctic.policy.decision.point.api.key";

    // Controls whether assets are decorated with Omega-X Marketplace metadata.
    // When enabled (true), the connector adds Dublin Core and FOAF properties to
    // assets.
    // Default value is "true" to ensure rich metadata by default.
    @Setting
    private static final String OMEGAX_DECORATION_ENABLED = "eu.datacellar.omegax.decoration.enabled";

    @Setting
    private static final String OMEGAX_DECORATION_CREATOR_NAME = "eu.datacellar.omegax.decoration.default.creator.name";

    @Setting
    private static final String OMEGAX_DECORATION_PUBLISHER_HOMEPAGE = "eu.datacellar.omegax.decoration.default.publisher.homepage";

    // Controls whether the connector should continue initialization when OpenAPI
    // validation fails.
    // When enabled (true), if the OpenAPI URL cannot be read or parsed, the
    // connector will log a warning
    // and continue without creating assets.
    // When disabled (false), the connector will throw an exception and stop
    // initialization.
    // Default value is "true" to continue on validation failures.
    @Setting
    private static final String OPENAPI_VALIDATION_CONTINUE_ON_FAILURE = "eu.datacellar.openapi.validation.continue.on.failure";

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

    @Inject
    private TypeManager typeManager;

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

        boolean isAuthEnabled = context.getSetting(ENABLE_AUTHORIZATION_CONSTRAINT, "false")
                .equals("true");

        PolicyBuilder policyBuilder = new PolicyBuilder(monitor, isAuthEnabled);

        boolean isOmegaxDecorationEnabled = context.getSetting(OMEGAX_DECORATION_ENABLED, "true")
                .equals("true");

        String creatorName = context.getSetting(OMEGAX_DECORATION_CREATOR_NAME, null);
        String publisherHomepage = context.getSetting(OMEGAX_DECORATION_PUBLISHER_HOMEPAGE, null);

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

                Asset.Builder assetBuilder = Asset.Builder.newInstance()
                        .id(assetId)
                        .name(String.format("%s %s (%s)", method, path, operationId))
                        .dataAddress(dataAddress);

                if (isOmegaxDecorationEnabled) {
                    OmegaxAssetDecorator.Context decorationContext = new OmegaxAssetDecorator.Context.Builder()
                            .monitor(monitor)
                            .operation(operation)
                            .path(path)
                            .method(method.name())
                            .baseUrl(baseUrl)
                            .creatorName(creatorName)
                            .publisherHomepage(publisherHomepage)
                            .build();

                    assetBuilder = OmegaxAssetDecorator.decorate(assetBuilder, decorationContext);
                }

                assetIndex.create(assetBuilder.build());

                monitor.debug(String.format("Created asset '%s' with data address: %s", assetId,
                        dataAddress.getProperties()));

                Map<String, Object> extensions = operation.getExtensions();
                Map<String, Object> presentationDefinition = null;

                if (extensions != null && extensions.containsKey(OPENAPI_PRESENTATION_DEFINITION_EXT_KEY)) {
                    presentationDefinition = (Map<String, Object>) extensions
                            .get(OPENAPI_PRESENTATION_DEFINITION_EXT_KEY);
                }

                monitor.debug("Building Policy for Presentation Definition: %s".formatted(presentationDefinition));

                PolicyDefinition policy = policyBuilder.buildPolicyDefinition(presentationDefinition);

                policyStore.create(policy);
                saveContractDefinition(policy.getId(), assetId);

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

    /**
     * Validates that the OpenAPI schema can be read and parsed successfully.
     * 
     * @param monitor           the EDC monitor
     * @param continueOnFailure whether to continue on validation failures or throw
     *                          exceptions
     * @return true if validation succeeds, false if validation fails and
     *         continueOnFailure is enabled
     * @throws IllegalStateException if validation fails and continueOnFailure is
     *                               disabled
     */
    private boolean validateOpenAPISchema(Monitor monitor, boolean continueOnFailure) {
        try {
            SwaggerParseResult result = new OpenAPIParser().readLocation(openapiUrl, null, null);
            OpenAPI openAPI = result.getOpenAPI();

            if (result.getMessages() != null && !result.getMessages().isEmpty()) {
                result.getMessages().forEach((msg) -> monitor.warning("OpenAPI validation warning: " + msg));
            }

            if (openAPI == null) {
                String errorMsg = String.format("Failed to read OpenAPI schema from URL '%s'", openapiUrl);

                if (continueOnFailure) {
                    monitor.warning(errorMsg + " - Skipping asset creation");
                    return false;
                } else {
                    throw new IllegalStateException(errorMsg);
                }
            }

            monitor.info(String.format("Successfully validated OpenAPI schema from URL '%s'", openapiUrl));
            return true;

        } catch (Exception e) {
            String errorMsg = String.format("Error validating OpenAPI schema from URL '%s': %s", openapiUrl,
                    e.getMessage());

            if (continueOnFailure) {
                monitor.warning(errorMsg + " - Skipping asset creation");
                return false;
            } else {
                throw new IllegalStateException(errorMsg, e);
            }
        }
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

    private AuthorizationConstraintFunction buildAuthorizationConstraintFunction(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();
        String pdpUrl = context.getSetting(POLICY_DECISION_POINT_API_URL, null);
        String pdpApiKey = context.getSetting(POLICY_DECISION_POINT_API_KEY, null);
        String implicitlyTrustedDids = context.getSetting(IMPLICITLY_TRUSTED_DIDS, null);

        List<String> implicitlyTrustedDidsList = implicitlyTrustedDids != null
                ? Arrays.asList(implicitlyTrustedDids.split(DIDS_SEPARATOR))
                : Collections.emptyList();

        if (!implicitlyTrustedDidsList.isEmpty()) {
            monitor.info("Implicitly trusted DIDs: %s".formatted(implicitlyTrustedDidsList));
        }

        Optional<PolicyDecisionPointAPI> policyDecisionPointAPI = pdpUrl != null
                ? Optional.of(new PolicyDecisionPointAPI(monitor, pdpUrl,
                        pdpApiKey != null ? Optional.of(pdpApiKey) : Optional.empty()))
                : Optional.empty();

        if (policyDecisionPointAPI.isPresent()) {
            monitor.info("Policy Decision Point API is available: %s".formatted(policyDecisionPointAPI.get()));
        } else {
            monitor.warning("Undefined Policy Decision Point API");
        }

        return new AuthorizationConstraintFunction(monitor, typeManager, implicitlyTrustedDidsList,
                policyDecisionPointAPI);
    }

    private void registerPolicyFunctions(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        ruleBindingRegistry.bind(ODRL_USE_ACTION_ATTRIBUTE, ALL_SCOPES);

        ruleBindingRegistry.bind(CredentialConstraintFunction.KEY, NEGOTIATION_SCOPE);
        ruleBindingRegistry.bind(CredentialConstraintFunction.KEY, TRANSFER_SCOPE);
        CredentialConstraintFunction atomConstraintFunction = new CredentialConstraintFunction(monitor);

        policyEngine.registerFunction(
                ALL_SCOPES,
                Permission.class,
                CredentialConstraintFunction.KEY,
                atomConstraintFunction);

        monitor.info("Registered policy function: %s".formatted(CredentialConstraintFunction.KEY));

        ruleBindingRegistry.bind(AuthorizationConstraintFunction.KEY, TRANSFER_SCOPE);
        AuthorizationConstraintFunction authorizationConstraintFunction = buildAuthorizationConstraintFunction(context);

        policyEngine.registerFunction(
                TRANSFER_SCOPE,
                Permission.class,
                AuthorizationConstraintFunction.KEY,
                authorizationConstraintFunction);

        monitor.info("Registered policy function: %s".formatted(AuthorizationConstraintFunction.KEY));
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
            boolean continueOnFailure = context.getSetting(OPENAPI_VALIDATION_CONTINUE_ON_FAILURE, "true")
                    .equals("true");

            if (validateOpenAPISchema(monitor, continueOnFailure)) {
                createAssets(context);
            }
        } else {
            monitor.warning(String.format("OpenAPI URL (property '%s') is not set", OPENAPI_URL));
        }

        paramsProvider
                .registerSourceDecorator(new ContractDetailsHttpParamsDecorator(monitor, contractNegotiationStore));

        // Check if backend API authentication is configured
        // This will be used to set an API key header in the proxied requests
        String backendAuthKeyHeader = context.getSetting(BACKEND_API_AUTH_KEY_HEADER, null);
        String backendAuthKeyEnvVar = context.getSetting(BACKEND_API_AUTH_KEY_ENVVAR, null);

        if (backendAuthKeyHeader != null && backendAuthKeyEnvVar != null) {
            monitor.info(String.format(
                    "Registering backend API authentication decorator with header '%s' and environment variable '%s'",
                    backendAuthKeyHeader, backendAuthKeyEnvVar));

            paramsProvider.registerSourceDecorator(
                    new BackendAPIAuthHttpParamsDecorator(monitor, backendAuthKeyHeader, backendAuthKeyEnvVar));
        }

        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }
}