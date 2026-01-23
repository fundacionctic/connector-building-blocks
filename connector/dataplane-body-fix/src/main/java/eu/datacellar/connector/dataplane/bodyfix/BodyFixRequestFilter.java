package eu.datacellar.connector.dataplane.bodyfix;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

import org.eclipse.edc.spi.monitor.Monitor;

import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.ext.Provider;

/**
 * JAX-RS filter that encodes binary request bodies to base64 to prevent
 * corruption during EDC's internal processing.
 *
 * <p>EDC's Data Plane converts request bodies to String internally, which
 * corrupts binary data (e.g., multipart boundaries with CRLF sequences).
 * This filter works around the issue by:
 * <ol>
 *   <li>Detecting requests with binary content types (configurable)</li>
 *   <li>Reading the raw bytes from the entity stream</li>
 *   <li>Encoding them as base64 with a marker prefix</li>
 *   <li>Replacing the entity stream with the encoded version</li>
 * </ol>
 *
 * <p>The corresponding {@link BodyFixHttpDataSource} detects the marker
 * and decodes the body before sending to the backend.
 *
 * <p>This filter is registered on the "public" web context by the
 * {@link BodyFixExtension}.
 */
@Provider
public class BodyFixRequestFilter implements ContainerRequestFilter {

    private final BodyFixConfig config;
    private final Monitor monitor;

    /**
     * Creates a new filter.
     *
     * @param config  the extension configuration
     * @param monitor the EDC monitor for logging
     */
    public BodyFixRequestFilter(BodyFixConfig config, Monitor monitor) {
        this.config = config;
        this.monitor = monitor;
    }

    @Override
    public void filter(ContainerRequestContext requestContext) throws IOException {
        if (!config.isEnabled()) {
            return;
        }

        String contentType = requestContext.getHeaderString("Content-Type");

        if (!config.matchesContentType(contentType)) {
            monitor.debug(() -> String.format(
                    "[BodyFix] Skipping encoding for content type: %s", contentType));
            return;
        }

        // Read the raw bytes from the entity stream
        byte[] rawBytes = requestContext.getEntityStream().readAllBytes();

        if (rawBytes.length == 0) {
            monitor.debug(() -> "[BodyFix] Empty body, skipping encoding");
            return;
        }

        monitor.debug(() -> String.format(
                "[BodyFix] Encoding %d bytes for content type: %s", rawBytes.length, contentType));

        // Base64 encode the bytes (no line breaks)
        String base64Encoded = Base64.getEncoder().encodeToString(rawBytes);

        // Prepend the marker
        String markedBody = config.getMarker() + base64Encoded;

        // Replace the entity stream with the encoded version
        byte[] encodedBytes = markedBody.getBytes(StandardCharsets.UTF_8);
        requestContext.setEntityStream(new ByteArrayInputStream(encodedBytes));

        monitor.debug(() -> String.format(
                "[BodyFix] Encoded body from %d bytes to %d bytes (base64 with marker)",
                rawBytes.length, encodedBytes.length));
    }
}
