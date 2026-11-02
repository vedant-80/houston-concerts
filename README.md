# Houston Concerts

A `nanoagent.plugin/v0001` plugin. Give it a range of dates in the coming month (one night, a
weekend, the whole month) and its agent lists the artists headlining a Houston concert then, each
with the date and venue of their first show in that range, ranked by how many listeners the artist
has on Last.fm (most first). It shows the top 20 and says how many artists play in all.

Shows come from SeatGeek and listener counts from Last.fm, fetched once and frozen in the plugin
(`src/plugin/data/`), so every answer is exact and every run can be reproduced offline, with no API
keys. "The coming month" is the snapshot's 30-day window, which `SOURCE.json` and every answer name.

## Tools

| Tool | Does | Code |
|---|---|---|
| `find_concerts` | For a start and end date inside the window (both included): every artist headlining a show then. One row per artist: listeners, and the date and venue of their first show in the range (by date, then start time, an unannounced time last). Ranked by listeners, most first, ties alphabetically by artist; top 20, plus how many play in all. A date that is not a calendar date, a start after the end, or a range outside the window is refused, naming the window | `src/plugin/tools.py`, `src/plugin/snapshot.py` |
| `artist_shows` | Every show one artist headlines in the window (name matched ignoring case), earliest first, with time and venue | `src/plugin/tools.py` |
| `pin_concerts` | The answer key: every show in the window and every headliner's listeners, whatever the range | `src/plugin/tools.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `find-concerts` | Lists up to 20 artists headlining a Houston show between two dates, most-listened-to first | `agent`, with `find_concerts`; reference `pin_concerts` |
| `artist-shows` | Shows one artist's Houston dates, times and venues | `tool` (`artist_shows`) |

The `find-concerts` agent makes two tool calls: `find_concerts` with the dates, then `submit` with
its result unchanged. The tool filters, groups and ranks, because the hosted model's reply is capped
at 2,048 tokens; the agent's job is to pass the dates exactly and copy the answer exactly.

## Ground truth

Before the agent starts, NanoAgent runs `pin_concerts` and pins every show in the snapshot. The
verifier never trusts a ranking: it keeps the shows inside the task's dates, takes each artist's
first one, ranks the artists by listeners itself and compares the answer with its top 20. It
re-implements these rules (`verifier/rules.py`, with its own calendar check, since a verifier may
not import `datetime`) and imports none of the plugin's code.

`src/plugin/tools_dev/build_snapshot.py` builds the snapshot (it is dev-only; the plugin never
touches the network):

1. **SeatGeek Platform API** (`/2/events`): concerts at venues in Houston, TX across a 30-day
   window of Houston local dates, page by page. A show is kept when its date is announced and in the
   window, its venue is in Houston, it is not cancelled or postponed and it names a performer (the
   one SeatGeek marks primary, else the first, is its headliner).
2. **Last.fm** `artist.getInfo` with the headliner's exact name (no autocorrect): `stats.listeners`.
3. Every show and artist dropped, and why, is counted in `src/plugin/data/SOURCE.json`, with the
   window, the request parameters and the snapshot's sha256. Any request failure stops the build,
   and so does a snapshot with no shows; it never writes a partial or empty snapshot.

## Checks

`verify_task` for `find-concerts` returns every check below in order with its expected and actual
values (the page shows them under the answer). The verdict is valid only when all hold. A failure
of `answer-key`, `range` or `window` scores 0; otherwise the score is the share of ranks exactly
right out of the longer of the expected and submitted lists.

| Check | Holds when |
|---|---|
| `answer-key` | The pinned key is for these dates, which lie inside its window; its shows are inside the window, listed once, and by artists with listener counts |
| `range` | The answer's `start_date` and `end_date` are the task's |
| `window` | The answer names the snapshot's window |
| `well-formed` | Every row has an artist, listeners ≥ 0 and a calendar date; each artist once; at most 20 rows |
| `count` | min(20, artists playing in the range) rows |
| `order` | Listeners descending, ties by artist name (skipped when the list is malformed) |
| `rows-exact` | At each rank: artist, listeners, and the date and venue of their first show in the range are the expected ones; the message names each wrong rank |
| `no-extra` | No artist outside the expected top 20 is listed |
| `none-missing` | Every artist in the expected top 20 is listed |
| `in-range` | Every listed date falls between the start and end dates |
| `total` | `total_artists` counts every artist playing in the range |

Each tool call is checked too: dates that are not calendar dates (`2026-02-30`, `11/02/2026`) or a
start after the end are refused; `find_concerts` must list min(20, total) rows inside the range,
ranked; `artist_shows` must list one artist's shows once each, earliest first.

## Limitations

- **No ticket prices.** The task first asked for the cheapest ticket within a budget, but neither
  free API gives prices: Ticketmaster's Discovery API priced 9 of 150 Houston concerts and SeatGeek's
  none of 100. Both keep prices for paid partners, so the task filters by date instead.
- **Last.fm listeners are not Spotify monthly listeners.** Spotify's API offers no monthly
  listener figure, and scraping it breaks Spotify's terms. Last.fm's figure counts all-time unique
  listeners among Last.fm users, so it favors artists popular for longer.
- **SeatGeek's listings only.** Shows SeatGeek does not list are missing.
- **A frozen month.** The window is the 30 days after the snapshot date; rebuild to refresh it. The
  agent is not told today's date, so "this weekend" must be turned into dates before the task runs.
- **Headliners only.** Each show counts for its primary performer; openers are not listed.
- **Exact names.** A headliner whose SeatGeek name Last.fm does not know is dropped (listed in
  `SOURCE.json` under `unknown_on_lastfm`).
- **Data terms.** SeatGeek's and Last.fm's terms limit storing and redistributing their data.
  This snapshot is a small sample for coursework; both sources are credited here.

Data: SeatGeek Platform API; Last.fm API.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (no network), tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server (__main__.py), the tools (tools.py), the snapshot and ranking
│                    #   (snapshot.py), data/ (the snapshot and SOURCE.json) and
│                    #   tools_dev/build_snapshot.py, which rebuilds the snapshot
├── tests/           # offline tests: a hand-made mini snapshot for edge cases, and end-to-end
│                    #   cases on the real snapshot
├── ui/              # how the page draws the outputs and the verdict's checks
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: one module per tool, the task's checks in task.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest -v          # offline; no model, no network, no keys
uv run ruff check .
```

The tests replay each task the way NanoAgent runs it, with a script in place of the model:
`pin_concerts` first, then `find_concerts`, each call checked by `verify_input` and
`verify_output`, then `verify_task` on the submitted answer (run twice, to show the verdict is
deterministic). `tests/test_verifier.py` covers correct, incorrect, missing, malformed and boundary
answers on a hand-made snapshot whose answers are worked out by hand; `tests/test_cases.py` runs
real date ranges on the real snapshot.

Rebuild the snapshot (needs a free SeatGeek client id from seatgeek.com/account/develop and a free Last.fm key from last.fm/api; set them in
your own shell, never in a file in this repository):

```bash
export SEATGEEK_CLIENT_ID=...
export LASTFM_API_KEY=...
uv run python src/plugin/tools_dev/build_snapshot.py             # window starts today in Houston
uv run python src/plugin/tools_dev/build_snapshot.py 2026-11-02  # or on a given date
```

Publishing checks every plugin rule: push the plugin to a public GitHub repository and submit it to
the RUSH Lab marketplace.
