# Technical Notes

Research notes, design considerations, and decision points for the technical specification. This file collects input gathered during the functional spec phase that is too implementation-specific for the functional spec but too valuable to lose.

---

## Design Decision Points

### Entity IDs: UUIDs vs. Auto-Increment Integers

The functional spec defines entity IDs at the logical level (unique identifier per entity). The tech spec must choose a concrete strategy.

**Options:**

- **Auto-increment integers:** Simple, compact, fast indexes. Sufficient for single-user SQLite. IDs are sequential and predictable (minor information leak in URLs).
- **UUIDs (v4):** Globally unique, non-sequential, safe for future multi-user/multi-node scenarios. Larger (36 chars vs. 4-8 bytes). Slightly worse index locality in SQLite.

**Recommendation:** UUIDs. The storage overhead is negligible at this scale, and they future-proof the schema for multi-user support without migration. Also avoids exposing entity counts in API responses.

### Password Hashing: Salt Storage

FR-051 requires salted password hashes. The functional spec's User entity has a `password_hash` field but no separate `salt` field — this is intentional.

Modern password hashing algorithms (bcrypt, argon2, scrypt) embed the salt, cost factor, and algorithm identifier directly in the output string. For example, bcrypt produces: `$2b$12$<22-char-salt><31-char-hash>`. A separate `salt` column is unnecessary and redundant.

**Recommendation:** Use bcrypt or argon2id. Store the full output in `password_hash`. No separate salt column needed. The tech spec should specify the algorithm and cost factor.

---

## External API Research

### Kaspa REST API

**Base URL:** `https://api.kaspa.org`
**Protocol:** REST over HTTPS, JSON responses. Served via Cloudflare.

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/addresses/{address}/balance` | GET | Returns balance in sompi (1 KAS = 100,000,000 sompi). Response: `{"address": "...", "balance": 1122651844695341}` |
| `/addresses/{address}/full-transactions?limit=N&offset=M&resolve_previous_outpoints=light` | GET | Paginated full transaction history with inputs, outputs, block times, acceptance status. The `resolve_previous_outpoints=light` param is required to populate `previous_outpoint_address` and `previous_outpoint_amount` on inputs. Without it, those fields are null. Note: `/addresses/{address}/transactions` (without "full-") returns 404. |
| `/addresses/{address}/utxos` | GET | Returns all unspent transaction outputs. |
| `/info/price` | GET | Returns KAS/USD price: `{"price": 0.03263027}`. Could be used instead of (or as fallback to) CoinGecko for KAS price. |
| `/info/coinsupply` | GET | Returns circulating and max supply. |

### Rate Limits

- No explicit rate-limit headers (`X-RateLimit-*`) in responses.
- `cache-control: public, max-age=8` on balance endpoint suggests an 8-second cache.
- Cloudflare abuse protection is in place — aggressive polling will likely be throttled or blocked.
- No documented rate limits.

### Notes

- The Kaspa Explorer (`explorer.kaspa.org`) uses the same `api.kaspa.org` backend — there is no separate explorer API.
- The API server is open-source (`kaspa-rest-server` on GitHub) and can be self-hosted against your own Kaspa node.

---

### Bitcoin API (Mempool.space)

**Base URL:** `https://mempool.space/api`
**Protocol:** REST over HTTPS, JSON responses.

*TODO: Research specific endpoints for balance, transaction history, and rate limits.*

---

### CoinGecko API

**Base URL:** `https://api.coingecko.com/api/v3`
**Protocol:** REST over HTTPS, JSON responses.

### Relevant Endpoints

| Endpoint | Description |
|---|---|
| `/simple/price?ids=bitcoin,kaspa&vs_currencies=usd` | Current spot prices for BTC and KAS in USD. |
| `/coins/{id}/market_chart/range?vs_currency=usd&from=UNIX&to=UNIX` | Historical daily prices for a date range. Used for computing USD values of historical balances. |

### Rate Limits

- Free tier: ~10-30 calls/minute (undocumented, varies).
- No API key required for basic use.

### Notes

- Kaspa API itself provides a KAS/USD price endpoint (`/info/price`). Consider using it as primary for KAS and falling back to CoinGecko, reducing CoinGecko API usage.

---

*Last updated: 2026-04-12*
