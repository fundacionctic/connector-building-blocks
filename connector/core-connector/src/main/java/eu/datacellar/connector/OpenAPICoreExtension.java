package eu.datacellar.connector;

import static org.eclipse.edc.dataaddress.httpdata.spi.HttpDataAddressSchema.HTTP_DATA_TYPE;
import static org.eclipse.edc.policy.engine.spi.PolicyEngine.ALL_SCOPES;
import static org.eclipse.edc.spi.query.Criterion.criterion;

import java.net.MalformedURLException;
import java.net.URL;

import org.eclipse.edc.connector.contract.spi.offer.store.ContractDefinitionStore;
import org.eclipse.edc.connector.contract.spi.types.offer.ContractDefinition;
import org.eclipse.edc.connector.core.CoreServicesExtension;
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

    private static final String WEB_HTTP_CONTROL_PORT = "web.http.control.port";
    private static final int DEFAULT_WEB_HTTP_CONTROL_PORT = 9192;
    private static final String WEB_HTTP_PUBLIC_PORT = "web.http.public.port";
    private static final int DEFAULT_WEB_HTTP_PUBLIC_PORT = 9291;
    private static final String DEFAULT_HTTP_SCHEME = "http";
    private static final String PUBLIC_API_URL_KEY = "publicApiUrl";
    private static final String DEFAULT_HOSTNAME = "localhost";

    /**
     * The name of the extension.
     */
    public static final String NAME = "Core Connector";

    /**
     * The ID of the data plane instance.
     */
    public static final String DATA_PLANE_ID = "core-data-plane";

    /**
     * The ID of the policy definition.
     */
    public static final String POLICY_DEFINITION_ID = "core-policy-definition";

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
    private DataPlaneInstanceStore dataPlaneStore;

    @Inject
    private RuleBindingRegistry ruleBindingRegistry;

    @Inject
    private PolicyEngine policyEngine;

    @Override
    public String name() {
        return NAME;
    }

    private DataPlaneInstance buildDataPlaneInstance(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();

        String hostname = context.getSetting(CoreServicesExtension.HOSTNAME_SETTING, DEFAULT_HOSTNAME);
        String controlPort = context.getSetting(WEB_HTTP_CONTROL_PORT, String.valueOf(DEFAULT_WEB_HTTP_CONTROL_PORT));
        String publicPort = context.getSetting(WEB_HTTP_PUBLIC_PORT, String.valueOf(DEFAULT_WEB_HTTP_PUBLIC_PORT));
        String scheme = context.getSetting(HTTP_SCHEME, DEFAULT_HTTP_SCHEME);

        DataPlaneInstance dataPlaneInstance = DataPlaneInstance.Builder.newInstance()
                .id(DATA_PLANE_ID)
                .url(String.format("%s://%s:%s/control/transfer", scheme, hostname, controlPort))
                .allowedSourceType(HTTP_DATA_TYPE)
                .allowedDestType(HTTP_DATA_TYPE)
                .allowedDestType(TransferDataPlaneConstants.HTTP_PROXY)
                .property(PUBLIC_API_URL_KEY, String.format("%s://%s:%s/public/", scheme, hostname, publicPort))
                .build();

        monitor.debug(String.format("Built data plane instance: %s", dataPlaneInstance.getProperties()));

        return dataPlaneInstance;
    }

    private PolicyDefinition buildPolicyDefinition() {
        final Action USE_ACTION = Action.Builder.newInstance().type("USE").build();

        ruleBindingRegistry.bind(USE_ACTION.getType(), ALL_SCOPES);
        ruleBindingRegistry.bind(CredentialConstraintFunction.KEY, ALL_SCOPES);

        // This policy constraint function always returns true, so it does not actually
        // enforce any constraint.
        // This is just a placeholder to demonstrate how to register a policy function.
        policyEngine.registerFunction(ALL_SCOPES, Permission.class,
                CredentialConstraintFunction.KEY,
                new CredentialConstraintFunction());

        var credentialConstraint = AtomicConstraint.Builder.newInstance()
                .leftExpression(new LiteralExpression(CredentialConstraintFunction.KEY))
                .operator(Operator.IN)
                .rightExpression(new LiteralExpression("expectedCredential")).build();

        var permission = Permission.Builder.newInstance().action(USE_ACTION).constraint(credentialConstraint)
                .build();

        return PolicyDefinition.Builder.newInstance()
                .id(POLICY_DEFINITION_ID)
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

    private void createAssets(ServiceExtensionContext context, String policyUid) {
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

        DataPlaneInstance dataPlane = buildDataPlaneInstance(context);
        dataPlaneStore.create(dataPlane);

        openapiUrl = context.getSetting(OPENAPI_URL, null);

        if (openapiUrl != null) {
            PolicyDefinition policy = buildPolicyDefinition();
            policyStore.create(policy);
            createAssets(context, policy.getUid());
        } else {
            monitor.warning(String.format("OpenAPI URL (property '%s') is not set", OPENAPI_URL));
        }

        Package pkg = OpenAPICoreExtension.class.getPackage();
        String pkgVersion = pkg.getImplementationVersion();

        paramsProvider.registerSourceDecorator((request, address, builder) -> {
            if (pkgVersion != null) {
                builder.header("X-Core-Connector-Source-Version", pkgVersion);
            }

            return builder;
        });

        paramsProvider.registerSinkDecorator((request, address, builder) -> {
            if (pkgVersion != null) {
                builder.header("X-Core-Connector-Sink-Version", pkgVersion);
            }

            return builder;
        });

        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }
}