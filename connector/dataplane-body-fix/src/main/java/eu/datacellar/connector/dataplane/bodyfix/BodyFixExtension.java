package eu.datacellar.connector.dataplane.bodyfix;

import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParamsProvider;
import org.eclipse.edc.connector.dataplane.spi.pipeline.PipelineService;
import org.eclipse.edc.http.spi.EdcHttpClient;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.web.spi.WebService;

/**
 * Extension that fixes binary body corruption in EDC Data Plane proxying.
 *
 * <p>EDC's Data Plane converts request bodies to String internally, which corrupts
 * binary data such as multipart form boundaries (CRLF sequences get mangled).
 * This extension provides a two-phase workaround:
 *
 * <ol>
 *   <li><b>Encode phase</b> ({@link BodyFixRequestFilter}): A JAX-RS filter on the
 *       public API encodes matching binary content types to base64 with a marker prefix,
 *       making the body safe for String conversion.</li>
 *   <li><b>Decode phase</b> ({@link BodyFixHttpDataSource}): A custom DataSource
 *       detects the marker and decodes the body back to raw bytes before sending
 *       to the backend.</li>
 * </ol>
 *
 * <h2>Configuration</h2>
 * <ul>
 *   <li>{@code edc.dataplane.bodyfix.enabled} - Enable/disable (default: true)</li>
 *   <li>{@code edc.dataplane.bodyfix.contentTypes} - Content types to encode (default: multipart/form-data,application/octet-stream)</li>
 *   <li>{@code edc.dataplane.bodyfix.marker} - Marker prefix (default: __EDC_B64:)</li>
 * </ul>
 *
 * <h2>Integration</h2>
 * <p>Assets that need binary body preservation must use the "HttpDataFixed" data
 * address type instead of the standard "HttpData" type. This routes requests to
 * the custom factory, avoiding conflicts with the built-in HTTP data source.
 *
 * @see BodyFixConfig
 * @see BodyFixRequestFilter
 * @see BodyFixHttpDataSourceFactory
 * @see BodyFixHttpDataSource
 */
@Extension(value = BodyFixExtension.NAME)
public class BodyFixExtension implements ServiceExtension {

    /**
     * The name of this extension.
     */
    public static final String NAME = "Data Plane Body Fix";

    @Inject
    private WebService webService;

    @Inject
    private PipelineService pipelineService;

    @Inject
    private HttpRequestParamsProvider paramsProvider;

    @Inject
    private EdcHttpClient httpClient;

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {
        Monitor monitor = context.getMonitor();
        BodyFixConfig config = new BodyFixConfig(context);

        if (!config.isEnabled()) {
            monitor.info("[BodyFix] Extension is disabled via configuration");
            return;
        }

        // Register the JAX-RS filter on the public API context
        // This encodes binary bodies to base64 before EDC processes them
        BodyFixRequestFilter filter = new BodyFixRequestFilter(config, monitor);
        webService.registerResource("public", filter);

        monitor.info(String.format(
                "[BodyFix] Registered request filter for content types: %s",
                config.getContentTypes()));

        // Register the custom data source factory
        // This handles requests with "HttpDataFixed" type and decodes the body
        BodyFixHttpDataSourceFactory factory = new BodyFixHttpDataSourceFactory(
                httpClient,
                paramsProvider,
                config,
                monitor);
        pipelineService.registerFactory(factory);

        monitor.info(String.format(
                "[BodyFix] Registered data source factory for type: %s",
                BodyFixConfig.HTTP_DATA_FIXED_TYPE));

        monitor.info("[BodyFix] Extension initialized successfully");
    }
}
