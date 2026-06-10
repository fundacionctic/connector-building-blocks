package eu.datacellar.connector;

import java.util.Set;
import java.util.TreeSet;

import org.eclipse.edc.policy.engine.spi.AtomicConstraintFunction;
import org.eclipse.edc.policy.engine.spi.PolicyContext;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.spi.agent.ParticipantAgent;
import org.eclipse.edc.spi.monitor.Monitor;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * A policy function that checks whether the counterparty's country or region of
 * origin is within the European Union.
 *
 * <p>
 * The check is resilient: it scans several well-known, ontology-aligned fields
 * across the Verifiable Credentials present in the counterparty's Verifiable
 * Presentation (the {@code vp} claim, which has already been cryptographically
 * verified against the trust anchor before policy evaluation). The discovered
 * values are normalized to ISO 3166-1 alpha-2 country codes and matched against
 * the set of EU-27 member states.
 *
 * <p>
 * Country codes are collected only from {@code credentialSubject} entries whose
 * {@code id} matches the counterparty (the VP holder / authenticated DID). The
 * upstream presentation validation only binds each credential's JWT {@code sub}
 * to the holder, not the embedded {@code credentialSubject.id}; binding here
 * prevents a holder from satisfying an EU-only policy with a credential that
 * describes a different (EU) subject, including multi-subject credentials.
 *
 * <p>
 * The function is fail-closed: if no recognizable, holder-bound country/region
 * field can be found, or if any discovered code falls outside the EU-27, the
 * permission is denied. Access is granted only when at least one country code is
 * found and every discovered code belongs to the EU-27.
 */
public class EURegionConstraintFunction implements AtomicConstraintFunction<Permission> {

    /** Key used to access the verifiable presentation claim. */
    private static final String CLAIMS_KEY_VERIFIABLE_PRESENTATION = "vp";
    /** Claim holding the authenticated counterparty DID. */
    private static final String CLAIMS_KEY_CLIENT_DID = "client_did";
    private static final String VP_VCS_KEY = "verifiableCredential";
    private static final String VP_HOLDER_KEY = "holder";
    private static final String VC_CREDENTIAL_SUBJECT_KEY = "credentialSubject";
    private static final String CREDENTIAL_SUBJECT_ID_KEY = "id";

    /**
     * The constraint identifier used in ODRL policies. This value should be
     * referenced as the left operand in policy definitions when using this
     * constraint.
     */
    public static final String KEY = "isCounterpartyWithinEu";

    /**
     * ISO 3166-1 alpha-2 country codes of the 27 European Union member states.
     */
    private static final Set<String> EU_COUNTRY_CODES = Set.of(
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
            "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
            "PL", "PT", "RO", "SK", "SI", "ES", "SE");

    /**
     * Keys whose string value holds a country code directly (ISO 3166-1
     * alpha-2) or a country subdivision code (ISO 3166-2, e.g. {@code ES-AS}).
     */
    private static final String[] DIRECT_CODE_KEYS = {
            "countryCode",
            "countrySubdivisionCode",
            "gx:vatID-countryCode",
    };

    /**
     * Keys whose value is a nested address object that holds a
     * {@code gx:countrySubdivisionCode} (ISO 3166-2) entry.
     */
    private static final String[] NESTED_ADDRESS_KEYS = {
            "gx:headquarterAddress",
            "gx:legalAddress",
    };

    private static final String GX_COUNTRY_SUBDIVISION_CODE_KEY = "gx:countrySubdivisionCode";

    private final Monitor monitor;

    /**
     * Constructs a new instance of the EURegionConstraintFunction class with the
     * specified monitor.
     *
     * @param monitor The monitor used for tracking and logging.
     */
    public EURegionConstraintFunction(Monitor monitor) {
        this.monitor = monitor;
    }

    /**
     * Evaluates the permission based on the counterparty's region of origin.
     *
     * @param operator   the operator used for evaluation (not used)
     * @param rightValue the right value used for evaluation (not used)
     * @param rule       the permission rule to evaluate
     * @param context    the policy context
     * @return true if the counterparty is within the EU, false otherwise
     */
    @Override
    public boolean evaluate(Operator operator, Object rightValue, Permission rule, PolicyContext context) {
        ParticipantAgent agent = context.getContextData(ParticipantAgent.class);

        if (agent == null) {
            monitor.warning("%s :: Participant agent is not available: denying".formatted(KEY));
            return false;
        }

        monitor.info("%s :: Participant agent identity: %s".formatted(KEY, agent.getIdentity()));

        Object vp = agent.getClaims().getOrDefault(CLAIMS_KEY_VERIFIABLE_PRESENTATION, null);

        if (vp == null) {
            monitor.warning(
                    "%s :: Participant agent does not have a verifiable presentation claim: denying".formatted(KEY));
            return false;
        }

        Object clientDid = agent.getClaims().getOrDefault(CLAIMS_KEY_CLIENT_DID, null);

        return evaluateVp((String) vp, clientDid instanceof String ? (String) clientDid : null);
    }

    /**
     * Decides whether the country/region of origin encoded in the given
     * Verifiable Presentation is within the EU. Package-private so that the
     * decision logic can be exercised directly in unit tests without an EDC
     * runtime.
     *
     * @param vpJsonStr      the Verifiable Presentation as a JSON string
     * @param counterpartyDid the authenticated counterparty DID, or null to fall
     *                        back to the VP's own validated {@code holder}
     * @return true if at least one holder-bound country code is found and every
     *         discovered code belongs to the EU-27, false otherwise
     */
    boolean evaluateVp(String vpJsonStr, String counterpartyDid) {
        Set<String> countryCodes;

        try {
            JSONObject vpJsonObj = new JSONObject(vpJsonStr);

            String holderDid = counterpartyDid != null && !counterpartyDid.isBlank()
                    ? counterpartyDid
                    : vpJsonObj.optString(VP_HOLDER_KEY, null);

            if (holderDid == null || holderDid.isBlank()) {
                monitor.warning(
                        "%s :: Could not resolve the counterparty/holder DID: denying".formatted(KEY));
                return false;
            }

            countryCodes = collectCountryCodes(vpJsonObj, holderDid);
        } catch (RuntimeException e) {
            monitor.warning("%s :: Failed to parse verifiable presentation: %s: denying".formatted(KEY, e.getMessage()));
            return false;
        }

        if (countryCodes.isEmpty()) {
            monitor.warning(
                    "%s :: No recognizable country/region field bound to the holder: denying".formatted(KEY));
            return false;
        }

        for (String code : countryCodes) {
            if (!EU_COUNTRY_CODES.contains(code)) {
                monitor.info("%s :: Discovered country code '%s' is outside the EU-27: denying (all codes: %s)"
                        .formatted(KEY, code, countryCodes));
                return false;
            }
        }

        monitor.info("%s :: All discovered country codes are within the EU-27: allowing (codes: %s)"
                .formatted(KEY, countryCodes));
        return true;
    }

    private Set<String> collectCountryCodes(JSONObject vpJsonObj, String holderDid) {
        Set<String> codes = new TreeSet<>();
        JSONArray vcsArr = vpJsonObj.optJSONArray(VP_VCS_KEY);

        if (vcsArr == null) {
            return codes;
        }

        for (int i = 0; i < vcsArr.length(); i++) {
            JSONObject vcObj = vcsArr.optJSONObject(i);

            if (vcObj == null) {
                continue;
            }

            // The credentialSubject may be a single object or an array of objects.
            JSONObject subjectObj = vcObj.optJSONObject(VC_CREDENTIAL_SUBJECT_KEY);

            if (subjectObj != null) {
                collectFromSubject(subjectObj, holderDid, codes);
                continue;
            }

            JSONArray subjectArr = vcObj.optJSONArray(VC_CREDENTIAL_SUBJECT_KEY);

            if (subjectArr != null) {
                for (int j = 0; j < subjectArr.length(); j++) {
                    JSONObject element = subjectArr.optJSONObject(j);
                    if (element != null) {
                        collectFromSubject(element, holderDid, codes);
                    }
                }
            }
        }

        return codes;
    }

    private void collectFromSubject(JSONObject subject, String holderDid, Set<String> codes) {
        // Only trust country fields from a subject that is the counterparty itself.
        // The upstream validation binds the credential's JWT `sub` to the holder, but
        // not this embedded credentialSubject.id, so we enforce the binding here.
        String subjectId = subject.optString(CREDENTIAL_SUBJECT_ID_KEY, null);

        if (!didMatches(subjectId, holderDid)) {
            monitor.debug("%s :: Ignoring credentialSubject '%s' not bound to holder '%s'"
                    .formatted(KEY, subjectId, holderDid));
            return;
        }

        for (String key : DIRECT_CODE_KEYS) {
            addNormalized(subject.optString(key, null), codes);
        }

        for (String key : NESTED_ADDRESS_KEYS) {
            JSONObject address = subject.optJSONObject(key);
            if (address != null) {
                addNormalized(address.optString(GX_COUNTRY_SUBDIVISION_CODE_KEY, null), codes);
            }
        }
    }

    /**
     * Returns whether two DIDs identify the same subject, ignoring any
     * {@code #fragment} (e.g. a verification-method suffix like {@code #key-1}).
     * The runtime VP {@code holder} may carry such a fragment while an embedded
     * {@code credentialSubject.id} is the bare DID, or vice versa.
     */
    private static boolean didMatches(String a, String b) {
        if (a == null || b == null) {
            return false;
        }
        return stripFragment(a).equals(stripFragment(b));
    }

    private static String stripFragment(String did) {
        int hashIndex = did.indexOf('#');
        return hashIndex >= 0 ? did.substring(0, hashIndex) : did;
    }

    /**
     * Normalizes a raw country or subdivision value to an ISO 3166-1 alpha-2
     * country code and adds it to the given set when non-empty.
     *
     * <p>
     * Subdivision codes (ISO 3166-2, e.g. {@code ES-AS}) are reduced to their
     * country prefix ({@code ES}). The Greek alias {@code EL} is mapped to its
     * ISO code {@code GR}.
     */
    private void addNormalized(String rawValue, Set<String> codes) {
        if (rawValue == null) {
            return;
        }

        String value = rawValue.trim().toUpperCase();

        if (value.isEmpty()) {
            return;
        }

        int dashIndex = value.indexOf('-');
        if (dashIndex > 0) {
            value = value.substring(0, dashIndex);
        }

        if (value.isEmpty()) {
            return;
        }

        if ("EL".equals(value)) {
            value = "GR";
        }

        codes.add(value);
    }
}
