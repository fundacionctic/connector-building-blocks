package eu.datacellar.connector;

import java.util.Map;
import java.util.UUID;

import org.eclipse.edc.connector.controlplane.policy.spi.PolicyDefinition;
import org.eclipse.edc.policy.model.Action;
import org.eclipse.edc.policy.model.AtomicConstraint;
import org.eclipse.edc.policy.model.LiteralExpression;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.policy.model.Policy;
import org.eclipse.edc.spi.monitor.Monitor;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * A builder class for creating EDC policy definitions with authorization and
 * credential constraints.
 * This class helps in constructing policies that can be used to control access
 * to resources
 * in the Eclipse Dataspace Connector (EDC) framework.
 */
public class PolicyBuilder {
    private static final String ODRL_USE_ACTION_ATTRIBUTE = "use";

    private final Monitor monitor;
    private final boolean enableAuthorization;

    /**
     * Constructs a new PolicyBuilder instance.
     *
     * @param monitor             The EDC monitor for logging purposes
     * @param enableAuthorization Flag to enable/disable authorization constraints
     *                            in the policy
     */
    public PolicyBuilder(Monitor monitor, boolean enableAuthorization) {
        this.monitor = monitor;
        this.enableAuthorization = enableAuthorization;
    }

    /**
     * Builds a PolicyDefinition based on the provided presentation definition.
     * The resulting policy includes authorization constraints (if enabled) and
     * credential constraints based on the presentation definition.
     *
     * @param presentationDefinition A map containing the presentation definition
     *                               that specifies
     *                               credential requirements. Can be null if no
     *                               credential
     *                               constraints are needed.
     * @return A new PolicyDefinition instance with the specified constraints
     */
    public PolicyDefinition buildPolicyDefinition(Map<String, Object> presentationDefinition) {
        Policy.Builder policyBuilder = Policy.Builder.newInstance();
        Action useAction = Action.Builder.newInstance().type(ODRL_USE_ACTION_ATTRIBUTE).build();

        if (enableAuthorization) {
            addAuthorizationConstraint(policyBuilder, useAction);
        }

        if (presentationDefinition != null) {
            addCredentialConstraint(policyBuilder, useAction, presentationDefinition);
        }

        return PolicyDefinition.Builder.newInstance()
                .id(UUID.randomUUID().toString())
                .policy(policyBuilder.build())
                .build();
    }

    /**
     * Adds an authorization constraint to the policy.
     * The constraint requires the authorization function to evaluate to 'true'
     * for the policy to be satisfied.
     *
     * @param policyBuilder The policy builder to add the constraint to
     * @param useAction     The use action to associate with the permission
     */
    private void addAuthorizationConstraint(Policy.Builder policyBuilder, Action useAction) {
        monitor.debug("Enabling authorization constraint");

        AtomicConstraint authorizationConstraint = AtomicConstraint.Builder.newInstance()
                .leftExpression(new LiteralExpression(AuthorizationConstraintFunction.KEY))
                .operator(Operator.EQ)
                .rightExpression(new LiteralExpression("true"))
                .build();

        Permission authorizationPermission = Permission.Builder.newInstance()
                .action(useAction)
                .constraint(authorizationConstraint)
                .build();

        policyBuilder.permission(authorizationPermission);
    }

    /**
     * Adds a credential constraint to the policy based on the presentation
     * definition.
     * The constraint specifies which credential types are acceptable.
     *
     * @param policyBuilder          The policy builder to add the constraint to
     * @param useAction              The use action to associate with the permission
     * @param presentationDefinition The presentation definition containing
     *                               credential requirements
     */
    private void addCredentialConstraint(Policy.Builder policyBuilder, Action useAction,
            Map<String, Object> presentationDefinition) {
        String credentialTypePattern = extractCredentialTypePattern(presentationDefinition);

        AtomicConstraint credentialConstraint = AtomicConstraint.Builder.newInstance()
                .leftExpression(new LiteralExpression(CredentialConstraintFunction.KEY))
                .operator(Operator.IN)
                .rightExpression(new LiteralExpression(credentialTypePattern))
                .build();

        Permission credentialPermission = Permission.Builder.newInstance()
                .action(useAction)
                .constraint(credentialConstraint)
                .build();

        policyBuilder.permission(credentialPermission);
    }

    /**
     * Extracts the credential type pattern from the presentation definition.
     * This method parses the presentation definition JSON structure to find
     * the pattern that specifies acceptable credential types.
     *
     * @param presentationDefinition The presentation definition to extract the
     *                               pattern from
     * @return A string containing the credential type pattern
     * @throws IllegalArgumentException if the presentation definition is invalid or
     *                                  missing required fields
     */
    private String extractCredentialTypePattern(Map<String, Object> presentationDefinition) {
        JSONObject presDefJsonObj = new JSONObject(presentationDefinition);
        JSONArray inputDescriptors = presDefJsonObj.optJSONArray("input_descriptors");

        if (inputDescriptors == null || inputDescriptors.length() == 0) {
            throw new IllegalArgumentException(
                    "Invalid presentation definition: input_descriptors is missing or empty");
        }

        JSONObject inputDescriptor = inputDescriptors.getJSONObject(0);
        JSONObject constraints = inputDescriptor.optJSONObject("constraints");

        if (constraints == null) {
            throw new IllegalArgumentException("Invalid presentation definition: constraints is missing");
        }

        JSONArray fields = constraints.optJSONArray("fields");

        if (fields == null || fields.length() == 0) {
            throw new IllegalArgumentException("Invalid presentation definition: fields is missing or empty");
        }

        JSONObject field = fields.getJSONObject(0);
        JSONArray paths = field.optJSONArray("path");

        if (paths == null || paths.length() == 0) {
            throw new IllegalArgumentException("Invalid presentation definition: path is missing or empty");
        }

        String credentialType = paths.getString(0);

        if (!credentialType.equals("$.type")) {
            throw new IllegalArgumentException("Invalid presentation definition: path is not equal to $.type");
        }

        JSONObject filter = field.optJSONObject("filter");

        if (filter == null) {
            throw new IllegalArgumentException("Invalid presentation definition: filter is missing");
        }

        return filter.getString("pattern");
    }
}