# CryptoDash — Functional Specification Addendum: HD Wallet Support

**Version:** 1.0
**Date:** 2026-04-13
**Status:** Draft
**Extends:** `FUNC_SPEC.md` v1.0

---

## 1. Executive Summary

### Feature Name

**HD Wallet Support (Bitcoin xpub/ypub/zpub)**

### Description

This addendum extends CryptoDash to support Bitcoin HD (Hierarchical Deterministic) wallets in addition to individual address tracking. Instead of entering a single Bitcoin address, the user can enter an extended public key (xpub, ypub, or zpub) exported from a hardware or software wallet (e.g., Trezor, Ledger, Electrum). CryptoDash then tracks the aggregate balance and transaction history across all addresses derived from that key, surfacing a single consolidated view to the user.

### Key Value Proposition

HD wallets generate a new address for each transaction by design — tracking them as a collection of individual addresses would be impractical. This feature allows the user to add one key and monitor the total holdings of an entire Bitcoin account, regardless of how many receive or change addresses have been used.

### Scope Boundary

**In scope:**

- Adding a Bitcoin HD wallet via xpub, ypub, or zpub extended public key
- Aggregated balance and historical balance tracking for the HD wallet as a whole
- Expandable list of active derived addresses with their current individual balances (no charts per address)
- Validation of xpub/ypub/zpub key format
- Coexistence with existing individual-address Bitcoin wallets
- Rejection of testnet keys (tpub, upub, vpub)

**Out of scope:**

- Address derivation performed locally by CryptoDash (derivation is delegated to the external API)
- Per-derived-address charts or historical data
- Kaspa HD wallet support
- Automatic detection of overlap between an individual tracked address and a derived address from a tracked xpub
- xpub-style support for any network other than Bitcoin

---

## 2. Glossary Additions

The following terms extend the glossary in `FUNC_SPEC.md § 2`.

| Term | Definition |
|---|---|
| **HD Wallet** | A Bitcoin wallet registered via an extended public key (xpub/ypub/zpub). Represents the aggregate of all addresses derived from that key. |
| **Extended Public Key** | A cryptographic key that encodes a Bitcoin account's public root, from which an unlimited sequence of child addresses can be derived. Comes in three mainnet variants: xpub (legacy), ypub (P2SH-wrapped SegWit), zpub (native SegWit). Also called "xpub" generically in the UI. |
| **xpub** | An extended public key whose prefix indicates the BIP32/BIP44 derivation standard, producing legacy P2PKH addresses (starting with `1`). |
| **ypub** | An extended public key whose prefix indicates the BIP49 standard, producing P2SH-wrapped SegWit addresses (starting with `3`). |
| **zpub** | An extended public key whose prefix indicates the BIP84 standard, producing native SegWit (Bech32) addresses (starting with `bc1q`). |
| **Testnet key** | An extended public key for the Bitcoin testnet (prefixes: tpub, upub, vpub). Not supported. |
| **Derived address** | An individual Bitcoin address generated from an extended public key according to the relevant BIP derivation path. |
| **Active derived address** | A derived address that has at least one on-chain transaction (incoming or outgoing). |
| **Aggregate balance** | The sum of the current balances across all derived addresses of an HD wallet. This is the balance shown at the HD wallet level. |
| **Individual address wallet** | A Bitcoin wallet registered using a single address (the pre-existing mode). Distinguished from HD Wallet. |

---

## 3. Impact on Users and Personas

No new user roles are introduced. The existing Owner persona gains a new option when adding a Bitcoin wallet. No new authorization rules.

---

## 4. Feature Map Changes

The following existing features are extended. No new top-level features are introduced.

| Feature | Change |
|---|---|
| F1 — Wallet Management | New wallet input mode (HD wallet via xpub/ypub/zpub); new validation rules; new display variant (HD badge + expandable address list) |
| F2 — Balance Retrieval | HD wallet balance is fetched as an aggregate from an xpub-capable API |
| F4 — Historical Data | Historical balance reconstruction applies at the aggregate (HD wallet) level |
| F5 — Dashboard | HD wallet widgets show aggregate data; per-address breakdown has no chart; wallet detail page shows aggregate chart + address list |

---

## 5. Feature Specifications

---

### F1 Extension: HD Wallet Management

#### 5.1.a Description and Purpose

Extends wallet registration to accept Bitcoin extended public keys. The user selects Bitcoin as the network and enters an xpub, ypub, or zpub key instead of a single address. The system validates the key, stores it as a single HD wallet entry, and tracks the aggregate balance of all derived addresses under that key.

#### 5.1.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-H01 | The system shall allow the user to add a Bitcoin HD wallet by entering an extended public key (xpub, ypub, or zpub) in the wallet address field. |
| FR-H02 | The system shall detect whether the input is an extended public key or an individual address based on the value's prefix, without requiring the user to select a wallet sub-type explicitly. |
| FR-H03 | The system shall validate the extended public key format: prefix must be one of `xpub`, `ypub`, or `zpub` (case-sensitive, lowercase); the full string must be 111 characters long; and the value must pass Base58Check integrity verification. |
| FR-H04 | The system shall reject extended public keys with testnet prefixes (`tpub`, `upub`, `vpub`) with the message: "Testnet keys are not supported. Please export a mainnet key from your wallet." |
| FR-H05 | The system shall reject any input that has 107–115 characters but an unrecognized prefix (i.e., not a known Bitcoin address prefix and not a recognized extended key prefix) with the message: "Unrecognized key format. Bitcoin extended public keys start with xpub, ypub, or zpub." |
| FR-H06 | The system shall reject a duplicate HD wallet (same extended public key already registered) with the message: "This HD wallet key is already being tracked." Comparison is exact-match (case-sensitive). |
| FR-H07 | The system shall apply the same tag rules to HD wallets as to individual-address wallets (FR-004, FR-005, FR-006). The default tag format for HD wallets shall be "BTC HD Wallet #{n}". |
| FR-H08 | The system shall display HD wallets in the wallet list with a visible "HD" badge adjacent to the wallet tag, distinguishing them from individual-address wallets. |
| FR-H09 | The system shall display the extended public key in the address field, truncated to the first 10 characters + "..." + last 6 characters (e.g., `xpub6CUGRo...d4e7f2`). The full key shall be accessible on hover (tooltip) or tap (bottom sheet on mobile). |
| FR-H10 | An HD wallet shall count as exactly 1 wallet toward the 50-wallet limit, regardless of how many derived addresses it covers. |
| FR-H11 | The system shall allow an HD wallet and an individual-address wallet to coexist even if the individual address happens to be derived from the HD wallet's key. The system shall not attempt to detect or warn about this overlap. |
| FR-H12 | The system shall, when the user expands an HD wallet entry in the wallet list, display a sub-list of all currently active derived addresses with their individual current balances in native coin and USD. |
| FR-H13 | The system shall define an "active derived address" as one that has at least one confirmed on-chain transaction (incoming or outgoing). Derived addresses with zero transactions shall not appear in the list. |
| FR-H14 | The system shall display the derived address sub-list in descending order of current balance. |
| FR-H15 | The system shall display a maximum of 200 derived addresses in the sub-list. If the API reports more than 200 active addresses, the system shall show the first 200 by balance and display a note: "Showing top 200 of {total} addresses." |
| FR-H16 | The system shall allow the user to remove an HD wallet. Removal shall delete the wallet entry, its aggregate snapshots, and all stored derived-address data from the database. The same confirmation dialog as for individual wallets applies (FR-008). |

#### 5.1.c User Interaction Flow

**Adding an HD Wallet:**

1. User clicks "Add Wallet."
2. The form appears with: network selector, address/key input field, tag field.
3. User selects "Bitcoin" as the network.
4. User pastes an xpub, ypub, or zpub key into the address/key field.
5. The system detects the extended key format in real-time (or on submit) and updates the label of the input field from "Wallet address" to "Extended public key (xpub/ypub/zpub)".
6. User optionally enters a custom tag (placeholder: "BTC HD Wallet #1").
7. User submits the form.
8. On validation error: inline error appears below the input field; form remains open with input preserved.
9. On success: form closes; the HD wallet appears in the wallet list with an "HD" badge; a background fetch is triggered to load the aggregate balance, derived address list, and transaction history.

**Viewing an HD Wallet in the Wallet List:**

1. The wallet list shows the HD wallet row: tag, "HD" badge, network "BTC", truncated key, aggregate balance in BTC and USD.
2. A chevron/expand icon is visible on the right of the row.
3. User clicks the expand icon.
4. A sub-list animates open below the row, showing a table of active derived addresses:
   - Truncated address (first 8 + "..." + last 6 chars, full address on hover/tap)
   - Current balance in BTC
   - Current balance in USD
5. User clicks the icon again to collapse.
6. If no active addresses exist yet (new key with no transactions): the sub-list shows: "No transactions found for this HD wallet yet."
7. If the address data is still loading (first fetch in progress): show a spinner inside the expanded area.

**Removing an HD Wallet:**

- Identical to removing an individual-address wallet. Confirmation dialog text: "Remove '{tag}'? All historical data for this HD wallet will be deleted."

#### 5.1.d Business Rules

**Extended public key validation:**

- IF input prefix is `xpub`, `ypub`, or `zpub` AND total length is 111 characters AND Base58Check integrity passes THEN accept as an HD wallet key.
- IF input prefix is `tpub`, `upub`, or `vpub` THEN reject with the testnet error message (FR-H04).
- IF input does not match any known Bitcoin address prefix (1, 3, bc1q, bc1p) AND does not match any known extended key prefix THEN reject with the unrecognized format message (FR-H05).
- IF input matches a known Bitcoin address prefix THEN validate as an individual address (existing F1 rules apply).

**Tag rules:**

- HD wallets follow the same tag length, uniqueness, and default-naming rules as individual wallets. The default tag pattern is "BTC HD Wallet #{n}" where {n} increments until unique.

**Duplicate detection:**

- HD wallet duplicate check is key-exact (same xpub/ypub/zpub string). An xpub and its ypub/zpub equivalent (same underlying key, different encoding) are not considered duplicates by the system since detecting this equivalence requires cryptographic computation outside scope.

**Derived address list refresh:**

- The derived address list (active addresses + individual balances) is refreshed on every balance refresh cycle (manual or automatic). The list may grow over time as new addresses become active.
- The derived address list is read-only. The user cannot add, remove, or tag individual derived addresses.

#### 5.1.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| User pastes an xpub with leading/trailing whitespace | System trims whitespace before validation. |
| User pastes an xpub that is 110 or 112 characters (off by one) | Reject with: "Invalid extended public key. Expected 111 characters, got {n}." |
| User pastes a valid-looking string with xpub prefix but fails Base58Check | Reject with: "Invalid extended public key: checksum verification failed. Please re-export the key from your wallet." |
| User pastes the same xpub key already tracked | Reject with: "This HD wallet key is already being tracked." |
| HD wallet has no active addresses at the time of first fetch | Wallet is saved; aggregate balance shows 0 BTC / $0.00; expanded list shows "No transactions found for this HD wallet yet." |
| API call to fetch aggregate balance fails on first add | Wallet is saved. Balance shows "Pending...". Warning: "Could not fetch balance for {tag}. Will retry on next refresh." (same as individual wallet behavior per F1.e) |
| API call for derived address list fails | Aggregate balance may still succeed. Expanded list shows: "Could not load address breakdown. Will retry on next refresh." |
| API returns more than 200 active derived addresses | System stores all returned data but displays only the top 200 by balance, with a note per FR-H15. |
| User attempts to remove an HD wallet while a refresh is in progress | Allow removal. The in-progress fetch for that wallet is cancelled or its result discarded. |
| xpub and ypub of the same underlying key are both added | Both are accepted as separate wallets (no equivalence detection). Their aggregate balances may partially overlap; this is a user responsibility. |

#### 5.1.f Acceptance Criteria

- **Given** the user selects "Bitcoin" and enters a valid zpub key, **When** they submit the Add Wallet form, **Then** the wallet list shows one entry with an "HD" badge, the truncated key, and the aggregate BTC balance.
- **Given** an HD wallet is in the list, **When** the user clicks its expand icon, **Then** a sub-list of active derived addresses appears, each showing a truncated address, BTC balance, and USD balance.
- **Given** a zpub key is already tracked, **When** the user tries to add the same zpub key again, **Then** the form shows "This HD wallet key is already being tracked." and the wallet is not added.
- **Given** the user enters a tpub key, **When** they submit the form, **Then** the form shows "Testnet keys are not supported. Please export a mainnet key from your wallet."
- **Given** an HD wallet exists alongside an individual-address wallet for the same BTC address, **When** the user views the wallet list, **Then** both appear as independent entries with no warning about overlap.
- **Given** an HD wallet has no on-chain transactions, **When** the user expands it, **Then** the message "No transactions found for this HD wallet yet." is shown.
- **Given** 50 wallets (any mix of individual and HD) are registered, **When** the user tries to add another, **Then** the Add Wallet button is disabled and the limit message is shown.

---

### F2 Extension: Balance Retrieval for HD Wallets

#### 5.2.a Description and Purpose

Fetches the aggregate BTC balance for each registered HD wallet from an xpub-capable Bitcoin API. The balance represents the total holdings across all derived addresses. Derived address individual balances are fetched at the same time and stored for display in the expandable sub-list.

#### 5.2.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-H17 | The system shall query an xpub-capable Bitcoin API to retrieve the aggregate current balance for each registered HD wallet. |
| FR-H18 | The system shall, in the same API call (or a separate call if the API requires it), retrieve the current individual balance of each active derived address, for display in the expandable sub-list. |
| FR-H19 | The system shall store the aggregate HD wallet balance as a snapshot on each successful fetch, using the same snapshot mechanism as individual wallets. |
| FR-H20 | The system shall include HD wallets in the same refresh cycle as individual wallets (both manual and automatic). No separate refresh trigger is needed. |
| FR-H21 | The system shall handle failures for HD wallet fetches using the same rules as individual wallet failures (existing F2 business rules and edge cases apply). |

#### 5.2.c Business Rules

- HD wallet balance failure handling is identical to individual wallet failure handling: retain the most recent successful aggregate balance, mark the wallet with a warning icon.
- The derived address sub-list is updated only when the HD wallet fetch succeeds. If the fetch fails, the previously cached address list remains displayed without a staleness indicator (the wallet-level warning icon is sufficient).
- Rate limiting: HD wallet API calls count toward the same Bitcoin API rate-limit budget as individual wallet calls. The scheduler shall not treat HD wallets preferentially.

#### 5.2.d Edge Cases

| Scenario | Expected Behavior |
|---|---|
| API returns aggregate balance but no derived address breakdown | Store the aggregate balance snapshot. Derived address sub-list shows: "Address breakdown unavailable from API." |
| Aggregate balance is 0 but derived address list is non-empty | Accept: some addresses may have received and spent all funds. Store the 0-balance snapshot normally. |
| Derived address list changes between refreshes (new address became active) | New active addresses are added to the stored list; the expanded UI shows the updated list on next expand. |

---

### F4 Extension: Historical Data for HD Wallets

#### 5.4.a Description and Purpose

When an HD wallet is first added, the system retrieves the full aggregate transaction history available from the API in order to reconstruct the wallet's balance over time. Subsequent refreshes fetch only new transactions (incremental sync). All history is stored and displayed at the HD wallet aggregate level — not per derived address.

#### 5.4.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-H22 | The system shall, upon adding a new HD wallet, perform a one-time full retrieval of the wallet's aggregate transaction history from the xpub-capable API, using the same mechanism as for individual wallets (existing FR-023 and FR-024 apply at the aggregate level). |
| FR-H23 | The system shall reconstruct historical balance snapshots from the HD wallet's aggregate transaction history using the same algorithm as for individual wallets (net balance at each transaction event). |
| FR-H24 | The system shall store incremental transaction updates for HD wallets on each subsequent refresh, following the same rules as for individual wallets (existing FR-025 and FR-026 apply). |
| FR-H25 | The system shall NOT store per-derived-address transaction history. Historical data is aggregate only. |

#### 5.4.c Business Rules

- Historical balance reconstruction for HD wallets uses the aggregate transaction stream from the API (not per-address streams). This is the natural output of an xpub-capable endpoint and requires no special handling beyond what already exists for individual wallets.
- The choice of API and the exact transaction retrieval mechanism for HD wallets is deferred to the technical specification phase (see Open Questions § 11.1).

---

### F5 Extension: Dashboard for HD Wallets

#### 5.5.a Description and Purpose

HD wallets are surfaced throughout the dashboard identically to individual wallets, with the exception that their detail view shows the derived address list instead of a single address, and no per-address charts are provided.

#### 5.5.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-H26 | The system shall include HD wallet aggregate balances in all portfolio-level totals and charts. |
| FR-H27 | The system shall display the HD wallet's aggregate balance history chart on the wallet detail page, using the same chart component as for individual wallets. |
| FR-H28 | The system shall NOT provide individual balance history charts for derived addresses. |
| FR-H29 | The system shall display the active derived address list on the wallet detail page, below the aggregate chart, using the same table layout as described in the wallet list expand behavior (FR-H12 through FR-H15). |
| FR-H30 | The system shall display the "HD" badge wherever the wallet's tag is shown: wallet list, wallet detail page header, and any dashboard widget that references individual wallets. |

---

## 6. Data Requirements

### 6.1 Changes to the Wallet Entity

The existing `Wallet` entity is extended with the following fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `wallet_type` | enum: `individual`, `hd` | Yes | Discriminates between the two wallet modes. Defaults to `individual` for all existing wallets. |
| `extended_public_key` | string (111 chars) | Conditional | Present if and only if `wallet_type = hd`. The raw xpub/ypub/zpub string. Not encrypted (it is public key material). |
| `extended_key_type` | enum: `xpub`, `ypub`, `zpub` | Conditional | Present if and only if `wallet_type = hd`. Derived from the key prefix at insert time. |

The existing `address` field on the Wallet entity:
- For `individual` wallets: the Bitcoin or Kaspa address (unchanged).
- For `hd` wallets: set to the `extended_public_key` value. This preserves the schema without a nullable column and allows existing unique constraints to function correctly.

The existing `network` field remains `BTC` for all HD wallets.

### 6.2 New Entity: DerivedAddress

Stores the current state of each active derived address for a given HD wallet. This is a cache of the last API response, not a historical record.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | Yes | Primary key |
| `wallet_id` | UUID (FK → Wallet) | Yes | The parent HD wallet |
| `address` | string | Yes | The derived Bitcoin address |
| `current_balance_native` | decimal | Yes | Current balance in BTC |
| `last_updated_at` | datetime | Yes | Timestamp of the last successful fetch |

- Relationship: Many DerivedAddresses → One HD Wallet.
- Lifecycle: Created or updated on each successful HD wallet balance fetch. Deleted when the parent HD wallet is deleted.
- Retention: Only the current snapshot is stored. No historical balance records per derived address.

### 6.3 Snapshot Entity (unchanged)

Balance snapshots for HD wallets use the existing snapshot entity, with `wallet_id` pointing to the HD wallet. No schema change needed.

---

## 7. External Interfaces

### 7.1 xpub-Capable Bitcoin API

- **Purpose:** Retrieve aggregate balance and transaction history for a Bitcoin HD wallet given its extended public key.
- **Direction:** Inbound (data flows into CryptoDash). Read-only.
- **Protocol:** REST over HTTPS (expected, based on existing Bitcoin API integration pattern).
- **Data exchanged (logical):**
  - Input: xpub, ypub, or zpub key string.
  - Output: aggregate confirmed balance (in satoshis), list of active derived addresses with individual balances, paginated list of transactions (with inputs, outputs, amounts, timestamps, confirmation status).
- **API selection:** Deferred to technical specification phase. The functional behavior described above is what the API must support; which specific API provides it is a technical decision. Research must confirm: (a) whether Mempool.space, blockchain.info, or another provider offers this capability with acceptable rate limits; (b) which extended key types (xpub/ypub/zpub) each provider supports; (c) pagination model for large transaction sets.
- **Failure handling:** Same as existing Bitcoin API failure handling (F2 edge cases).
- **Dependency criticality:** Hard dependency for HD wallet balance and history. If the API is unavailable, HD wallet data cannot be updated; cached data is shown with a warning. Individual-address wallets continue to function independently.

---

## 8. Non-Functional Requirements

### 8.a Performance

- The first-add history retrieval for an HD wallet with many transactions (e.g., 500+ transactions across 50+ addresses) should complete within 30 seconds, subject to API response times. If it exceeds 30 seconds, it continues in the background without blocking the UI.
- Rendering the expanded derived address sub-list (up to 200 rows) must complete within 500ms on the client.

### 8.b Security

- Extended public keys are public key material. They do not grant spending ability. They are stored in the database unencrypted, consistent with how individual Bitcoin addresses are stored.
- The xpub key does allow address enumeration (privacy consideration). The user is assumed to be aware of this trade-off when exporting it from their hardware wallet.

### 8.c Usability

- Users unfamiliar with extended public keys may not know where to find them on their Trezor. The Add Wallet form should include a brief helper text: "Find your extended public key in Trezor Suite under Account → Details → Show public key." This text is shown only when the network is Bitcoin.
- The "HD" badge must be accessible (not conveyed by color alone; use text).

---

## 9. Constraints and Assumptions

| Constraint / Assumption | Impact if Wrong |
|---|---|
| An xpub-capable Bitcoin public API exists that covers xpub, ypub, and zpub with acceptable rate limits. | If no suitable API is found, the feature cannot be implemented without running local address derivation (significant additional complexity). This must be confirmed in the tech spec phase. |
| The API aggregates transactions across both receive and change addresses for a given extended key. | If the API only covers receive addresses, change address balances would be missing and totals would be incorrect. Must be verified. |
| Extended public keys are always 111 characters in Base58Check encoding for mainnet. | If an edge case produces a different length (e.g., certain encoding libraries), valid keys might be rejected. The tech spec may relax the length check to a range (e.g., 107–115) with a note. |
| The user exports an account-level xpub (e.g., m/44'/0'/0') not a root xpub (m/). | A root xpub would cover all accounts, not just one. The system cannot distinguish these — it relies on the API's interpretation. Documented as a user responsibility. |
| Kaspa does not currently use xpub-style HD wallets in a way that benefits from this feature. | No impact on this version. Revisit if Kaspa adds HD wallet support. |

---

## 10. Release and Phasing

This feature is delivered as a single increment on top of the base CryptoDash release (FUNC_SPEC.md v1.0). There are no sub-phases.

**Dependencies:**

- The base Bitcoin individual-address wallet feature (F1, F2, F4 in FUNC_SPEC.md) must be complete before this feature can be built, as it shares the wallet management UI, snapshot infrastructure, and Bitcoin API client.
- The xpub-capable API must be identified and validated in the tech spec before implementation begins.

---

## 11. Open Questions & Decisions Log

### 11.1 xpub API Provider — Deferred to Tech Spec (HIGH PRIORITY)

**Ambiguity:** The brief states "blockchain.info API already offers endpoints to retrieve aggregated balance and transactions for all addresses generated." Mempool.space was the planned Bitcoin API but does not have confirmed xpub support.

**Decision:** The specific API provider for xpub queries is deferred to the technical specification phase. The tech spec must research and confirm: which provider(s) support xpub, ypub, and zpub; what their rate limits are; whether the same provider can serve both individual-address and HD wallet queries; and whether blockchain.info's xpub endpoint is reliable enough for production use.

**Flag:** This is a hard dependency. If no suitable public API is found, the feature may require local address derivation (BIP32/BIP44 implementation), which significantly increases implementation scope. The tech spec must resolve this before implementation begins.

---

### 11.2 Derived Address Sub-List: Receive vs. Change Addresses

**Ambiguity:** HD wallets generate two types of addresses: external/receive (shown to senders) and internal/change (used internally by the wallet). Some users may be surprised to see change addresses in the list.

**Decision:** Display all active derived addresses regardless of type (receive or change), since both types hold real funds and are part of the wallet's total balance. The API aggregates both; filtering them out would require local derivation path analysis, which is out of scope.

---

### 11.3 Real-Time Input Detection vs. Submit-Time Detection

**Ambiguity:** FR-H02 specifies that the system detects whether the input is an extended key or an individual address. It is unspecified whether this detection happens on each keystroke (real-time) or only on form submit.

**Decision:** Detect on submit and on paste events (not on every keystroke). This avoids false detections while the user is still typing and avoids jitter in the input label. The label change (FR-H02's "Wallet address" → "Extended public key") applies after paste or blur.

---

### 11.4 Extended Key Length Tolerance

**Ambiguity:** FR-H03 specifies exactly 111 characters. In practice, Base58Check-encoded extended keys are consistently 111 characters for mainnet, but some encoding edge cases could produce 110 or 112 characters.

**Decision:** Validate as exactly 111 characters for v1. If this causes user-reported rejections of valid keys, the tech spec may change this to a range (108–112) without functional consequence.

---

### 11.5 No Overlap Detection Between HD and Individual Wallets

**Ambiguity:** The brief explicitly states not to detect overlap. Documented here as a deliberate decision.

**Decision:** No overlap detection. If a user tracks both `xpub6...` and one of its derived addresses (e.g., `bc1qxyz...`) as separate wallets, both are tracked independently and both contribute to the portfolio total. This means the overlapping balance is counted twice. This is a user responsibility and is consistent with how two individual wallets at the same address would behave (the system already rejects duplicate individual addresses per FR-003, but cross-mode duplicates are not detected).

---

*Last updated: 2026-04-13*
