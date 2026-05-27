package eu.datacellar.connector;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.eclipse.edc.connector.dataplane.http.spi.HttpDataAddress;
import org.eclipse.edc.connector.dataplane.http.spi.HttpParamsDecorator;
import org.eclipse.edc.connector.dataplane.http.spi.HttpRequestParams.Builder;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowStartMessage;

import okhttp3.HttpUrl;

/**
 * Resolves OpenAPI path parameter templates stored in the dataAddress.
 *
 * For assets with path parameters (e.g. /items/{id}), the path template is
 * stored as a dataAddress property instead of a literal path. This decorator
 * substitutes each {variable} with the matching consumer query parameter and
 * removes those keys from the forwarded query string.
 */
public class PathTemplateHttpParamsDecorator implements HttpParamsDecorator {

    public static final String PATH_TEMPLATE_PROP = "pathTemplate";
    private static final Pattern PATH_PARAM_PATTERN = Pattern.compile("\\{([^}]+)\\}");
    private static final String PROP_QUERY_PARAMS = "queryParams";

    private final Monitor monitor;

    public PathTemplateHttpParamsDecorator(Monitor monitor) {
        this.monitor = monitor;
    }

    @Override
    public Builder decorate(DataFlowStartMessage request, HttpDataAddress address, Builder builder) {
        String template = address.getStringProperty(PATH_TEMPLATE_PROP);
        if (template == null || template.isBlank()) {
            return builder;
        }

        monitor.debug("Resolving path template: %s".formatted(template));

        String queryParams = request.getProperties().getOrDefault(PROP_QUERY_PARAMS, null);
        Map<String, List<String>> queryMap = parseQueryParams(queryParams);

        Matcher matcher = PATH_PARAM_PATTERN.matcher(template);
        String resolvedPath = template;
        List<String> substitutedKeys = new ArrayList<>();

        while (matcher.find()) {
            String varName = matcher.group(1);
            List<String> values = queryMap.get(varName);

            if (values == null || values.isEmpty()) {
                monitor.warning("Path parameter '%s' not found in query params for template '%s'"
                        .formatted(varName, template));
                continue;
            }

            resolvedPath = resolvedPath.replace("{" + varName + "}", values.get(0));
            substitutedKeys.add(varName);
        }

        monitor.debug("Resolved path: %s".formatted(resolvedPath));
        builder.path(resolvedPath);

        substitutedKeys.forEach(queryMap::remove);
        builder.queryParams(buildQueryString(queryMap));

        return builder;
    }

    private Map<String, List<String>> parseQueryParams(String queryParams) {
        Map<String, List<String>> queryMap = new HashMap<>();
        if (queryParams == null || queryParams.isBlank()) {
            return queryMap;
        }
        HttpUrl url = HttpUrl.parse("https://example.com?" + queryParams);
        if (url == null) {
            return queryMap;
        }
        for (int i = 0, size = url.querySize(); i < size; i++) {
            queryMap.computeIfAbsent(url.queryParameterName(i), k -> new ArrayList<>())
                    .add(url.queryParameterValue(i));
        }
        return queryMap;
    }

    private String buildQueryString(Map<String, List<String>> queryMap) {
        if (queryMap.isEmpty()) {
            return null;
        }
        HttpUrl.Builder urlBuilder = new HttpUrl.Builder().scheme("https").host("example.com");
        queryMap.forEach((key, values) -> values.forEach(v -> urlBuilder.addQueryParameter(key, v)));
        return urlBuilder.build().query();
    }
}
