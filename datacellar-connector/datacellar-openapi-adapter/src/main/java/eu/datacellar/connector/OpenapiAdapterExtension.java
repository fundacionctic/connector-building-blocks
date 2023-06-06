package eu.datacellar.connector;

import static org.eclipse.edc.spi.query.Criterion.criterion;

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

/**
 * An extension that acts as a thin layer between the Data Cellar data space
 * and an existing HTTP API in a private backend accessible by the connector.
 */
@Extension(value = OpenapiAdapterExtension.NAME)
public class OpenapiAdapterExtension implements ServiceExtension {

    /**
     * The name of the extension.
     */
    public static final String NAME = "Data Cellar OpenAPI Adapter Extension";

    @Setting
    private static final String OPENAPI_URL = "eu.datacellar.openapiurl";

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

    @Override
    public void initialize(ServiceExtensionContext context) {
        var openapiUrl = context.getSetting(OPENAPI_URL, null);

        if (openapiUrl == null) {
            throw new IllegalStateException(String.format("OpenAPI URL (property '%s') is not set", OPENAPI_URL));
        }

        paramsProvider.registerSourceDecorator(
                (request, address, builder) -> builder.header("X-Data-Cellar", "source"));

        paramsProvider.registerSinkDecorator(
                (request, address, builder) -> builder.header("X-Data-Cellar", "sink"));

        String assetId = "the-asset";
        String dataPlaneId = "the-data-plane-instance";
        String dataAddressId = "the-asset-http-data-address";

        String hostname = context.getSetting(CoreServicesExtension.HOSTNAME_SETTING, "localhost");

        DataPlaneInstance dataPlaneInstance = DataPlaneInstance.Builder.newInstance()
                .id(dataPlaneId)
                .url(String.format("http://%s:9192/control/transfer", hostname))
                .allowedSourceType(HttpDataAddress.HTTP_DATA)
                .allowedDestType(HttpDataAddress.HTTP_DATA)
                .allowedDestType(TransferDataPlaneConstants.HTTP_PROXY)
                .property("publicApiUrl", String.format("http://%s:9291/public/", hostname))
                .build();

        dataPlaneStore.create(dataPlaneInstance);

        PolicyDefinition policy = buildPolicyDefinition();
        policyStore.create(policy);

        HttpDataAddress dataAddress = HttpDataAddress.Builder.newInstance()
                .name(dataAddressId)
                .baseUrl("https://dummyjson.com")
                .path("/carts")
                .method("GET")
                // .proxyBody("true")
                // .proxyMethod("true")
                // .proxyPath("true")
                // .proxyQueryParams("true")
                .contentType("application/json")
                .build();

        Asset asset = Asset.Builder.newInstance().id(assetId).build();
        assetIndex.create(asset, dataAddress);

        saveContractDefinition(policy.getUid(), assetId);

        Monitor monitor = context.getMonitor();
        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }

    private PolicyDefinition buildPolicyDefinition() {
        String policyDefinitionId = "the-policy-definition";

        return PolicyDefinition.Builder.newInstance()
                .id(policyDefinitionId)
                .policy(Policy.Builder.newInstance().build())
                .build();
    }

    private void saveContractDefinition(String policyUid, String assetId) {
        String contractDefinitionId = "the-contract-definition";

        var contractDefinition = ContractDefinition.Builder.newInstance()
                .id(contractDefinitionId)
                .accessPolicyId(policyUid)
                .contractPolicyId(policyUid)
                .assetsSelectorCriterion(criterion(Asset.PROPERTY_ID, "=", assetId))
                .build();

        contractStore.save(contractDefinition);
    }
}