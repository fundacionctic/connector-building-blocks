package datacellar.connector.extension;

import java.io.File;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

import org.eclipse.edc.connector.contract.spi.offer.store.ContractDefinitionStore;
import org.eclipse.edc.connector.contract.spi.types.offer.ContractDefinition;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataTransferExecutorServiceContainer;
import org.eclipse.edc.connector.dataplane.spi.pipeline.PipelineService;
import org.eclipse.edc.connector.policy.spi.PolicyDefinition;
import org.eclipse.edc.connector.policy.spi.store.PolicyDefinitionStore;
import org.eclipse.edc.policy.model.Action;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.policy.model.Policy;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.spi.asset.AssetIndex;
import org.eclipse.edc.spi.asset.AssetSelectorExpression;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.domain.DataAddress;
import org.eclipse.edc.spi.types.domain.asset.Asset;
import org.json.JSONObject;

/**
 * Extension that registers a {@link JsonTransferDataSourceFactory} and a
 * {@link JsonTransferDataSinkFactory} with the
 * {@link PipelineService}.
 */
public class JsonTransferExtension implements ServiceExtension {

    /**
     * The type of the data source and sink.
     */
    public static final String JSON_TYPE = "jsonfile";

    /**
     * The name of the policy.
     */
    public static final String USE_POLICY = "use-eu";

    /**
     * The asset ID.
     */
    public static final String ASSET_ID = UUID.randomUUID().toString();

    /**
     * The contract definition ID.
     */
    public static final String CONTRACT_DEFINITION_ID = UUID.randomUUID().toString();

    private static final String USE_ACTION_TYPE = "USE";

    @Inject
    private ContractDefinitionStore contractStore;

    @Inject
    private AssetIndex assetIndex;

    @Inject
    private PipelineService pipelineService;

    @Inject
    private DataTransferExecutorServiceContainer executorContainer;

    @Inject
    private PolicyDefinitionStore policyStore;

    @Override
    public void initialize(ServiceExtensionContext context) {
        var monitor = context.getMonitor();

        var sourceFactory = new JsonTransferDataSourceFactory();
        pipelineService.registerFactory(sourceFactory);

        var sinkFactory = new JsonTransferDataSinkFactory(monitor, executorContainer.getExecutorService(), 5);
        pipelineService.registerFactory(sinkFactory);

        var policy = createPolicy();
        policyStore.save(policy);

        try {
            registerDataEntries(context);
        } catch (IOException e) {
            context.getMonitor().severe(e.toString());
        }

        registerContractDefinition(policy.getUid());

        context.getMonitor().info(String.format("Initialized extension: %s", this.getClass().getName()));
    }

    private PolicyDefinition createPolicy() {
        var usePermission = Permission.Builder.newInstance()
                .action(Action.Builder.newInstance().type(USE_ACTION_TYPE).build())
                .build();

        return PolicyDefinition.Builder.newInstance()
                .id(USE_POLICY)
                .policy(Policy.Builder.newInstance()
                        .permission(usePermission)
                        .build())
                .build();
    }

    private void registerDataEntries(ServiceExtensionContext context) throws IOException {
        JSONObject jsonObject = new JSONObject();
        jsonObject.put("assetId", ASSET_ID);
        jsonObject.put("initDate", LocalDateTime.now().format(DateTimeFormatter.ISO_DATE_TIME));
        jsonObject.put("jvmName", ManagementFactory.getRuntimeMXBean().getVmName());

        File tempFile = File.createTempFile("datacellar-", ".json");
        tempFile.deleteOnExit();
        Files.write(tempFile.toPath(), jsonObject.toString().getBytes());
        context.getMonitor().info(String.format("Created temporary file: %s", tempFile.getAbsolutePath()));

        var dataAddress = DataAddress.Builder.newInstance()
                .property("type", JSON_TYPE)
                .property("path", tempFile.getParent())
                .property("filename", tempFile.getName())
                .build();

        var asset = Asset.Builder.newInstance().id(ASSET_ID).build();

        assetIndex.accept(asset, dataAddress);
    }

    @SuppressWarnings("deprecation")
    private void registerContractDefinition(String uid) {
        long yearSeconds = 3600 * 24 * 365;

        var contractDefinition = ContractDefinition.Builder.newInstance()
                .id(CONTRACT_DEFINITION_ID)
                .accessPolicyId(uid)
                .contractPolicyId(uid)
                .selectorExpression(AssetSelectorExpression.Builder.newInstance()
                        .whenEquals(Asset.PROPERTY_ID, ASSET_ID)
                        .build())
                .validity(yearSeconds)
                .build();

        contractStore.save(contractDefinition);
    }
}
