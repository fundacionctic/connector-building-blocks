package eu.datacellar.connector;

import java.util.List;
import java.util.Optional;

import org.eclipse.edc.connector.controlplane.contract.spi.types.agreement.ContractAgreement;
import org.eclipse.edc.policy.engine.spi.AtomicConstraintFunction;
import org.eclipse.edc.policy.engine.spi.PolicyContext;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.spi.agent.ParticipantAgent;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.types.TypeManager;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * A policy function that implements the authorization flow of Data Cellar.
 */
public class AuthorizationConstraintFunction implements AtomicConstraintFunction<Permission> {

    /** Key used to access verifiable presentation claims */
    private static final String CLAIMS_KEY_VERIFIABLE_PRESENTATION = "vp";
    private static final String VP_HOLDER = "holder";
    private static final String VP_VC = "verifiableCredential";
    private static final String VP_VC_CREDENTIAL_SUBJECT = "credentialSubject";
    private static final String VP_VC_CREDENTIAL_SUBJECT_DID = "id";

    /**
     * The constraint identifier used in ODRL policies.
     * This value should be referenced in policy definitions when using this
     * constraint.
     */
    public static final String KEY = "https://ctic.es/odrl/constraint/authorization";

    /** Monitor for logging */
    private Monitor monitor;

    /** Type manager for JSON serialization */
    private TypeManager typeManager;

    /** List of DIDs that are implicitly trusted */
    private List<String> implicitlyTrustedDids;

    /** Policy Decision Point API client */
    private Optional<PolicyDecisionPointAPI> policyDecisionPointAPI;

    /**
     * Creates a new AuthorizationConstraintFunction with a Policy Decision Point
     * API.
     *
     * @param monitor                The EDC monitor for logging
     * @param typeManager            Type manager for JSON serialization
     * @param implicitlyTrustedDids  List of DIDs that are implicitly trusted
     * @param policyDecisionPointAPI Optional Policy Decision Point API client
     */
    public AuthorizationConstraintFunction(Monitor monitor, TypeManager typeManager, List<String> implicitlyTrustedDids,
            Optional<PolicyDecisionPointAPI> policyDecisionPointAPI) {
        this.monitor = monitor;
        this.typeManager = typeManager;
        this.implicitlyTrustedDids = implicitlyTrustedDids;
        this.policyDecisionPointAPI = policyDecisionPointAPI;
    }

    /**
     * Creates a new AuthorizationConstraintFunction without a Policy Decision Point
     * API.
     *
     * @param monitor               The EDC monitor for logging
     * @param typeManager           Type manager for JSON serialization
     * @param implicitlyTrustedDids List of DIDs that are implicitly trusted
     */
    public AuthorizationConstraintFunction(Monitor monitor, TypeManager typeManager,
            List<String> implicitlyTrustedDids) {
        this(monitor, typeManager, implicitlyTrustedDids, Optional.empty());
    }

    /**
     * Checks if the DID in the Verifiable Presentation is one of the implicitly
     * trusted DIDs.
     * 
     * @param vpJson The Verifiable Presentation as a JSON object
     * @return true if the DID in the VP matches one of the implicitly trusted DIDs
     *         and the holder matches the subject DID,
     *         false otherwise
     */
    private boolean isImplicitlyTrustedDID(JSONObject vpJson) {
        monitor.debug("Checking if the participant is one of the implicitly trusted DIDs: %s"
                .formatted(implicitlyTrustedDids));

        String holder = vpJson.optString(VP_HOLDER, null);

        if (holder == null) {
            monitor.debug("VP holder is null");
            return false;
        }

        JSONArray vcs = vpJson.optJSONArray(VP_VC);

        if (vcs == null || vcs.length() == 0) {
            monitor.debug("No verifiable credentials found in VP");
            return false;
        }

        JSONObject firstVC = vcs.optJSONObject(0);

        if (firstVC == null) {
            monitor.debug("First VC is null or not a JSON object");
            return false;
        }

        JSONObject credentialSubject = firstVC.optJSONObject(VP_VC_CREDENTIAL_SUBJECT);

        if (credentialSubject == null) {
            monitor.debug("Credential subject is null");
            return false;
        }

        String subjectDID = credentialSubject.optString(VP_VC_CREDENTIAL_SUBJECT_DID, null);

        if (subjectDID == null) {
            monitor.debug("Subject DID is null");
            return false;
        }

        boolean isTrusted = subjectDID.equals(holder) && implicitlyTrustedDids.contains(subjectDID);

        if (isTrusted) {
            monitor.info("%s :: Participant '%s' is implicitly trusted".formatted(KEY, subjectDID));
        } else {
            monitor.debug("%s :: Participant '%s' is not implicitly trusted".formatted(KEY, subjectDID));
        }

        return isTrusted;
    }

    /**
     * Implements the authorization constraint function.
     * 
     * @param operator   The operator to apply (not used in current implementation)
     * @param rightValue The right-hand value to compare against (not used in
     *                   current implementation)
     * @param rule       The permission rule being evaluated
     * @param context    The policy evaluation context
     * @return true if authorization passes, false otherwise
     */
    @Override
    public boolean evaluate(Operator operator, Object rightValue, Permission rule, PolicyContext context) {
        ContractAgreement agreement = context.getContextData(ContractAgreement.class);

        if (agreement == null) {
            monitor.warning("%s :: Contract agreement is not available".formatted(KEY));
            return false;
        }

        ParticipantAgent agent = context.getContextData(ParticipantAgent.class);

        if (agent == null) {
            monitor.warning("%s :: Participant agent is not available".formatted(KEY));
            return false;
        }

        Object vp = agent.getClaims().getOrDefault(CLAIMS_KEY_VERIFIABLE_PRESENTATION, null);

        if (vp == null) {
            monitor.warning("%s :: Participant agent does not have a Verifiable Presentation claim".formatted(KEY));
            return false;
        }

        JSONObject vpJson = new JSONObject((String) vp);

        if (isImplicitlyTrustedDID(vpJson)) {
            return true;
        }

        String policyJsonString = typeManager.writeValueAsString(agreement.getPolicy());
        String agreementId = agreement.getId();
        String vpJsonString = vpJson.toString();

        if (policyDecisionPointAPI.isPresent()) {
            return policyDecisionPointAPI.get().requestAuthorizationDecision(policyJsonString, agreementId,
                    vpJsonString);
        } else {
            monitor.warning("%s :: PDP API is not available: Skipping authorization check".formatted(KEY));
            return true;
        }
    }
}
