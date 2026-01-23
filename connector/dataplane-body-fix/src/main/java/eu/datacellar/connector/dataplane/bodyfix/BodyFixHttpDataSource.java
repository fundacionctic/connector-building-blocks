package eu.datacellar.connector.dataplane.bodyfix;

import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParams;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult;
import org.eclipse.edc.http.spi.EdcHttpClient;
import org.eclipse.edc.spi.EdcException;
import org.eclipse.edc.spi.monitor.Monitor;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Stream;

import static java.lang.String.format;
import static org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress.OCTET_STREAM;
import static org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult.error;
import static org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult.success;

/**
 * Custom HTTP DataSource that detects and decodes base64-encoded bodies
 * that were marked by {@link BodyFixRequestFilter}.
 *
 * <p>This data source works by:
 * <ol>
 *   <li>Checking if the request body starts with the configured marker</li>
 *   <li>If marked, stripping the marker and base64-decoding to raw bytes</li>
 *   <li>Creating an OkHttp request with the raw binary body</li>
 *   <li>Executing the request and returning the response stream</li>
 * </ol>
 *
 * <p>If the body is not marked, it falls back to standard string body handling.
 */
public class BodyFixHttpDataSource implements DataSource {

    private static final int FORBIDDEN = 401;
    private static final int NOT_AUTHORIZED = 403;
    private static final int NOT_FOUND = 404;
    private static final String SLASH = "/";

    private String name;
    private HttpRequestParams params;
    private String requestId;
    private Monitor monitor;
    private EdcHttpClient httpClient;
    private BodyFixConfig config;

    private final AtomicReference<ResponseBodyStream> responseBodyStream = new AtomicReference<>();

    private BodyFixHttpDataSource() {
    }

    @Override
    public StreamResult<Stream<Part>> openPartStream() {
        var request = buildRequest();
        monitor.debug(() -> "Executing HTTP request: " + request.url());

        try {
            // NB: Do not close the response as the body input stream needs to be read
            // after this method returns. The response closes the body stream.
            Response response = httpClient.execute(request);

            if (response.isSuccessful()) {
                var body = response.body();
                if (body == null) {
                    throw new EdcException(format(
                            "Received empty response body transferring HTTP data for request %s: %s",
                            requestId, response.code()));
                }

                var stream = body.byteStream();
                responseBodyStream.set(new ResponseBodyStream(body, stream));
                var mediaType = Optional.ofNullable(body.contentType())
                        .map(MediaType::toString)
                        .orElse(OCTET_STREAM);

                return success(Stream.of(new HttpPart(name, stream, mediaType)));
            } else {
                try {
                    if (NOT_AUTHORIZED == response.code() || FORBIDDEN == response.code()) {
                        return StreamResult.notAuthorized();
                    } else if (NOT_FOUND == response.code()) {
                        return StreamResult.notFound();
                    } else {
                        return error(format("Received code transferring HTTP data: %s - %s.",
                                response.code(), response.message()));
                    }
                } finally {
                    try {
                        response.close();
                    } catch (Exception e) {
                        monitor.severe("Error closing failed response", e);
                    }
                }
            }
        } catch (IOException e) {
            throw new EdcException(e);
        }
    }

    /**
     * Builds the OkHttp request, handling base64 decoding if the body is marked.
     */
    private Request buildRequest() {
        String body = params.getBody();
        byte[] bodyBytes = null;
        String contentType = params.getContentType();

        if (body != null && config != null && body.startsWith(config.getMarker())) {
            // Decode the base64-encoded body
            String encoded = body.substring(config.getMarker().length());
            bodyBytes = Base64.getDecoder().decode(encoded);

            int originalLen = body.length();
            int decodedLen = bodyBytes.length;
            monitor.debug(() -> String.format(
                    "[BodyFix] Decoded body from %d chars to %d bytes",
                    originalLen, decodedLen));
        } else if (body != null) {
            // Fallback: use string body as UTF-8 bytes
            bodyBytes = body.getBytes(StandardCharsets.UTF_8);
        }

        // Build the URL
        okhttp3.HttpUrl.Builder urlBuilder = okhttp3.HttpUrl.parse(params.getBaseUrl()).newBuilder();

        String path = params.getPath();
        if (path != null && !path.isEmpty()) {
            String sanitizedPath = path.startsWith(SLASH) ? path.substring(1) : path;
            urlBuilder.addPathSegments(sanitizedPath);
        }

        String queryParams = params.getQueryParams();
        if (queryParams != null && !queryParams.isEmpty()) {
            urlBuilder.query(queryParams);
        }

        // Build the request
        Request.Builder requestBuilder = new Request.Builder()
                .url(urlBuilder.build());

        // Add headers
        params.getHeaders().forEach(requestBuilder::addHeader);

        // Set method and body
        RequestBody requestBody = null;
        if (bodyBytes != null && contentType != null) {
            requestBody = RequestBody.create(bodyBytes, MediaType.parse(contentType));
        }

        requestBuilder.method(params.getMethod(), requestBody);

        return requestBuilder.build();
    }

    @Override
    public void close() {
        var bodyStream = responseBodyStream.get();
        if (bodyStream != null) {
            bodyStream.responseBody().close();
            try {
                bodyStream.stream().close();
            } catch (IOException e) {
                // do nothing
            }
        }
    }

    private record ResponseBodyStream(ResponseBody responseBody, InputStream stream) {
    }

    /**
     * Represents a part of the HTTP response.
     */
    private record HttpPart(String name, InputStream content, String mediaType) implements Part {

        @Override
        public String name() {
            return name;
        }

        @Override
        public InputStream openStream() {
            return content;
        }

        @Override
        public String mediaType() {
            return mediaType;
        }

        @Override
        public long size() {
            return SIZE_UNKNOWN;
        }
    }

    /**
     * Builder for BodyFixHttpDataSource.
     */
    public static class Builder {
        private final BodyFixHttpDataSource dataSource;

        public static Builder newInstance() {
            return new Builder();
        }

        private Builder() {
            dataSource = new BodyFixHttpDataSource();
        }

        public Builder params(HttpRequestParams params) {
            dataSource.params = params;
            return this;
        }

        public Builder name(String name) {
            dataSource.name = name;
            return this;
        }

        public Builder requestId(String requestId) {
            dataSource.requestId = requestId;
            return this;
        }

        public Builder httpClient(EdcHttpClient httpClient) {
            dataSource.httpClient = httpClient;
            return this;
        }

        public Builder monitor(Monitor monitor) {
            dataSource.monitor = monitor;
            return this;
        }

        public Builder config(BodyFixConfig config) {
            dataSource.config = config;
            return this;
        }

        public BodyFixHttpDataSource build() {
            Objects.requireNonNull(dataSource.requestId, "requestId");
            Objects.requireNonNull(dataSource.httpClient, "httpClient");
            Objects.requireNonNull(dataSource.monitor, "monitor");
            Objects.requireNonNull(dataSource.config, "config");
            return dataSource;
        }
    }
}
