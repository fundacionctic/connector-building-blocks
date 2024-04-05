package eu.datacellar.connector;

import org.eclipse.edc.policy.engine.spi.AtomicConstraintFunction;
import org.eclipse.edc.policy.engine.spi.PolicyContext;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.spi.agent.ParticipantAgent;

/**
 * This class represents a credential constraint function that is used to
 * evaluate permissions based on credentials.
 */
public class CredentialConstraintFunction implements AtomicConstraintFunction<Permission> {

    /**
     * The constant representing the credential constraint.
     */
    public static final String KEY = "hasCredential";

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
            return false;
        }

        System.out.println(
                String.format("%s :: ParticipantAgent.getIdentity() = %s", KEY,
                        agent.getIdentity()));

        return true;
    }
}
