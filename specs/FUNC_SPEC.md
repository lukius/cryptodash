# CryptoDash — Functional Specification

**Version:** 1.0
**Date:** 2026-04-12
**Status:** Draft

---

## 1. Executive Summary

### Product Name

**CryptoDash**

### Description

CryptoDash is a personal web application that allows a single user to monitor the balances of multiple cryptocurrency wallets across the Bitcoin and Kaspa networks. The user adds wallet addresses, assigns custom names/tags to them, and views a dashboard of charts and widgets showing current balances, portfolio composition, and balance history over time. The application periodically fetches balance data from public blockchain APIs and price data from CoinGecko, storing snapshots locally for historical tracking.

### Key Value Proposition

A self-hosted, unified view of crypto holdings across Bitcoin and Kaspa — no private keys required, no third-party account needed, no data shared with centralized portfolio services. The user retains full control of their data in a local SQLite database.

### Scope Boundary

**In scope (this version):**

- Single-user mode (no authentication, no login)
- Add/remove wallets (Bitcoin and Kaspa networks only)
- Custom wallet names/tags
- Dashboard with portfolio-level and per-wallet charts and widgets
- Periodic background balance and price polling with configurable interval
- On-demand manual refresh
- Balance history from blockchain transaction history (retroactive) and forward-looking snapshots
- Price history (forward-looking snapshots from CoinGecko)
- Wallet address format validation
- Mobile-friendly responsive design
- Configuration panel for refresh interval and other settings
- Single-user authentication (first-run account setup, login, logout, session management)
- SQLite storage
- Python backend, web frontend

**Out of scope (this version):**

- Multi-user mode / user registration (only one account exists)
- Sending transactions or managing private keys
- Networks other than Bitcoin and Kaspa
- Data export (CSV, PDF)
- Notifications and alerts
- Fiat currencies other than USD for display

---

## 2. Glossary

| Term | Definition |
|---|---|
| **Wallet** | A blockchain address that the user registers in CryptoDash for balance tracking. Does not imply private key access. |
| **Network** | The blockchain network a wallet belongs to. In this version: Bitcoin (BTC) or Kaspa (KAS). |
| **Tag** | A user-assigned display name for a wallet (e.g., "Cold Storage", "Trading Fund"). |
| **Balance** | The amount of native cryptocurrency held at a wallet address at a given point in time. |
| **Snapshot** | A timestamped record of a wallet's balance and the corresponding USD price, stored for historical charting. |
| **Refresh** | The act of querying external APIs to update wallet balances and crypto prices. Can be manual or automatic. |
| **Portfolio** | The aggregate of all wallets the user has registered in CryptoDash. |
| **Native coin** | The cryptocurrency native to a network: BTC for Bitcoin, KAS for Kaspa. |
| **BTC** | Bitcoin, the native currency of the Bitcoin network. |
| **KAS** | Kaspa, the native currency of the Kaspa network. |
| **USD** | United States Dollar, used as the fiat reference currency for displaying portfolio value. |
| **Session** | An authenticated browser session, represented by a server-side token. Valid for 7 days by default, or extended via "Remember me." |
| **First-run setup** | The one-time account creation flow that appears when the application is launched for the first time (no user exists in the database). |

---

## 3. Users and Personas

### 3.1 User Type: Owner (single user)

- **Description:** A crypto holder who owns wallets on the Bitcoin and/or Kaspa networks and wants a centralized, self-hosted dashboard to monitor balances and track value over time.
- **Goals:**
  - See total portfolio value at a glance (in USD, BTC, and KAS).
  - Track how each wallet's balance and the portfolio's total value evolve over time.
  - Organize wallets with custom names for easy identification.
  - Access the dashboard from desktop and mobile devices.
- **Constraints:**
  - Technical literacy: comfortable running a self-hosted web app.
  - Device: desktop browser (primary), mobile browser (secondary).
  - Usage frequency: daily to weekly check-ins.

### 3.2 Authentication and Authorization

The application requires login. A single user account is created during the first-run setup flow (see F8). All features behind the dashboard require an active session.

- **Unauthenticated access:** Only the login page and the first-run setup page are accessible without a session.
- **Authenticated access:** All other pages and API endpoints require a valid session. Requests without a valid session are redirected to the login page.
- **Single account:** Only one user account exists. There is no registration page or self-service signup. If multi-user support is added in a future version, the data model already accommodates it via the `user_id` field on wallets and settings.

---

## 4. System Overview

### 4.1 Context Diagram

```
                          +------------------+
                          |    CryptoDash    |
                          |   (Web App)      |
                          +--------+---------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
    +-------------------+  +-----------------+  +------------------+
    | Bitcoin Blockchain |  | Kaspa Blockchain|  | CoinGecko API    |
    | Public API(s)      |  | Public API      |  | (Price Data)     |
    | (Balance + Tx      |  | (Balance + Tx   |  |                  |
    |  History)          |  |  History)       |  |                  |
    +-------------------+  +-----------------+  +------------------+
              ^                    ^                    ^
              |                    |                    |
         Read-only            Read-only            Read-only
       (wallet balance,     (wallet balance,     (BTC/USD, KAS/USD
        tx history)          tx history)          spot prices)
```

**Actors:**

- **Owner** — interacts with CryptoDash via a web browser.
- **Bitcoin public API** — provides BTC wallet balance and transaction history. Data flows in (to CryptoDash). Read-only.
- **Kaspa public API** — provides KAS wallet balance and transaction history. Data flows in. Read-only.
- **CoinGecko API** — provides BTC/USD and KAS/USD spot prices. Data flows in. Read-only.

### 4.2 High-Level Feature Map

| # | Feature Area | Description |
|---|---|---|
| F1 | Wallet Management | Add, edit (tag), remove wallets; address validation |
| F2 | Balance Retrieval | Fetch current balances from blockchain APIs |
| F3 | Price Retrieval | Fetch current BTC/USD and KAS/USD prices from CoinGecko |
| F4 | Historical Data | Retrieve past balances from blockchain transaction history; store periodic snapshots |
| F5 | Dashboard | Charts and widgets showing portfolio and wallet data |
| F6 | Configuration Panel | User-adjustable settings (refresh interval, etc.) |
| F7 | Background Scheduler | Periodic automatic balance and price refresh |
| F8 | Authentication | First-run account setup, login, logout, session management |

### 4.3 Core Workflows

**Workflow 0a: First-Run Setup**

1. User opens the application for the first time (no account exists in the database).
2. System displays the account creation screen.
3. User enters a username and password (with confirmation).
4. System validates password strength and creates the account.
5. System automatically logs the user in and redirects to the dashboard (empty state).

**Workflow 0b: Login**

1. User opens the application (account exists, no active session).
2. System displays the login screen.
3. User enters username and password, optionally checks "Remember me."
4. System validates credentials.
5. On success: session is created, user is redirected to the dashboard.
6. On failure: error message displayed, input preserved (except password).

**Workflow 1: Add a Wallet**

1. User navigates to the wallet management area and clicks "Add Wallet."
2. A form appears with: network selector, wallet address field, and tag/name field (optional).
3. User selects the network (Bitcoin or Kaspa), enters the wallet address, and optionally enters a custom tag.
4. User submits the form.
5. System validates the address format for the selected network.
6. If invalid, system displays an inline error message; the user's input is preserved.
7. If valid, system saves the wallet (assigning a default tag if none was provided), immediately fetches its current balance, and retrieves available transaction history to reconstruct past balances.
8. Dashboard updates to include the new wallet's data.

**Workflow 2: View Dashboard**

1. User opens the application in a browser.
2. System displays the dashboard with all widgets populated from the most recently stored data.
3. Balances and prices reflect the last refresh (timestamp displayed).
4. User can browse charts, switch time ranges, and view per-wallet details.

**Workflow 3: Manual Refresh**

1. User clicks a "Refresh" button on the dashboard.
2. System fetches current balances for all wallets and current prices from CoinGecko.
3. System stores new snapshots.
4. Dashboard updates with fresh data; a "last updated" timestamp is shown.
5. If any API call fails, the system displays a warning indicating which wallet(s) or price(s) could not be updated, while still displaying the most recent successful data.

**Workflow 4: Inspect Historical Balance**

1. User views a balance-over-time chart (portfolio-level or per-wallet).
2. Chart shows historical data points reconstructed from blockchain transaction history (for the period before the wallet was added) and from stored snapshots (for the period after).
3. User can hover/tap data points to see exact values and dates.

**Workflow 5: Configure Refresh Interval**

1. User opens the configuration panel.
2. User sets the automatic refresh interval (e.g., every 5, 15, 30 minutes).
3. System saves the setting and restarts the background scheduler with the new interval.

---

## 5. Feature Specifications

---

### F1: Wallet Management

#### 5.1.a Description and Purpose

Allows the user to register blockchain wallet addresses for tracking, assign human-readable tags to them, and remove wallets that are no longer of interest. This is the foundational feature — without wallets, there is nothing to track.

#### 5.1.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-001 | The system shall allow the user to add a wallet by specifying a network (Bitcoin or Kaspa) and a wallet address. |
| FR-002 | The system shall validate the wallet address format against the rules of the selected network before saving (see Business Rules below). |
| FR-003 | The system shall reject a wallet address that is already registered (same network + same address), displaying a message: "This wallet address is already being tracked." |
| FR-004 | The system shall allow the user to assign an optional tag (free-text name) to a wallet at creation time. |
| FR-005 | The system shall assign a default tag of "{NETWORK} Wallet #{n}" (e.g., "BTC Wallet #3") if the user does not provide one, where {n} is incremented until the resulting tag is unique. |
| FR-006 | The system shall allow the user to edit the tag of an existing wallet at any time. |
| FR-007 | The system shall allow the user to remove a wallet. Removal deletes the wallet and all its associated snapshot history from the database. |
| FR-008 | The system shall prompt the user for confirmation before removing a wallet: "Remove '{tag}'? All historical data for this wallet will be deleted." |
| FR-009 | The system shall enforce a maximum of 50 wallets. When the limit is reached, the "Add Wallet" action shall be disabled and a message displayed: "Wallet limit reached (50). Remove a wallet to add a new one." |
| FR-010 | The system shall display a list of all registered wallets showing: tag, network, address (truncated with full address on hover/tap), current balance in native coin, and current balance in USD. |

#### 5.1.c User Interaction Flow

1. **Add Wallet:**
   - User clicks "Add Wallet" button.
   - A form appears with: network selector (dropdown: Bitcoin / Kaspa), address input field, tag input field (optional, with placeholder showing the default tag).
   - User fills in fields and clicks "Add".
   - On validation error: error message appears inline below the address field; form remains open with user input preserved.
   - On success: form closes, wallet appears in the wallet list, and a background fetch is triggered for the wallet's balance and history.

2. **Edit Tag:**
   - User clicks on a wallet's tag in the wallet list (or an edit icon next to it).
   - Tag becomes an editable text field.
   - User modifies and presses Enter or clicks a confirm button.
   - If the new tag is already used by another wallet: inline error "A wallet with this tag already exists." The tag reverts to its previous value.
   - On success: tag updates immediately.

3. **Remove Wallet:**
   - User clicks a delete/remove icon on a wallet row.
   - Confirmation dialog appears.
   - On confirm: wallet and its snapshots are deleted; dashboard updates.
   - On cancel: no action.

#### 5.1.d Business Rules

**Address validation:**

- **Bitcoin (BTC):**
  - IF address starts with `1` THEN it must be 25–34 characters, alphanumeric (Base58Check: no `0`, `O`, `I`, `l`). (P2PKH — Legacy)
  - IF address starts with `3` THEN same rules as above. (P2SH)
  - IF address starts with `bc1q` THEN it must be 42 or 62 characters, lowercase alphanumeric excluding `1`, `b`, `i`, `o`. (Bech32 — SegWit v0)
  - IF address starts with `bc1p` THEN it must be 62 characters, same character set as Bech32. (Bech32m — Taproot)
  - ELSE reject with message: "Invalid Bitcoin address format."

- **Kaspa (KAS):**
  - IF address starts with `kaspa:` THEN the remainder must be 61 characters of lowercase alphanumeric (Bech32 charset).
  - ELSE reject with message: "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'."

**Tag rules:**

- IF tag length > 50 characters THEN reject with message: "Tag must be 50 characters or fewer."
- IF tag is empty or whitespace-only THEN assign the default tag.
- Tags must be unique across all wallets (case-insensitive). IF the user enters a tag already in use THEN reject with message: "A wallet with this tag already exists."

**Duplicate detection:**

- IF a wallet with the same (network, address) pair already exists THEN reject with message: "This wallet address is already being tracked."
- Comparison is case-insensitive for Bitcoin addresses and exact-match for Kaspa addresses (which are always lowercase).

#### 5.1.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| User pastes an address with leading/trailing whitespace | System trims whitespace before validation. |
| User pastes a multi-line string into the address field | System strips newlines and whitespace, then validates. |
| User submits the form with an empty address field | Error: "Please enter a wallet address." |
| User tries to add wallet #51 | "Add Wallet" is disabled; message shown (FR-009). |
| User removes the last wallet | Dashboard shows an empty state: "No wallets tracked. Add a wallet to get started." |
| API is unreachable when fetching balance for a newly added wallet | Wallet is saved. Balance shows "Pending..." until the next successful refresh. A warning is displayed: "Could not fetch balance for {tag}. Will retry on next refresh." |

#### 5.1.f Acceptance Criteria

- **Given** no wallets exist, **When** the user adds a valid BTC wallet with tag "Savings", **Then** the wallet list shows one entry with tag "Savings", network "BTC", and the current balance.
- **Given** 50 wallets exist, **When** the user tries to add another, **Then** the Add Wallet button is disabled and a limit message is displayed.
- **Given** a wallet "Mining Rig" exists, **When** the user edits the tag to "Old Mining Rig", **Then** the wallet list and all dashboard widgets reflect the new tag.
- **Given** a wallet exists, **When** the user removes it and confirms, **Then** the wallet and all its snapshots are deleted and the dashboard no longer shows it.
- **Given** the user enters an invalid BTC address (e.g., "not-a-real-address"), **When** they submit the form, **Then** an inline validation error appears and the form remains open with the input preserved.

---

### F2: Balance Retrieval

#### 5.2.a Description and Purpose

Fetches the current balance of each registered wallet from public blockchain APIs. This is the core data pipeline that feeds the dashboard.

#### 5.2.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-011 | The system shall query the appropriate public blockchain API for each registered wallet to retrieve its current balance in native coin. |
| FR-012 | The system shall use a public Bitcoin API (e.g., Mempool.space, Blockchair) to retrieve BTC wallet balances. |
| FR-013 | The system shall use the public Kaspa REST API to retrieve KAS wallet balances. |
| FR-014 | The system shall store each successful balance retrieval as a snapshot (wallet ID, balance, timestamp). |
| FR-015 | The system shall support manual (on-demand) refresh triggered by the user. |
| FR-016 | The system shall support automatic (periodic) refresh via the background scheduler (see F7). |
| FR-017 | The system shall display a "Last updated" timestamp on the dashboard indicating when balances were last successfully fetched. |
| FR-018 | The system shall rate-limit outgoing API requests to stay within the free-tier limits of each external API. |

#### 5.2.c User Interaction Flow

- **Manual refresh:** User clicks "Refresh" button on the dashboard. A loading indicator appears. Once all balances are fetched (or have failed/timed out), the dashboard updates and the loading indicator clears.
- **Automatic refresh:** Happens silently in the background. Dashboard updates in place when new data arrives. No explicit user action required.

#### 5.2.d Business Rules

- IF a wallet's balance fetch fails THEN the system retains the most recent successful balance and marks the wallet with a warning icon and tooltip: "Last update failed. Showing data from {last_success_timestamp}."
- IF all wallets fail to update THEN the dashboard shows a banner: "Unable to reach blockchain APIs. Displaying cached data from {timestamp}."
- IF a manual refresh is triggered while another refresh is already in progress THEN the system ignores the second request and shows a message: "Refresh already in progress."

#### 5.2.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| API returns HTTP 429 (rate limited) | Log the event. Retry after the period indicated in the response headers, or after 60 seconds if no header is present. Mark wallet as "pending update." |
| API returns HTTP 5xx | Log the event. Do not retry immediately. Mark the wallet with a warning. Retry on the next scheduled refresh. |
| API request times out (>30 seconds) | Abort the request. Log a timeout warning. Mark the wallet with a warning. |
| API returns a balance of 0 for a known-funded wallet | Accept and store the result (the wallet may legitimately have been emptied). Do not treat zero as an error. |
| Network is completely unreachable | All fetches fail. Dashboard shows the banner described in business rules. Cached data remains visible. |

#### 5.2.f Acceptance Criteria

- **Given** 3 wallets are registered, **When** the user clicks Refresh, **Then** balances for all 3 wallets are fetched and the "Last updated" timestamp changes to the current time.
- **Given** one API call fails, **When** refresh completes, **Then** the successful wallets update, the failed wallet shows a warning, and cached data is preserved.

---

### F3: Price Retrieval

#### 5.3.a Description and Purpose

Fetches the current USD spot prices for BTC and KAS from the CoinGecko API so that wallet balances can be displayed in USD and the portfolio value can be computed.

#### 5.3.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-019 | The system shall query the CoinGecko API for the current BTC/USD and KAS/USD prices. |
| FR-020 | The system shall store each successful price retrieval as a price snapshot (coin, USD price, timestamp). |
| FR-021 | The system shall fetch prices on the same schedule as balance retrieval (both manual and automatic refresh). |
| FR-022 | The system shall display the current BTC/USD and KAS/USD prices on the dashboard. |

#### 5.3.c User Interaction Flow

Prices are fetched as part of the general refresh cycle (manual or automatic). No separate user action is needed.

#### 5.3.d Business Rules

- IF the CoinGecko API is unavailable THEN the system uses the most recent cached price and displays a note: "Prices may be outdated (last updated {timestamp})."
- Price snapshots are stored alongside balance snapshots so that historical USD values can be computed accurately (i.e., the USD value of a balance at time T uses the price at time T, not the current price).

#### 5.3.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| CoinGecko returns stale or delayed data | Accept it — the system has no way to detect this. |
| CoinGecko rate limit exceeded | Same handling as balance API rate limits (FR-018 / edge cases in F2). |
| CoinGecko returns price = 0 | Treat as an error. Log a warning. Retain the previous cached price. Display a warning: "Price data may be unreliable." |
| No cached price exists (first run, API unreachable) | USD values display as "N/A" until a successful price fetch. |

#### 5.3.f Acceptance Criteria

- **Given** the system has never fetched prices, **When** the first successful refresh completes, **Then** BTC/USD and KAS/USD prices are displayed on the dashboard.
- **Given** CoinGecko is unreachable, **When** a refresh is triggered, **Then** cached prices are used and a staleness note is shown.

---

### F4: Historical Data

#### 5.4.a Description and Purpose

Provides historical balance data for charts by combining two sources: (1) a one-time full retrieval of past transaction history from the blockchain when a wallet is first added, and (2) incremental transaction syncing on each subsequent refresh cycle. All transaction data is stored locally so that the blockchain API is never asked for the same data twice. This enables the user to see how a wallet's balance — and the portfolio's total value — have evolved over time with transaction-level granularity.

#### 5.4.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-023 | The system shall, upon adding a new wallet, perform a one-time full retrieval of the wallet's transaction history from the blockchain API. |
| FR-024 | The system shall store all retrieved transactions locally (wallet ID, transaction ID/hash, amount, direction, timestamp). |
| FR-025 | The system shall reconstruct historical balances by replaying stored transactions in chronological order, computing a daily end-of-day balance for each historical day. |
| FR-026 | The system shall, on each refresh cycle (manual or automatic), perform an incremental sync: fetch only transactions newer than the most recent locally stored transaction for each wallet. |
| FR-027 | The system shall never re-fetch transactions that are already stored locally. The blockchain API is queried only for new data. |
| FR-028 | The system shall compute the current balance from stored transactions rather than relying solely on the balance endpoint, using the balance API call as a consistency check. |
| FR-029 | The system shall merge historical and incrementally synced data seamlessly in charts, with no visible gap or duplication. |
| FR-030 | The system shall retrieve historical BTC/USD and KAS/USD prices from CoinGecko (which offers free historical price data) to compute USD values for historical balances. |

#### 5.4.c User Interaction Flow

- **On wallet addition:** Full transaction history is fetched. A progress indicator is shown: "Loading transaction history for {tag}..." If retrieval takes more than a few seconds, the dashboard is still usable — the history loads in the background and charts update when ready.
- **On each refresh (manual or automatic):** Incremental sync runs silently. Only new transactions since the last known one are fetched. This is transparent to the user — charts simply gain new data points.
- Charts display the full timeline from all stored transactions, with no distinction between initially imported and incrementally synced data.

#### 5.4.d Business Rules

- IF the blockchain API limits how far back transaction history can be retrieved THEN the system fetches as much as is available and notes the earliest available date.
- IF a wallet has a very large transaction history (>10,000 transactions) THEN the system fetches it in pages and may take longer, but must complete without erroring out.
- IF historical price data from CoinGecko is unavailable for a given date THEN the system uses the nearest available date's price, annotating the data point as "estimated."
- Transactions are immutable once stored. The system identifies the most recent stored transaction (by timestamp or block height) and requests only newer ones from the API.
- IF the balance computed from stored transactions does not match the balance reported by the API THEN log a warning and store the API-reported balance as authoritative. This covers edge cases like undetected chain reorganizations.

#### 5.4.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| Wallet has zero transactions (just received one large deposit) | Historical balance shows 0 before the deposit and the deposited amount after. |
| Blockchain API fails during initial history retrieval | Wallet is saved, live balance is fetched. History shows a message: "Transaction history could not be loaded. Historical charts will begin from the date this wallet was added." Retry is possible via a "Retry" button on the wallet. |
| Blockchain API fails during incremental sync | Log the failure. Retry on the next refresh cycle. Existing data is unaffected. |
| Transaction history is enormous (>100k transactions) | System processes in batches. A progress indicator updates. If it exceeds a 5-minute timeout, partial history is stored and a note displayed. Incremental syncs will pick up from where the import left off. |
| CoinGecko does not have price data before a certain date (e.g., KAS before listing) | USD values for those dates are shown as "N/A" on charts. Balance in native coin is still shown. |
| Computed balance from transactions doesn't match API-reported balance | Log a warning. Use the API-reported balance as authoritative. A small discrepancy icon may be shown on the wallet in the UI. |
| Duplicate transaction returned by API (already stored locally) | Deduplicate by transaction ID/hash. Do not store a second copy. |

#### 5.4.f Acceptance Criteria

- **Given** a BTC wallet with 6 months of transaction history, **When** the user adds it, **Then** the balance-over-time chart shows daily balances going back 6 months.
- **Given** a wallet was added 3 days ago and has received 2 new transactions since, **When** a refresh cycle completes, **Then** the 2 new transactions are fetched and stored, and the chart extends with the new data points.
- **Given** a wallet's transactions are already fully stored locally, **When** a refresh cycle runs and no new transactions exist, **Then** the blockchain API is queried only for transactions newer than the last stored one (not the full history), resulting in minimal API usage.

---

### F5: Dashboard

#### 5.5.a Description and Purpose

The main screen of the application. Presents a collection of widgets and charts that give the user a comprehensive view of their crypto portfolio's current state and historical evolution.

#### 5.5.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-031 | The system shall display a dashboard as the application's main screen (landing page). |
| FR-032 | The dashboard shall include the following widgets (see detailed descriptions below): Total Portfolio Value (USD), Total BTC Balance, Total KAS Balance, Wallet Table, Portfolio Composition Pie Chart, Portfolio Value Over Time (line chart), Per-Wallet Balance Over Time (line chart), Price Chart (BTC/USD and KAS/USD). |
| FR-033 | The dashboard shall be responsive and usable on screen widths from 360px (mobile) to 1920px+ (desktop). |
| FR-034 | All monetary values shall be displayed with appropriate precision: USD to 2 decimal places, BTC to 8 decimal places, KAS to 2 decimal places. |
| FR-035 | The dashboard shall display a "Last updated" timestamp showing when data was last successfully refreshed. |
| FR-036 | The dashboard shall include a manual "Refresh" button. |
| FR-037 | The dashboard shall show an empty state with a call-to-action when no wallets are registered. |

#### Widget Specifications

**W1: Total Portfolio Value (USD)**
- Large, prominent number showing the sum of all wallets' balances converted to USD.
- Shows absolute value and 24-hour change (amount and percentage).
- IF no price data is available THEN display "N/A" instead of a number.

**W2: Total BTC Balance**
- Sum of all BTC wallet balances, displayed in BTC.
- Below it, the equivalent USD value.

**W3: Total KAS Balance**
- Sum of all KAS wallet balances, displayed in KAS.
- Below it, the equivalent USD value.

**W4: Wallet Table**
- Columns: Tag, Network, Address (truncated, full on hover/tap), Balance (native coin), Balance (USD).
- Sortable by any column.
- Clicking a wallet row navigates to/opens a detail view for that wallet (showing its individual balance-over-time chart and transaction history timeline).

**W5: Portfolio Composition Pie Chart**
- Segments: one per network (BTC, KAS), sized by USD value.
- Labels show percentage and absolute USD value.
- IF only one network has wallets THEN show a full circle with a label, not a pie chart.

**W6: Portfolio Value Over Time (Line Chart)**
- X-axis: time. Y-axis: USD value.
- Shows the total portfolio value over time.
- Time range selector: 7 days, 30 days, 90 days, 1 year, All.
- Default range: 30 days.
- Data points come from snapshots (historical + forward-looking).

**W7: Per-Wallet Balance Over Time (Line Chart)**
- Accessible from the wallet detail view (click a row in W4) or as a filterable chart on the dashboard.
- One line per selected wallet. Balance in native coin or USD (toggle).
- Same time range selector as W6.

**W8: Price Chart (BTC/USD and KAS/USD)**
- Two lines on a dual-axis or separate small charts.
- Time range selector matching W6.
- Shows price history from stored price snapshots and CoinGecko historical data.

#### 5.5.c User Interaction Flow

1. User opens the application — dashboard loads with all widgets.
2. Widgets populate from cached data first (instant), then update if a background refresh completes.
3. User can interact with charts: hover for tooltips, select time ranges, toggle between native coin and USD views.
4. User can click a wallet row in W4 to see the per-wallet detail view.
5. User can click "Refresh" to trigger a manual update.

#### 5.5.d Business Rules

- All USD calculations use the price snapshot closest in time to the balance snapshot being displayed.
- 24-hour change (W1) is calculated by comparing the current portfolio USD value with the value from the snapshot closest to 24 hours ago. IF no snapshot exists from ~24h ago THEN 24-hour change displays "N/A."
- Chart time ranges with no data show an empty chart with a message: "Not enough data for this time range."

#### 5.5.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| No wallets registered | Dashboard shows empty state: "No wallets tracked. Add a wallet to get started." with a prominent "Add Wallet" button. |
| Only BTC wallets, no KAS | Total KAS Balance widget shows "0 KAS". Pie chart shows 100% BTC. |
| Prices unavailable | USD-dependent widgets show "N/A". Charts that require USD can toggle to native-coin view. |
| Very small balances (e.g., 0.00000001 BTC) | Displayed correctly to 8 decimal places (satoshi precision). |
| Very large balances | Formatted with thousands separators (e.g., 1,234,567.89 KAS). |

#### 5.5.f Acceptance Criteria

- **Given** 2 BTC wallets and 1 KAS wallet, **When** the user opens the dashboard, **Then** all 8 widgets are visible and populated.
- **Given** a 30-day snapshot history, **When** the user selects "30 days" on the portfolio chart, **Then** a line chart with ~30 data points is displayed.
- **Given** the user is on a 375px-wide mobile screen, **When** they view the dashboard, **Then** all widgets are visible, scrollable, and no content is cut off or overlapping.

---

### F6: Configuration Panel

#### 5.6.a Description and Purpose

A settings screen where the user can adjust application behavior, most importantly the automatic refresh interval.

#### 5.6.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-038 | The system shall provide a configuration panel accessible from the dashboard (e.g., a gear icon). |
| FR-039 | The configuration panel shall allow the user to set the automatic refresh interval, choosing from: 5 minutes, 15 minutes (default), 30 minutes, 1 hour, or disabled. |
| FR-040 | The system shall persist configuration changes to the database so they survive application restarts. |
| FR-041 | Changes to the refresh interval shall take effect immediately (the scheduler restarts with the new interval). |
| FR-042 | The configuration panel shall display the current value of each setting. |

#### 5.6.c User Interaction Flow

1. User clicks the settings/gear icon on the dashboard.
2. Configuration panel opens (modal or dedicated page).
3. User adjusts the refresh interval via a dropdown or radio buttons.
4. User clicks "Save" (or changes auto-save).
5. A confirmation is shown: "Settings saved."
6. The background scheduler immediately adopts the new interval.

#### 5.6.d Business Rules

- IF the user disables automatic refresh THEN no background polling occurs; the user must refresh manually.
- IF the application restarts THEN it reads the saved configuration and starts the scheduler with the saved interval.
- Default refresh interval: 15 minutes.

#### 5.6.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| User saves settings while a refresh is in progress | The in-progress refresh completes. The new interval applies starting from the next cycle. |
| Database write fails when saving settings | Error message: "Could not save settings. Please try again." Settings revert to previous values in the UI. |

#### 5.6.f Acceptance Criteria

- **Given** the refresh interval is set to 15 minutes, **When** the user changes it to 5 minutes and saves, **Then** the next automatic refresh occurs within 5 minutes.
- **Given** the user disables automatic refresh, **When** 30 minutes pass, **Then** no automatic refresh has occurred.

---

### F7: Background Scheduler

#### 5.7.a Description and Purpose

A server-side process that periodically triggers balance and price fetches without user interaction, ensuring the dashboard stays reasonably up to date.

#### 5.7.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-043 | The system shall run a background task that triggers a full refresh (all wallet balances + prices) at the configured interval. |
| FR-044 | The scheduler shall start automatically when the application starts, using the saved refresh interval. |
| FR-045 | The scheduler shall restart with a new interval when the configuration changes (FR-041). |
| FR-046 | The scheduler shall log each run (start time, end time, success/failure per wallet). |
| FR-047 | The scheduler shall not run concurrent refresh cycles. If a cycle is still running when the next is due, the next cycle is skipped and logged as "skipped — previous cycle still running." |

#### 5.7.c User Interaction Flow

The scheduler has no direct user-facing interaction. Its effects are visible through updated data on the dashboard and the "Last updated" timestamp.

#### 5.7.d Business Rules

- IF the configured interval is "disabled" THEN the scheduler does not run.
- IF the application starts and there are zero wallets THEN the scheduler starts but each cycle is a no-op (fetch prices only).

#### 5.7.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| Application crashes mid-refresh | On restart, the scheduler begins a fresh cycle. Partial snapshot data from the interrupted cycle (if any was committed) is retained. |
| All API calls fail for multiple consecutive cycles | The scheduler continues running at the configured interval. No data is lost. Warning state persists on the dashboard. |

#### 5.7.f Acceptance Criteria

- **Given** refresh interval is 5 minutes and 3 wallets are registered, **When** 5 minutes elapse, **Then** balances for all 3 wallets and prices for BTC/KAS are fetched and stored without user action.
- **Given** a refresh cycle takes 4 minutes and the interval is 5 minutes, **When** the next cycle is due 1 minute after the previous one ends, **Then** the next cycle runs at the 1-minute mark (not skipped).

---

### F8: Authentication

#### 5.8.a Description and Purpose

Provides single-user authentication: a one-time account setup on first launch, login/logout, and session management. Protects the dashboard and all API endpoints from unauthorized access so the application can be safely exposed beyond localhost.

#### 5.8.b Functional Requirements

| ID | Requirement |
|---|---|
| FR-048 | The system shall detect on startup whether a user account exists in the database. If no account exists, all requests shall be redirected to the first-run setup page. |
| FR-049 | The first-run setup page shall allow the user to create an account by entering a username and a password (entered twice for confirmation). |
| FR-050 | The system shall enforce minimum password requirements: at least 8 characters. |
| FR-051 | The system shall store passwords using a secure, salted hash (functional requirement: plaintext passwords are never stored or logged). |
| FR-052 | After account creation, the system shall automatically log the user in and redirect to the dashboard. |
| FR-053 | The system shall display a login page for unauthenticated users (when an account already exists). |
| FR-054 | The login page shall accept a username and password, and include a "Remember me" checkbox. |
| FR-055 | On successful login, the system shall create a session and redirect the user to the dashboard. |
| FR-056 | Sessions shall expire after 7 days of inactivity. If "Remember me" was checked, sessions shall expire after 30 days of inactivity. |
| FR-057 | The system shall provide a logout action (accessible from the dashboard UI) that invalidates the current session and redirects to the login page. |
| FR-058 | All API endpoints (except login and first-run setup) shall require a valid session. Requests without a valid session shall return an appropriate error (HTTP 401) or redirect to the login page. |
| FR-059 | The first-run setup page shall not be accessible once an account exists. Navigating to it shall redirect to the login page. |
| FR-060 | The system shall support a CLI command to reset the user's password (for recovery when the password is forgotten). |

#### 5.8.c User Interaction Flow

**First-Run Setup:**

1. User opens the application for the first time.
2. System shows a setup page with: username field, password field, confirm password field, and a "Create Account" button.
3. User fills in the fields and clicks "Create Account."
4. On validation error (password mismatch, too short): inline error message; form preserved.
5. On success: account created, user logged in, redirected to the empty dashboard.

**Login:**

1. User opens the application (account exists, no active session).
2. System shows the login page with: username field, password field, "Remember me" checkbox, "Log In" button.
3. User enters credentials and clicks "Log In."
4. On invalid credentials: error message "Invalid username or password." Username field preserved, password field cleared.
5. On success: session created, redirected to the dashboard.

**Logout:**

1. User clicks a logout button/link (e.g., in a user menu or header).
2. Session is invalidated server-side.
3. User is redirected to the login page.

**Password Reset (CLI):**

1. Administrator runs a CLI command (e.g., `python manage.py reset-password`).
2. Command prompts for a new password (entered twice).
3. Password is updated in the database.
4. All existing sessions are invalidated (forces re-login).

#### 5.8.d Business Rules

- IF the password and confirmation do not match THEN reject with message: "Passwords do not match."
- IF the password is fewer than 8 characters THEN reject with message: "Password must be at least 8 characters."
- IF login credentials are invalid THEN display a generic message ("Invalid username or password") — do not reveal whether the username or password was wrong.
- IF a user is already logged in and navigates to the login page THEN redirect to the dashboard.
- IF the session has expired THEN treat as unauthenticated — redirect to login on the next request.
- The background scheduler (F7) operates independently of user sessions — it does not require a logged-in user to run.

#### 5.8.e Edge Cases and Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| User navigates directly to a dashboard URL without a session | Redirected to login page. After login, redirected back to the originally requested URL. |
| User submits the first-run setup form when an account already exists (race condition or direct URL access) | Reject with redirect to login page. Only one account can exist. |
| User has multiple browser tabs open and logs out in one | Other tabs redirect to login on the next interaction (API call returns 401, frontend redirects). |
| Session cookie is tampered with | Server rejects the invalid session. User is redirected to login. |
| User forgets password and has no CLI access | No recovery path — this is documented as a known limitation. The user must access the server to run the CLI reset command. |
| Brute-force login attempts | Rate-limit login attempts: after 5 consecutive failures, impose a 30-second delay before the next attempt is accepted. Display: "Too many failed attempts. Please wait before trying again." |

#### 5.8.f Acceptance Criteria

- **Given** a fresh installation with no account, **When** the user opens the app, **Then** the first-run setup page is displayed.
- **Given** the setup page is shown, **When** the user creates an account with valid credentials, **Then** they are logged in and see the empty dashboard.
- **Given** an account exists, **When** the user navigates to the app without a session, **Then** the login page is displayed.
- **Given** the login page is shown, **When** the user enters correct credentials, **Then** they are redirected to the dashboard.
- **Given** the login page is shown, **When** the user enters wrong credentials, **Then** an error is shown and the password field is cleared.
- **Given** a logged-in user, **When** they click logout, **Then** their session is invalidated and they see the login page.
- **Given** a session is 7 days old (without "Remember me"), **When** the user makes a request, **Then** they are redirected to login.
- **Given** the user has forgotten their password, **When** an admin runs the CLI reset command, **Then** the password is updated and all sessions are invalidated.

---

## 6. Data Requirements

### 6.1 Data Entities

**User**

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-generated. Always 1 in single-user mode. |
| username | String | Yes | Unique. Max 50 characters. |
| password_hash | String | Yes | Salted hash of the user's password. |
| created_at | Datetime | Yes | When the account was created. |

**Session**

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-generated. |
| user_id | Integer (FK) | Yes | References User. |
| token | String | Yes | Unique, cryptographically random session token. |
| created_at | Datetime | Yes | When the session was created. |
| expires_at | Datetime | Yes | 7 days from creation (default) or 30 days ("Remember me"). |

**Wallet**

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-generated. |
| user_id | Integer (FK) | Yes | References User. Defaults to 1 (single-user). |
| network | Enum (BTC, KAS) | Yes | |
| address | String | Yes | Unique per (network, user_id). |
| tag | String | Yes | Max 50 characters. Unique (case-insensitive). Default auto-generated. |
| created_at | Datetime | Yes | When the wallet was added. |

**Transaction**

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-generated. |
| wallet_id | Integer (FK) | Yes | References Wallet. |
| tx_hash | String | Yes | Blockchain transaction ID/hash. Unique per (wallet_id, tx_hash). |
| amount | Decimal | Yes | Signed amount in native coin (positive = inflow, negative = outflow). High precision (18 decimal places). |
| balance_after | Decimal | No | Running balance after this transaction, if computable. |
| block_height | Integer | No | Block number, used for ordering and incremental sync cursor. |
| timestamp | Datetime | Yes | When the transaction was confirmed on-chain. |
| created_at | Datetime | Yes | When this record was stored in CryptoDash. |

**Balance Snapshot**

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-generated. |
| wallet_id | Integer (FK) | Yes | References Wallet. |
| balance | Decimal | Yes | In native coin. High precision (18 decimal places for safety). |
| timestamp | Datetime | Yes | When this balance was recorded. |
| source | Enum (live, historical) | Yes | "live" for periodic snapshots; "historical" for reconstructed from transactions. |

**Price Snapshot**

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-generated. |
| coin | Enum (BTC, KAS) | Yes | |
| price_usd | Decimal | Yes | Precision to 8 decimal places. |
| timestamp | Datetime | Yes | |

**Configuration**

| Field | Type | Required | Notes |
|---|---|---|---|
| key | String (PK) | Yes | Setting name (e.g., "refresh_interval_minutes"). |
| value | String | Yes | Setting value (serialized as string). |
| updated_at | Datetime | Yes | |

### 6.2 Entity Relationships

- **User → Session**: one-to-many. A user has many sessions (e.g., across devices).
- **User → Wallet**: one-to-many. A user has many wallets.
- **Wallet → Transaction**: one-to-many. A wallet has many transactions.
- **Wallet → Balance Snapshot**: one-to-many. A wallet has many balance snapshots.
- **Price Snapshot**: independent entity. Linked to balance snapshots by timestamp proximity when computing USD values.
- **Configuration**: independent key-value store. No relationships.

### 6.3 Entity Lifecycle

- **User**: created once during first-run setup. Updated when password is reset via CLI. Never deleted.
- **Session**: created on login. Never updated. Deleted on logout, password reset (all sessions), or when expired (cleanup).
- **Wallet**: created when user adds it. Updated when tag is edited. Deleted when user removes it — cascade deletes all associated transactions and balance snapshots.
- **Transaction**: created during initial history import and incremental sync. Never updated or deleted (immutable). Deleted only when the parent wallet is deleted.
- **Balance Snapshot**: created on each refresh cycle and derived from transaction replay. Never updated. Deleted only when the parent wallet is deleted.
- **Price Snapshot**: created on each refresh cycle and during historical price import. Never updated or deleted (grows over time).
- **Configuration**: created on first access with default values. Updated when user changes settings. Never deleted.

### 6.4 Data Validation Rules

- Username: non-empty after trimming, max 50 characters.
- Password: at least 8 characters.
- Wallet address: validated per network rules (see F1 business rules).
- Tag: non-empty after trimming, max 50 characters.
- Balance: must be >= 0.
- Price: must be > 0 (zero prices are treated as errors, see F3).
- Refresh interval: must be one of the allowed values (5, 15, 30, 60 minutes, or disabled).

### 6.5 Data Retention and Cleanup

- **Balance snapshots**: retained indefinitely. No automatic cleanup. (Future versions may add downsampling for very old data.)
- **Price snapshots**: retained indefinitely.
- **Wallet data**: retained until the user explicitly removes the wallet.
- **Database growth**: with 50 wallets at 15-minute intervals, this is ~4,800 balance snapshots/day + ~192 price snapshots/day (~5,000/day total). At ~100 bytes/row, this is ~500 KB/day, or ~180 MB/year. Acceptable for SQLite.

---

## 7. External Interfaces

### 7.1 Bitcoin Blockchain API

- **System:** Public Bitcoin blockchain API (primary candidate: Mempool.space; fallback: Blockchair).
- **Purpose:** Retrieve wallet balances and transaction history for BTC addresses.
- **Direction:** Inbound (CryptoDash reads from API).
- **Protocol:** REST API over HTTPS.
- **Data exchanged:**
  - Request: wallet address.
  - Response: current confirmed balance (in satoshis); list of transactions with amounts and timestamps.
- **Failure handling:** Retry once after 10 seconds. On second failure, use cached data and mark wallet with a warning.
- **Dependency criticality:** Soft dependency. CryptoDash functions in degraded mode (stale data) without it.

### 7.2 Kaspa Blockchain API

- **System:** Public Kaspa REST API (api.kaspa.org).
- **Purpose:** Retrieve wallet balances and transaction history for KAS addresses.
- **Direction:** Inbound.
- **Protocol:** REST API over HTTPS.
- **Data exchanged:**
  - Request: wallet address.
  - Response: current balance (in sompi); list of transactions with amounts and timestamps.
- **Failure handling:** Same as Bitcoin API.
- **Dependency criticality:** Soft dependency.

### 7.3 CoinGecko API

- **System:** CoinGecko free API.
- **Purpose:** Retrieve current and historical BTC/USD and KAS/USD prices.
- **Direction:** Inbound.
- **Protocol:** REST API over HTTPS.
- **Data exchanged:**
  - Request: coin ID (`bitcoin`, `kaspa`), target currency (`usd`).
  - Response: current spot price; historical daily prices for a given date range.
- **Failure handling:** On failure, use cached prices. Display staleness note.
- **Dependency criticality:** Soft dependency. Dashboard functions without it but cannot show USD values.
- **Rate limits:** CoinGecko free tier allows ~10-30 calls/minute. The system must batch requests and respect these limits.

---

## 8. Non-Functional Requirements

### 8.a Performance

- Dashboard initial load: < 2 seconds (from cached data).
- Manual refresh (all wallets + prices): < 15 seconds for up to 50 wallets.
- Historical data import for a new wallet: < 60 seconds for wallets with up to 10,000 transactions. Wallets with more show a progress indicator.
- Chart rendering: < 1 second for up to 1 year of daily data points.

### 8.b Reliability and Availability

- The application is self-hosted, so availability depends on the host machine. No uptime SLA.
- The application must not crash or lose data if an external API is temporarily unavailable.
- SQLite database must be protected against corruption from unclean shutdowns (use WAL mode).
- All data writes must be transactional — a partial refresh failure must not leave the database in an inconsistent state.

### 8.c Security

- **Authentication:** Single-user login required (see F8). Passwords stored as salted hashes. Sessions expire after 7 or 30 days.
- **Brute-force protection:** Login rate-limited to 5 consecutive failures before a 30-second lockout.
- **Session management:** Session tokens are cryptographically random. Transmitted via secure, HTTP-only cookies. All sessions invalidated on password reset.
- **No private keys or seed phrases** are ever entered, stored, or transmitted. The system handles only public wallet addresses.
- **Input validation:** All user-supplied data (wallet addresses, tags, configuration values) is validated server-side.
- **API calls:** All outgoing API calls use HTTPS.
- **Data sensitivity:** Wallet addresses are semi-public (visible on the blockchain). Balance data reveals the user's holdings — sensitive in aggregate. The SQLite database file should be treated as sensitive. The password hash is sensitive.
- **No audit logging required** in this version.

### 8.d Scalability

- Designed for a single user with up to 50 wallets. No multi-user scaling concerns in this version.
- SQLite is adequate for this scale. Migration to a client-server database is not needed.
- If a future version adds multi-user support, the database and API layer will need reassessment.

### 8.e Usability

- **Responsive design:** Functional from 360px to 1920px+ screen widths.
- **Accessibility:** Basic accessibility: semantic HTML, sufficient color contrast, keyboard-navigable controls. Full WCAG 2.1 AA compliance is out of scope for this version.
- **Internationalization:** Out of scope. UI in English only. Numbers follow US formatting conventions (period as decimal separator, comma as thousands separator).
- **Dark/light mode:** Nice-to-have. If the chosen frontend framework supports it easily, include it. Otherwise, out of scope.

---

## 9. Constraints and Assumptions

### Constraints

| Constraint | Type | Detail |
|---|---|---|
| SQLite | Technical | Storage must use SQLite (file-based, no external database server). |
| Python backend | Technical | Backend must be written in Python. |
| Free-tier APIs only | Business | No paid API subscriptions. All external data sources must be free to use. |
| Read-only blockchain access | Technical | The system never submits transactions. Only public read APIs are used. |

### Assumptions

| # | Assumption | Impact if Wrong |
|---|---|---|
| A1 | The user runs the application on a machine with reliable internet access. | Without internet, no balance or price updates are possible. Cached data remains available. |
| A2 | Public blockchain APIs (Mempool.space, Kaspa API) remain available and free. | If APIs are discontinued or paywalled, alternative providers must be configured. The system should abstract the API layer so providers can be swapped. |
| A3 | CoinGecko's free tier continues to support BTC and KAS price queries. | If CoinGecko restricts access, an alternative price provider must be integrated. |
| A4 | Kaspa transaction history is fully available via the public API. | If history is limited, retroactive balance reconstruction will be partial. The system should handle this gracefully (display data from the earliest available point). |
| A5 | 50 wallets is sufficient for a single user. | If users need more, the limit can be raised — there is no architectural reason for the cap beyond UI manageability. |

---

## 10. Release and Phasing

### Single Release

All features described in this specification (F1–F8) are delivered in a single release. The scope is compact enough that phasing would add coordination overhead without meaningful risk reduction.

**Full feature set:**

- Authentication (first-run setup, login, logout, session management, CLI password reset)
- Wallet management (add, edit tag, remove) with address validation
- Balance retrieval from public APIs (manual and automatic refresh)
- Price retrieval from CoinGecko
- Historical balance reconstruction from blockchain transaction history with incremental sync
- Dashboard with all widgets (Total Portfolio Value, Total BTC/KAS Balance, Wallet Table, Portfolio Composition Pie Chart, Portfolio Value Over Time, Per-Wallet Balance Over Time, Price Chart)
- 24-hour change calculation
- Configuration panel (refresh interval)
- Background scheduler
- SQLite storage
- Responsive layout

### Suggested Build Order

While all features ship together, the following build order reflects natural dependencies:

1. **Database schema and authentication (F8)** — foundation; everything else sits behind login.
2. **Wallet management (F1)** — CRUD for wallets; needed before any data fetching.
3. **Balance retrieval (F2) and price retrieval (F3)** — core data pipeline.
4. **Historical data and incremental sync (F4)** — builds on the same API clients as F2/F3.
5. **Dashboard (F5)** — consumes all stored data.
6. **Background scheduler (F7) and configuration panel (F6)** — automation layer on top of the working refresh logic.

---

## 11. Open Questions & Decisions Log

| # | Topic | Ambiguity | Decision | Justification | Review Needed? |
|---|---|---|---|---|---|
| OQ-1 | Bitcoin API provider | Input says "public APIs" but doesn't name a specific provider. | Default to Mempool.space as primary (fully open, no API key). Blockchair as documented fallback. | Mempool.space is free, open-source, and widely used. No API key required for basic queries. | No |
| OQ-2 | Kaspa API provider | Not specified. | Use api.kaspa.org (the official Kaspa REST API). | It is the canonical public API for the Kaspa network. | No |
| OQ-3 | BTC address types | Input mentions "Bitcoin network" but doesn't specify which address types. | Support all four common types: P2PKH (1...), P2SH (3...), Bech32/SegWit (bc1q...), Taproot (bc1p...). | These cover the vast majority of Bitcoin addresses in active use. | No |
| OQ-4 | Historical price source | Input confirmed CoinGecko but didn't mention historical prices. | Use CoinGecko's `/coins/{id}/market_chart/range` endpoint for historical daily prices. | CoinGecko's free tier supports this. Needed to compute historical USD values for balance charts. | No |
| OQ-5 | Frontend framework | Input mentions "vue.js? vanilla js? explore possibilities" — deferred to tech spec. | Not decided in this functional spec. The tech spec will evaluate options. | This is a technical implementation choice, not a functional one. | Deferred to tech spec |
| OQ-6 | Backend framework | Input mentions "maybe FastAPI?" — deferred to tech spec. | Not decided in this functional spec. | Same as above. | Deferred to tech spec |
| OQ-7 | Dark/light mode | Not mentioned in input. | Classified as nice-to-have (see NFR 8.e). Include if the frontend framework makes it easy. | Low risk either way. Modern frameworks often provide this for minimal effort. | No |
| OQ-8 | Multi-user migration path | User wants single-user auth now, multi-user later. | Auth is in scope (F8) with a single account. Data model includes `user_id` FK (defaulting to 1). Multi-user registration is out of scope but the schema supports it without restructuring. | Prevents a painful migration later at near-zero cost now. | No |
| OQ-9 | Blockchain history depth | User wants to browse past balances from blockchain history. Depth depends on API capabilities. | Fetch as much history as the public API provides. Document the limitation per API. | We cannot control API limitations. Graceful handling of partial history is specified in F4. | No |
| OQ-10 | Snapshot downsampling | Long-running instances will accumulate many snapshots. | No downsampling in this version. Storage estimate (~180 MB/year) is acceptable for SQLite. | Premature optimization. Can be added if database size becomes a problem. | No |

---

*End of Functional Specification.*