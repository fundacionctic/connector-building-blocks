package eu.datacellar.connector.dataplane.bodyfix;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import org.eclipse.edc.spi.system.ServiceExtensionContext;

/**
 * Configuration settings for the Body Fix extension.
 *
 * This extension addresses binary body corruption in EDC Data Plane proxying
 * by encoding binary payloads to base64 before EDC processes them, then
 * decoding them before sending to the backend.
 */
public class BodyFixConfig {

    /**
     * Setting key to enable/disable the extension.
     * Default: true
     */
    public static final String SETTING_ENABLED = "edc.dataplane.bodyfix.enabled";

    /**
     * Setting key for content types to encode.
     * Comma-separated list of content types.
     * Default: multipart/form-data,application/octet-stream
     */
    public static final String SETTING_CONTENT_TYPES = "edc.dataplane.bodyfix.contentTypes";

    /**
     * Setting key for the marker prefix used to identify encoded bodies.
     * Default: __EDC_B64:
     */
    public static final String SETTING_MARKER = "edc.dataplane.bodyfix.marker";

    /**
     * The data address type used to route requests to the body fix factory.
     * This is different from the standard "HttpData" type to avoid factory
     * selection conflicts.
     */
    public static final String HTTP_DATA_FIXED_TYPE = "HttpDataFixed";

    private static final String DEFAULT_CONTENT_TYPES = "multipart/form-data,application/octet-stream";
    private static final String DEFAULT_MARKER = "__EDC_B64:";
    private static final boolean DEFAULT_ENABLED = true;

    private final boolean enabled;
    private final Set<String> contentTypes;
    private final String marker;

    /**
     * Creates a new configuration from the service extension context.
     *
     * @param context the service extension context
     */
    public BodyFixConfig(ServiceExtensionContext context) {
        this.enabled = Boolean.parseBoolean(
                context.getSetting(SETTING_ENABLED, String.valueOf(DEFAULT_ENABLED)));

        String contentTypesStr = context.getSetting(SETTING_CONTENT_TYPES, DEFAULT_CONTENT_TYPES);
        this.contentTypes = new HashSet<>(Arrays.asList(contentTypesStr.split(",")));

        this.marker = context.getSetting(SETTING_MARKER, DEFAULT_MARKER);
    }

    /**
     * Creates a configuration with explicit values (for testing).
     *
     * @param enabled      whether the extension is enabled
     * @param contentTypes the set of content types to encode
     * @param marker       the marker prefix
     */
    public BodyFixConfig(boolean enabled, Set<String> contentTypes, String marker) {
        this.enabled = enabled;
        this.contentTypes = contentTypes;
        this.marker = marker;
    }

    /**
     * Returns whether the extension is enabled.
     *
     * @return true if the extension is enabled
     */
    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Returns the set of content types that should be encoded.
     *
     * @return the content types
     */
    public Set<String> getContentTypes() {
        return contentTypes;
    }

    /**
     * Returns the marker prefix used to identify encoded bodies.
     *
     * @return the marker
     */
    public String getMarker() {
        return marker;
    }

    /**
     * Checks if the given content type matches any of the configured types.
     * Uses prefix matching to handle content types with parameters
     * (e.g., "multipart/form-data; boundary=...").
     *
     * @param contentType the content type to check
     * @return true if the content type should be encoded
     */
    public boolean matchesContentType(String contentType) {
        if (contentType == null) {
            return false;
        }

        String normalizedContentType = contentType.toLowerCase().trim();

        for (String configuredType : contentTypes) {
            String normalizedConfigured = configuredType.toLowerCase().trim();
            if (normalizedContentType.startsWith(normalizedConfigured)) {
                return true;
            }
        }

        return false;
    }
}
