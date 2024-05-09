package eu.datacellar.connector;

import java.util.regex.Pattern;

import org.eclipse.edc.policy.engine.spi.AtomicConstraintFunction;
import org.eclipse.edc.policy.engine.spi.PolicyContext;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.spi.agent.ParticipantAgent;
import org.eclipse.edc.spi.monitor.Monitor;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * This class represents a credential constraint function that is used to
 * evaluate permissions based on credentials.
 */
public class CredentialConstraintFunction implements AtomicConstraintFunction<Permission> {
    private static final String CLAIMS_KEY_VERIFIABLE_PRESENTATION = "vp";
    private static final String VP_VCS_KEY = "verifiableCredential";

    /**
     * The constant representing the credential constraint.
     */
    public static final String KEY = "hasVerifiableCredentialType";

    private Monitor monitor;

    /**
     * Constructs a new instance of the CredentialConstraintFunction class with the
     * specified monitor.
     *
     * @param monitor The monitor used for tracking and logging.
     */
    public CredentialConstraintFunction(Monitor monitor) {
        this.monitor = monitor;
    }

    private boolean isCredentialTypePresent(String vpJsonStr, String expectedCredentialTypePattern) {
        Pattern compiledTypePattern = Pattern.compile(expectedCredentialTypePattern);
        JSONObject vpJsonObj = new JSONObject(vpJsonStr);
        JSONArray vcsArr = vpJsonObj.optJSONArray(VP_VCS_KEY);

        if (vcsArr == null) {
            throw new IllegalArgumentException("VP does not contain '%s' array.".formatted(VP_VCS_KEY));
        }

        for (int i = 0; i < vcsArr.length(); i++) {
            JSONObject vcObj = vcsArr.getJSONObject(i);
            JSONArray vcTypesArr = vcObj.optJSONArray("type");

            if (vcTypesArr == null) {
                continue;
            }

            for (int j = 0; j < vcTypesArr.length(); j++) {
                String vcType = vcTypesArr.getString(j);
                monitor.debug("Checking if '%s' matches '%s'".formatted(vcType, expectedCredentialTypePattern));

                if (compiledTypePattern.matcher(vcType).matches()) {
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * Evaluates the permission based on the credential constraint.
     *
     * @param operator   the operator used for evaluation
     * @param rightValue the right value used for evaluation
     * @param rule       the permission rule to evaluate
     * @param context    the policy context
     * @return true if the permission is evaluated successfully, false otherwise
     */
    @Override
    public boolean evaluate(Operator operator, Object rightValue, Permission rule, PolicyContext context) {
        ParticipantAgent agent = context.getContextData(ParticipantAgent.class);

        if (agent == null) {
            monitor.warning("Participant agent is not available.");
            return false;
        }

        monitor.debug("%s :: Participant agent identity: %s".formatted(KEY, agent.getIdentity()));

        Object vp = agent.getClaims().getOrDefault(CLAIMS_KEY_VERIFIABLE_PRESENTATION, null);

        if (vp == null) {
            monitor.warning("Participant agent does not have a verifiable presentation claim.");
            return false;
        }

        String vpJsonStr = (String) vp;
        String expectedCredentialTypePattern = (String) rightValue;

        monitor.debug("Checking VP for credential type '%s': %s".formatted(expectedCredentialTypePattern, vpJsonStr));

        return isCredentialTypePresent(vpJsonStr, expectedCredentialTypePattern);
    }
}
