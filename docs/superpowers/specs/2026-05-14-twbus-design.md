# twbus — Taiwan Bus Realtime Skill Plugin Design

- **Date**: 2026-05-14
- **Status**: Approved, pending implementation plan
- **Author**: brainstorm session (user + claude)
- **Reference plugin**: [echoulen/twparking](https://github.com/echoulen/twparking) — shape mirrored, runtime/install model adapted

## 1. Summary

`twbus` is a Claude Code skill plugin that exposes Taiwan public bus realtime data (Taipei / New Taipei / Keelung / Taichung) via slash commands. It wraps the [TDX V3 transport API](https://tdx.transportdata.tw/) with OAuth2 client_credentials. The implementation is a single Python entry script using only the standard library (no pip install needed at runtime); the user installs the plugin and provides TDX credentials via `~/.twbus/.env`.

The primary user need is **"how soon does the bus I'm waiting for arrive"** — narrowed to the four-tuple `(city, route, stop, direction)`. Favourites are saved at this granularity. A separate stop-centric query (`/bus-stop`) covers the "I'm at this stop, what's coming" case.

## 2. Scope & Non-Goals

**In scope**:
- 5 slash commands: `/bus-search`, `/bus-status`, `/bus-stop`, `/bus-add`, `/bus-list`
- Four cities: Taipei, NewTaipei, Keelung, Taichung
- Realtime ETA + plate number lookup
- Local favourites stored as 4-tuple refs
- Static route/stop catalog cached locally (7-day TTL)
- OAuth2 token cache, auto-refresh

**Out of scope**:
- High Speed Rail / TRA / MRT realtime (separate skills/MCPs exist)
- TUI / watch mode (twparking's `watch` doesn't apply — skills are single-shot)
- Nearby-stop by GPS (no lat/lon UX in skill mode)
- Cities beyond the four listed (Taoyuan/Tainan/Kaohsiung possible later)
- Remove-favourite command (manual edit of `~/.twbus/favourites.json` for v1; add later if needed)

## 3. Architecture

### 3.1 Repository layout

```
twbus/                                   # this repo
├── .claude-plugin/
│   └── plugin.json                      # name=twbus, skills=./skills/, commands=./commands/
├── commands/
│   ├── bus-search.md
│   ├── bus-status.md
│   ├── bus-stop.md
│   ├── bus-add.md
│   └── bus-list.md
├── skills/
│   └── twbus/
│       ├── SKILL.md                     # entry / dispatcher description
│       └── scripts/
│           ├── twbus.py                 # argparse dispatcher
│           ├── _tdx.py                  # OAuth2 + HTTP helpers
│           ├── _catalog.py              # StopOfRoute cache + ref normalize
│           ├── _favs.py                 # favourites I/O
│           └── _format.py               # JSON envelope helpers
├── tests/
│   ├── conftest.py
│   ├── fixtures/                        # recorded TDX JSON
│   ├── test_tdx.py
│   ├── test_catalog.py
│   ├── test_favs.py
│   └── test_cli.py
├── pyproject.toml                       # dev deps only (pytest, optional ruff)
├── README.md
└── LICENSE
```

### 3.2 Runtime

- **Python**: 3.10+ (uses `zoneinfo`, `match/case`, modern type hints; stdlib only at runtime)
- **Invocation**: every slash command runs
  ```bash
  python3 "$CLAUDE_PLUGIN_ROOT/skills/twbus/scripts/twbus.py" <subcommand> ... --json
  ```
- **`$CLAUDE_PLUGIN_ROOT`**: provided by Claude Code plugin runtime, points to the installed plugin root.

### 3.3 State directory

All state lives under `~/.twbus/`:

| Path | Content | Lifecycle |
|---|---|---|
| `~/.twbus/.env` | `TDX_CLIENT_ID=...` / `TDX_CLIENT_SECRET=...` | created `chmod 600` on first run if missing |
| `~/.twbus/token.json` | `{access_token, expires_at}` | refreshed when within 60s of expiry |
| `~/.twbus/catalog/<city>.json` | static route + stop catalog per city | 7-day TTL, lazy-loaded per query |
| `~/.twbus/favourites.json` | `[{ref, label?}, ...]` | manual edit OK; written by `/bus-add` |

**Credential load order**: process env var → `~/.twbus/.env`. Env var wins (useful for CI / temporary override).

### 3.4 Modules

| Module | Responsibility |
|---|---|
| `twbus.py` | argparse dispatcher; calls into helpers; prints JSON envelope or plain text |
| `_tdx.py` | OAuth2 token cache + refresh; `request(path, params)` returning parsed JSON; 401 retry-once; structured `TDXError` exceptions |
| `_catalog.py` | Load/refresh `StopOfRoute` per city; `normalize_ref(ref) → {city, route_id, route_name, direction, stop_id, stop_name, destination}`; fuzzy match via `difflib`; auto-refresh on `route_not_found` if cache > 1 day old |
| `_favs.py` | Read/write `favourites.json`; multi-match handling for partial refs in `add` |
| `_format.py` | `ok(data, warnings=...)` / `err(kind, message)` envelope builders; consistent ETA seconds → status string |

## 4. Slash Commands

All `.md` files use `allowed-tools: Bash` and instruct Claude to parse the JSON envelope and render a Chinese table.

### 4.1 `/bus-search`

- **Argument-hint**: `<關鍵字> [--city Taipei|NewTaipei|Keelung|Taichung] [--kind route|stop|all]`
- **CLI**: `twbus.py search <kw> [--city ...] [--kind ...] --json`
- **Default**: cross-city, `--kind=all`
- **Output `data`**: `[{kind: "route"|"stop", city, id, name, extra}]`
  - For `route`: `extra = {sub_routes: [{direction, destination}, ...]}`
  - For `stop`: `extra = {district?, routes_passing: ["235", "236", ...]}`
- **Truncation**: max 30 entries; envelope `warnings: [{kind: "truncated", total: N}]`

### 4.2 `/bus-status`

- **Argument-hint**: `<ref> [<ref> ...]`
- **CLI**: `twbus.py status <ref...> --json`
- **Ref form**: `<city>:<route>:<stop>:往<終點>` (e.g., `台北:235:公館:往台北車站`)
- **Output `data`**: `[{ref, normalized: {...}, etas: [{plate, seconds, status}], fetchError?}]`
  - `seconds < 60` → `status: "即將進站"`
  - `seconds null` → `status: "未發車或末班已過"`
  - `etas` carries whatever TDX returns for that ref (typically the next bus; sometimes the one after)
- **Batching**: refs grouped by city, one ETA API call per city using OData `$filter ... or ...`. If >20 refs in one city, batched into multiple calls.
- **Per-ref partial failure**: failed ref carries `fetchError`, other refs still return.

### 4.3 `/bus-stop`

- **Argument-hint**: `<city>:<stop> [--limit N]`
- **CLI**: `twbus.py stop <city>:<stop> [--limit 10] --json`
- **Single stop only** (not a list — use case is "I'm at one specific stop").
- **Output `data`**: `[{route, direction_label, destination, seconds, status, fetchError?}]`, sorted by `seconds` ascending, limit applies (default 10).

### 4.4 `/bus-add`

- **Argument-hint**: `<ref>` (full or partial: missing direction / missing route+direction)
- **CLI**: `twbus.py add <ref>` — plain text output, mirrors twparking. Exit code always 0; slash command parses by prefix.
- **Output prefixes** (one line each, candidates on following lines indented with `  `):
  - `added <ref>\t<label>` — added to favourites
  - `already in favourites: <ref>` — duplicate
  - `ambiguous direction for <ref>, please pick one:` + indented candidate lines (`  往台北車站` / `  往青年公園`) — missing direction
  - `multiple routes at <stop>, please pick one:` + indented candidate route lines — partial ref missing route
  - `route not found: <route>` + indented top-3 fuzzy suggestions — typo
  - `stop not on route: <stop>` + indented full stop list for that direction — wrong stop
  - `stop not found: <stop>` + indented top-3 fuzzy suggestions — typo
- Slash command treats `ambiguous`/`multiple`/`not found` lines as **selection prompts, not errors** — show candidates to user and ask them to retry with a precise ref.

### 4.5 `/bus-list`

- **Argument-hint**: (none)
- **CLI**: `twbus.py list` (plain text, tab-separated `<ref>\t<route> <stop> <direction_label>`)
- **Empty**: prints `no favourites` literal → slash command suggests `/bus-add`

## 5. Data Flow & TDX Integration

### 5.1 OAuth2 token

```
get_token():
  cached = read("~/.twbus/token.json")
  if cached and cached.expires_at - now() > 60s:
    return cached.access_token
  resp = POST https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token
         form-encoded: grant_type=client_credentials, client_id, client_secret
  write("~/.twbus/token.json", {access_token, expires_at: now() + expires_in - 60})
  return resp.access_token
```

- 401 on subsequent API call → force refresh once, retry; second 401 → `auth_invalid` error.
- Missing creds → `auth_missing` error with onboarding message.

### 5.2 Catalog cache

- **Source**: `Bus/StopOfRoute/City/{city}` — one endpoint returns routes with sub-routes, directions, stop sequence, departure/destination names.
- **Storage**: one file per city: `~/.twbus/catalog/<city>.json`.
- **Structure**:
  ```json
  {
    "fetched_at": "ISO8601",
    "routes": [
      {"route_id": "...", "route_name": "235",
       "sub_routes": [{"sub_route_id": "...", "direction": 0,
                       "departure": "青年公園", "destination": "台北車站",
                       "stops": [{"stop_id": "...", "stop_name": "公館", "seq": 5}, ...]}]}
    ],
    "stops_index": {                              // derived for /bus-stop and search
      "<stop_name>": [{"stop_id": "...", "routes": ["235", ...]}]
    }
  }
  ```
- **TTL**: 7 days. `--refresh` flag on any subcommand forces refetch.
- **Stale fallback**: if refetch fails and old cache exists → use old cache, add `warnings: [{kind: "stale_catalog", fetched_at: "..."}]`.

### 5.3 Ref normalization

Input ref `<city>:<route>:<stop>:往<終點>`:

1. Split by `:` (4 segments, last must start with `往`).
2. Map `<city>` (`台北`/`新北`/`基隆`/`台中`) → TDX city code (`Taipei`/`NewTaipei`/`Keelung`/`Taichung`).
3. Load catalog for that city (refresh if missing/expired).
4. Find `route_name` in `routes` — not found → `route_not_found` with `difflib.get_close_matches(cutoff=0.6)` suggestions.
5. Fuzzy-match `往XX` against `sub_routes[].destination` — match unique → `direction`; ambiguous/no-match → `ambiguous_direction` with `candidates = [往d for d in destinations]`.
6. In the matching sub-route's stop sequence, find `stop_name` — not found → `stop_not_on_route` with the full stop list for that direction.
7. Return normalized struct.

**Auto-refresh on miss**: if step 4 or 6 fails and catalog `fetched_at > 1 day ago`, refresh catalog once and retry. (New stops / route changes happen.)

### 5.4 Realtime ETA

- **Endpoint**: `Bus/EstimatedTimeOfArrival/City/{city}`
- **`status` filter** (multiple refs in one city):
  ```
  $filter=(RouteName/Zh_tw eq '235' and StopName/Zh_tw eq '公館' and Direction eq 0)
       or (RouteName/Zh_tw eq '236' and StopName/Zh_tw eq '景美' and Direction eq 1)
  ```
- **`stop` filter** (single stop, all routes):
  ```
  $filter=StopName/Zh_tw eq '公館'
  ```
- **Plate join**: separate call to `Bus/RealTimeNearStop/City/{city}` filtered by the same RouteName+Direction set, matched by `PlateNumb`. If plate isn't there (bus not yet near the stop), `plate: null`.
- **Rate limit (429)**: no auto-retry; surface `rate_limit` error.

## 6. Error Handling

### 6.1 Envelope

All `--json` invocations print one JSON document to stdout:

```json
// success
{ "ok": true, "data": <subcommand-specific>, "warnings": [] }

// failure
{ "ok": false, "error": { "kind": "<KindEnum>", "message": "...", "extra": {...} } }
```

**Exit code is always 0** unless the script crashes (unhandled exception). Slash commands branch on `ok`, not on shell exit.

Plain-text subcommands (`/bus-add`, `/bus-list`) follow the twparking convention: structured line prefixes the slash command parses (see §4.4 for the full `add` prefix list; `list` outputs one `<ref>\t<label>` per line, or the literal `no favourites`). The error kinds in §6.2 apply to JSON-envelope commands only (`search` / `status` / `stop`); the same logical conditions surface as prefix lines for plain-text commands.

### 6.2 Error kinds

| `kind` | Triggered by | UX |
|---|---|---|
| `auth_missing` | `.env` missing or empty | Print onboarding (申請 URL + sample `.env`), create empty `.env` chmod 600 |
| `auth_invalid` | 401 after refresh | `憑證錯誤，請檢查 ~/.twbus/.env` |
| `rate_limit` | 429 | `TDX rate limit，請稍後再試` |
| `route_not_found` | catalog lookup miss | Suggest top-3 fuzzy matches |
| `stop_not_on_route` | route OK, stop not in sub-route | List all stops on that direction |
| `ambiguous_direction` | direction string doesn't uniquely match | List both destinations |
| `no_etas` | API returns `[]` | `data: []` + `warnings: [{kind: "no_data", message: "可能末班過或路線停駛"}]` |
| `stale_catalog` | warning only — refresh failed, old cache used | Render with `（資料 X 天前）` annotation |
| `network` | DNS / timeout / non-200 not above | `網路錯誤：<message>` |

### 6.3 Slash command guidance for Claude

Each `commands/*.md` includes inline instructions:

- On `ok: false` with `route_not_found` / `stop_not_on_route` / `ambiguous_direction` → present candidates, **don't guess** the user's intent.
- On `auth_missing` → relay onboarding message verbatim, don't try to set env vars.
- On `stale_catalog` warning → render normally but annotate freshness.
- Plain-text `add` / `list` → parse known prefixes (see §4.4); treat `ambiguous direction for` / `multiple routes at` / `route not found` / `stop not on route` / `stop not found` as **selection prompts, not errors** — list candidates and ask the user to retry with a precise ref.

## 7. Testing

### 7.1 Unit tests (mocked, no network)

- Framework: `pytest` (dev dep via `pyproject.toml`).
- Strategy: `unittest.mock.patch('urllib.request.urlopen')` returning fixture JSON.
- Fixtures recorded once via `scripts/_dev_record.py` against live TDX, stored in `tests/fixtures/`.

Test modules:

| File | Covers |
|---|---|
| `test_tdx.py` | Token cache hit/miss, refresh on expiry, 401 retry-once, `auth_missing`/`auth_invalid` |
| `test_catalog.py` | `normalize_ref` happy + all error kinds, fuzzy matching cutoffs, auto-refresh on miss |
| `test_favs.py` | `.env` parsing, favourites add/list/dedupe, multi-match returns candidates |
| `test_cli.py` | argparse parsing, JSON envelope shape per subcommand, plain-text `add`/`list` output |

### 7.2 Integration tests (opt-in)

`tests/integration/test_live.py` marked `@pytest.mark.integration`; only runs when `TDX_CLIENT_ID` env is set. Local dev sanity check; not in CI.

### 7.3 CI

GitHub Actions matrix `python-version: ['3.10', '3.11', '3.12']`, runs `pytest -m "not integration"` + optional `ruff check`.

## 8. Open Questions / Future Work

- **Remove favourite**: deferred — manual `~/.twbus/favourites.json` edit OK for v1.
- **More cities**: Taoyuan/Tainan/Kaohsiung have TDX coverage; add by extending city enum + catalog tests.
- **Catalog `refresh` flag UX**: `--refresh` on every subcommand is implicit; consider adding `/bus-refresh` slash command if users hit stale-catalog frequently.
- **Token cache concurrency**: two concurrent CLI invocations could both refresh the token; benign (TDX accepts overlapping tokens), no lock needed.

## 9. Glossary

| Term | Meaning |
|---|---|
| TDX | [Transport Data eXchange](https://tdx.transportdata.tw/) — Taiwan MOTC's open transport data platform |
| Route | A bus line, identified by `RouteName/Zh_tw` (e.g., `235`) |
| SubRoute | A directional variant of a route, with its own destination |
| Direction | TDX `Direction` field: `0` = 去程, `1` = 回程 |
| Stop | A bus stop along a sub-route, identified by `StopName/Zh_tw` + per-city `StopID` |
| Ref | This skill's user-facing identifier: `<city>:<route>:<stop>:往<終點>` |
| ETA | Estimated Time of Arrival, in seconds from `EstimatedTimeOfArrival` endpoint |
