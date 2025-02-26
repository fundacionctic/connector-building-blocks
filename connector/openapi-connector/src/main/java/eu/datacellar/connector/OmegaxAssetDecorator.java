package eu.datacellar.connector;

import java.util.Map;

import org.eclipse.edc.connector.controlplane.asset.spi.domain.Asset;
import org.eclipse.edc.spi.monitor.Monitor;

import io.swagger.v3.oas.models.Operation;

/**
 * Decorator class that adds Omega-X Marketplace specific properties to EDC
 * assets.
 */
public class OmegaxAssetDecorator {
    private static final String URI_DC_LANGUAGE = "http://purl.org/dc/terms/language";
    private static final String URI_DC_TITLE = "http://purl.org/dc/terms/title";
    private static final String URI_DC_DESCRIPTION = "http://purl.org/dc/terms/description";
    private static final String URI_DC_PUBLISHER = "http://purl.org/dc/terms/publisher";
    private static final String URI_FOAF_HOMEPAGE = "http://xmlns.com/foaf/0.1/homepage";
    private static final String URI_DC_CREATOR = "http://purl.org/dc/terms/creator";
    private static final String URI_FOAF_NAME = "http://xmlns.com/foaf/0.1/name";
    private static final String URI_W3_LANGUAGE_EN = "http://www.w3id.org/idsa/code/EN";

    /**
     * Context class that holds all necessary information for asset decoration.
     * This class follows the Builder pattern to ensure all required fields are
     * provided.
     */
    public static class Context {
        private final Monitor monitor;
        private final Operation operation;
        private final String path;
        private final String method;
        private final String baseUrl;
        private final String creatorName;
        private final String publisherHomepage;

        private Context(Builder builder) {
            this.monitor = builder.monitor;
            this.operation = builder.operation;
            this.path = builder.path;
            this.method = builder.method;
            this.baseUrl = builder.baseUrl;
            this.creatorName = builder.creatorName;
            this.publisherHomepage = builder.publisherHomepage;
        }

        /**
         * Builder class for Context.
         * Provides a fluent API for constructing Context instances.
         */
        public static class Builder {
            private Monitor monitor;
            private Operation operation;
            private String path;
            private String method;
            private String baseUrl;
            private String creatorName;
            private String publisherHomepage;

            /**
             * Sets the monitor for logging and debugging.
             * 
             * @param monitor The EDC monitor instance
             * @return The builder instance
             */
            public Builder monitor(Monitor monitor) {
                this.monitor = monitor;
                return this;
            }

            /**
             * Sets the OpenAPI operation.
             * 
             * @param operation The OpenAPI operation instance
             * @return The builder instance
             */
            public Builder operation(Operation operation) {
                this.operation = operation;
                return this;
            }

            /**
             * Sets the API endpoint path.
             * 
             * @param path The endpoint path
             * @return The builder instance
             */
            public Builder path(String path) {
                this.path = path;
                return this;
            }

            /**
             * Sets the HTTP method.
             * 
             * @param method The HTTP method (GET, POST, etc.)
             * @return The builder instance
             */
            public Builder method(String method) {
                this.method = method;
                return this;
            }

            /**
             * Sets the base URL for the API.
             * 
             * @param baseUrl The base URL
             * @return The builder instance
             */
            public Builder baseUrl(String baseUrl) {
                this.baseUrl = baseUrl;
                return this;
            }

            /**
             * Sets the creator name.
             * 
             * @param creatorName The creator name
             * @return The builder instance
             */
            public Builder creatorName(String creatorName) {
                this.creatorName = creatorName;
                return this;
            }

            /**
             * Sets the publisher homepage.
             * 
             * @param publisherHomepage The publisher homepage
             * @return The builder instance
             */
            public Builder publisherHomepage(String publisherHomepage) {
                this.publisherHomepage = publisherHomepage;
                return this;
            }

            /**
             * Builds and validates a new Context instance.
             * 
             * @return A new Context instance
             * @throws IllegalArgumentException if any required field is null
             */
            public Context build() {
                if (monitor == null || operation == null || path == null || method == null || baseUrl == null) {
                    throw new IllegalArgumentException("Some required fields are missing");
                }

                return new Context(this);
            }
        }

        /**
         * @return The monitor instance
         */
        public Monitor getMonitor() {
            return monitor;
        }

        /**
         * @return The OpenAPI operation
         */
        public Operation getOperation() {
            return operation;
        }

        /**
         * @return The endpoint path
         */
        public String getPath() {
            return path;
        }

        /**
         * @return The HTTP method
         */
        public String getMethod() {
            return method;
        }

        /**
         * @return The base URL
         */
        public String getBaseUrl() {
            return baseUrl;
        }

        /**
         * @return The creator name
         */
        public String getCreatorName() {
            return creatorName;
        }

        /**
         * @return The publisher homepage
         */
        public String getPublisherHomepage() {
            return publisherHomepage;
        }
    }

    /**
     * Decorates an EDC asset builder with Omega-X Marketplace specific properties.
     * 
     * @param builder The asset builder to decorate
     * @param context The context containing information needed for decoration
     * @return The decorated asset builder
     * @throws IllegalArgumentException if builder or context is null
     */
    public static Asset.Builder decorate(Asset.Builder builder, Context context) {
        if (builder == null) {
            throw new IllegalArgumentException("Asset builder cannot be null");
        }

        if (context == null) {
            throw new IllegalArgumentException("Context cannot be null");
        }

        context.getMonitor().debug("Decorating asset with Omega-X properties for %s %s".formatted(
                context.getMethod(),
                context.getPath()));

        Operation operation = context.getOperation();
        String description = operation.getDescription();
        String summary = operation.getSummary() != null ? operation.getSummary() : operation.getOperationId();
        String creatorName = context.getCreatorName();
        String publisherHomepage = context.getPublisherHomepage();

        if (description != null) {
            builder = builder.property(URI_DC_DESCRIPTION, description);
        }

        if (publisherHomepage != null) {
            builder = builder.property(URI_DC_PUBLISHER, Map.of(URI_FOAF_HOMEPAGE, publisherHomepage));
        }

        if (creatorName != null) {
            builder = builder.property(URI_DC_CREATOR, Map.of(URI_FOAF_NAME, creatorName));
        }

        return builder
                .property(URI_DC_LANGUAGE, URI_W3_LANGUAGE_EN)
                .property(URI_DC_TITLE, summary);
    }
}