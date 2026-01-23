package eu.datacellar.connector.dataplane.bodyfix;

import org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParamsProvider;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSourceFactory;
import org.eclipse.edc.http.spi.EdcHttpClient;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.result.Result;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowStartMessage;
import org.jetbrains.annotations.NotNull;

/**
 * Factory that creates {@link BodyFixHttpDataSource} instances for requests
 * with the "HttpDataFixed" data address type.
 *
 * <p>This factory is registered alongside the standard {@link org.eclipse.edc.connector.dataplane.http.pipeline.HttpDataSourceFactory}
 * but handles a different type ("HttpDataFixed" instead of "HttpData") to avoid
 * factory selection conflicts. Assets that need binary body preservation should
 * use the "HttpDataFixed" type in their data address.
 *
 * <p>The factory uses the shared {@link HttpRequestParamsProvider} so that
 * decorators registered by other extensions (like OpenAPICoreExtension) are
 * applied to requests.
 */
public class BodyFixHttpDataSourceFactory implements DataSourceFactory {

    private final EdcHttpClient httpClient;
    private final HttpRequestParamsProvider paramsProvider;
    private final BodyFixConfig config;
    private final Monitor monitor;

    /**
     * Creates a new factory.
     *
     * @param httpClient     the HTTP client for executing requests
     * @param paramsProvider the shared params provider (with decorators)
     * @param config         the extension configuration
     * @param monitor        the EDC monitor for logging
     */
    public BodyFixHttpDataSourceFactory(
            EdcHttpClient httpClient,
            HttpRequestParamsProvider paramsProvider,
            BodyFixConfig config,
            Monitor monitor) {
        this.httpClient = httpClient;
        this.paramsProvider = paramsProvider;
        this.config = config;
        this.monitor = monitor;
    }

    /**
     * Returns the supported data address type.
     * Uses "HttpDataFixed" to differentiate from the standard "HttpData" type
     * and avoid factory selection conflicts.
     *
     * @return the supported type
     */
    @Override
    public String supportedType() {
        return BodyFixConfig.HTTP_DATA_FIXED_TYPE;
    }

    @Override
    public @NotNull Result<Void> validateRequest(DataFlowStartMessage request) {
        try {
            createSource(request);
            return Result.success();
        } catch (Exception e) {
            return Result.failure("Failed to build BodyFixHttpDataSource: " + e.getMessage());
        }
    }

    @Override
    public DataSource createSource(DataFlowStartMessage request) {
        var dataAddress = HttpDataAddress.Builder.newInstance()
                .copyFrom(request.getSourceDataAddress())
                .build();

        monitor.debug(() -> String.format(
                "[BodyFix] Creating data source for request %s, address type: %s",
                request.getId(), dataAddress.getType()));

        return BodyFixHttpDataSource.Builder.newInstance()
                .httpClient(httpClient)
                .monitor(monitor)
                .requestId(request.getId())
                .name(dataAddress.getName())
                .params(paramsProvider.provideSourceParams(request))
                .config(config)
                .build();
    }
}
