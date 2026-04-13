# T11 Frontend Foundation — Review

## Round 1 (initial)

**Result: CHANGES REQUIRED**

All automated checks passed. Six issues filed:

| # | Severity | File | Summary |
|---|----------|------|---------|
| 1 | High | `frontend/src/types/websocket.ts` | Discriminant field `type`/`payload` does not match wire format `event`/`data`/`timestamp` |
| 2 | Medium | `frontend/src/utils/format.ts:37` | Function exported as `formatDateTime`; spec requires `formatTimestamp` |
| 3 | Medium | `frontend/src/components/common/EmptyState.vue` | Uses `title`/`subtitle` props; spec requires `message` prop |
| 4 | Medium | `frontend/src/composables/useApi.ts:8` | `useRouter()` called at composable root; breaks when called from store actions |
| 5 | Low | `frontend/src/style.css` | Three token values differ from mockups; two tokens missing (`--bg-subtle`, `--border-focus`) |
| 6 | Low | `tests/node_modules` symlink | Fragile symlink destroyed by `npm ci`; `vitest.config.ts` `moduleDirectories` should suffice |

**Spec ambiguity noted:** Task spec acceptance criterion for `truncateAddress` contains a typo (`"bc1qar...mdq"` should be `"bc1qar...5mdq"`). Implementation and tests are correct.

---

## Round 2 (re-review after fixes)

**Result: APPROVED**

### Fix verification

| Issue | Fix | Verified |
|-------|-----|---------|
| 1 — WebSocket field names | All 8 interfaces now use `event` as discriminant, `data` as payload, `timestamp: string` as top-level field — matches `ConnectionManager.broadcast()` wire format exactly | Yes |
| 2 — `formatTimestamp` rename | `format.ts` exports `formatTimestamp`; `AppFooter.vue` and `format.test.ts` both updated to match | Yes |
| 3 — `EmptyState.vue` `message` prop | Component now defines a single `message: string` prop and renders it in a `<p>` | Yes |
| 4 — `useRouter()` in composable | Replaced with `import router from "@/router"` — safe to call from any context | Yes |
| 5 — CSS token values | `--bg-subtle` and `--border-focus` added. Note: the three "differing" values (`--text-muted: 0.38`, `--accent-dim: 0.1`, `--accent-glow: 0.35`) match `02-dashboard.html` and `03-wallet-detail.html` exactly; `01-login.html` uses slightly different values for the same tokens. `style.css` correctly reflects the majority view and the primary screen mockups. Original Issue 5 was a partial false positive on those three values. | Yes |
| 6 — `tests/node_modules` symlink | Symlink removed. `vitest.config.ts` now adds explicit `resolve.alias` entries pinning `vue`, `vue-router`, `pinia`, and `@vue/test-utils` to `frontend/node_modules` — a more robust solution than the symlink | Yes |

### Automated check results (round 2)

| Check | Result |
|-------|--------|
| `vue-tsc --noEmit` | PASS |
| `eslint src/` | PASS (15 warnings, 0 errors) |
| `prettier --check src/` | PASS |
| `npm run test` | PASS — 42 tests in 4 files |
| `npm run build` | PASS |

All acceptance criteria from `tasks/TASK-011.md` are met.
