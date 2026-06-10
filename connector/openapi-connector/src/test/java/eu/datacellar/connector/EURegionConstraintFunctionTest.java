package eu.datacellar.connector;

import static org.assertj.core.api.Assertions.assertThat;

import org.eclipse.edc.spi.monitor.ConsoleMonitor;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link EURegionConstraintFunction}, exercising the country
 * extraction and EU-27 decision logic directly against verifiable presentation
 * JSON strings (no EDC runtime required).
 */
class EURegionConstraintFunctionTest {

    private static final String HOLDER = "did:web:acme.example";
    private static final String OTHER = "did:web:other.example";

    private EURegionConstraintFunction function;

    @BeforeEach
    void setUp() {
        function = new EURegionConstraintFunction(new ConsoleMonitor());
    }

    /**
     * Builds a verifiable presentation with the given holder, one credential per
     * provided credentialSubject JSON fragment.
     */
    private static String vp(String holder, String... credentialSubjects) {
        StringBuilder vcs = new StringBuilder();
        for (int i = 0; i < credentialSubjects.length; i++) {
            if (i > 0) {
                vcs.append(",");
            }
            vcs.append("{\"type\":[\"VerifiableCredential\"],\"credentialSubject\":")
                    .append(credentialSubjects[i])
                    .append("}");
        }
        return "{\"type\":[\"VerifiablePresentation\"],\"holder\":\"" + holder
                + "\",\"verifiableCredential\":[" + vcs + "]}";
    }

    /** Convenience: a VP held by {@link #HOLDER}. */
    private static String vpHeldByHolder(String... credentialSubjects) {
        return vp(HOLDER, credentialSubjects);
    }

    // --- Country value handling (subject bound to the holder) ---

    @Test
    void allowsFlatEuCountryCode() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void allowsFlatEuSubdivisionCode() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countrySubdivisionCode\":\"FR-75\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void allowsGaiaxShapedHeadquarterAddress() {
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"gx:headquarterAddress\":{\"gx:countrySubdivisionCode\":\"ES-AS\"}}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void allowsGaiaxShapedLegalAddress() {
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"gx:legalAddress\":{\"gx:countrySubdivisionCode\":\"DE-BE\"}}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void allowsVatIdCountryCode() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"gx:vatID-countryCode\":\"DE\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void mapsGreekElAliasToGr() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countryCode\":\"EL\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void deniesNonEuCountryCode() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countryCode\":\"US\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesNonEuSubdivisionCode() {
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"gx:headquarterAddress\":{\"gx:countrySubdivisionCode\":\"GB-ENG\"}}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesWhenAnyDiscoveredCodeIsNonEu() {
        // Two holder-bound credentials, one EU and one non-EU: conflicting -> deny.
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\"}",
                "{\"id\":\"" + HOLDER + "\",\"countryCode\":\"US\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesWhenMixedFieldsWithinSingleSubjectConflict() {
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\",\"gx:vatID-countryCode\":\"US\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesWhenNoCountryFieldPresent() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"gx:legalName\":\"Acme\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesWhenNoVerifiableCredentialArray() {
        String vp = "{\"type\":[\"VerifiablePresentation\"],\"holder\":\"" + HOLDER + "\"}";
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesOnMalformedJson() {
        assertThat(function.evaluateVp("not-json", HOLDER)).isFalse();
    }

    @Test
    void handlesCredentialSubjectAsArray() {
        String vp = "{\"type\":[\"VerifiablePresentation\"],\"holder\":\"" + HOLDER + "\","
                + "\"verifiableCredential\":[{"
                + "\"type\":[\"VerifiableCredential\"],"
                + "\"credentialSubject\":[{\"id\":\"" + HOLDER + "\",\"countryCode\":\"IT\"}]"
                + "}]}";
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void normalizesLowercaseAndWhitespace() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countryCode\":\"  pt  \"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    // --- Holder binding (B2) ---

    @Test
    void fallsBackToVpHolderWhenCounterpartyDidNull() {
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\"}");
        assertThat(function.evaluateVp(vp, null)).isTrue();
    }

    @Test
    void deniesWhenHolderCannotBeResolved() {
        // No counterparty DID and no holder field in the VP.
        String vp = "{\"type\":[\"VerifiablePresentation\"],\"verifiableCredential\":[{"
                + "\"type\":[\"VerifiableCredential\"],"
                + "\"credentialSubject\":{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\"}}]}";
        assertThat(function.evaluateVp(vp, null)).isFalse();
    }

    @Test
    void ignoresDecoyEuSubjectWhenHolderHasNoCountry() {
        // Holder credential carries no country; a decoy credential about another
        // subject carries an EU country. The decoy must not grant access.
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"gx:legalName\":\"Acme\"}",
                "{\"id\":\"" + OTHER + "\",\"countryCode\":\"DE\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void ignoresDecoyEuSubjectWhenHolderIsNonEu() {
        String vp = vpHeldByHolder(
                "{\"id\":\"" + HOLDER + "\",\"countryCode\":\"US\"}",
                "{\"id\":\"" + OTHER + "\",\"countryCode\":\"DE\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void collectsOnlyHolderElementInMultiSubjectArray() {
        // Array with a non-holder non-EU subject and the holder's EU subject:
        // only the holder's code is collected -> allow.
        String vp = "{\"type\":[\"VerifiablePresentation\"],\"holder\":\"" + HOLDER + "\","
                + "\"verifiableCredential\":[{"
                + "\"type\":[\"VerifiableCredential\"],"
                + "\"credentialSubject\":["
                + "{\"id\":\"" + OTHER + "\",\"countryCode\":\"US\"},"
                + "{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\"}]"
                + "}]}";
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }

    @Test
    void ignoresEuArrayElementNotBoundToHolder() {
        // Only a non-holder element carries an EU country -> no holder-bound code -> deny.
        String vp = "{\"type\":[\"VerifiablePresentation\"],\"holder\":\"" + HOLDER + "\","
                + "\"verifiableCredential\":[{"
                + "\"type\":[\"VerifiableCredential\"],"
                + "\"credentialSubject\":["
                + "{\"id\":\"" + OTHER + "\",\"countryCode\":\"FR\"},"
                + "{\"id\":\"" + HOLDER + "\",\"gx:legalName\":\"Acme\"}]"
                + "}]}";
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void deniesWhenSubjectIdMissing() {
        // A subject with a country but no id cannot be bound to the holder.
        String vp = vpHeldByHolder("{\"countryCode\":\"ES\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isFalse();
    }

    @Test
    void matchesHolderIgnoringFragmentOnHolder() {
        // Counterparty DID carries a #key fragment; subject id is the bare DID.
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "\",\"countryCode\":\"ES\"}");
        assertThat(function.evaluateVp(vp, HOLDER + "#key-1")).isTrue();
    }

    @Test
    void matchesHolderIgnoringFragmentOnSubject() {
        // Subject id carries a #key fragment; counterparty DID is the bare DID.
        String vp = vpHeldByHolder("{\"id\":\"" + HOLDER + "#key-1\",\"countryCode\":\"ES\"}");
        assertThat(function.evaluateVp(vp, HOLDER)).isTrue();
    }
}
