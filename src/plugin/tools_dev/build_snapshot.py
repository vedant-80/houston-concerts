"""Build the frozen concert snapshot, src/plugin/data/concerts.json.gz, from SeatGeek and Last.fm.

Dev-only: the plugin itself never touches the network. Run from the plugin root, with both keys
set in your own shell (never commit them):

    export SEATGEEK_CLIENT_ID=...     # seatgeek.com/account/develop, free
    export LASTFM_API_KEY=...         # last.fm/api/account/create, free
    uv run python src/plugin/tools_dev/build_snapshot.py            # window starts today in Houston
    uv run python src/plugin/tools_dev/build_snapshot.py 2026-11-02 # or on a given date

The window is WINDOW_DAYS days of Houston local dates starting on the given date, both ends
included. For it, the build:

1. asks SeatGeek's Platform API (/2/events) for concerts (taxonomy "concert") at venues in
   Houston, TX, a page at a time;
2. keeps an event only when its date is announced, its local date falls inside the window, its
   venue is in Houston, it names a performer (the one SeatGeek marks primary, else the first, is
   its headliner) and it is not cancelled or postponed. Everything else is counted in SOURCE.json
   by why it was dropped. (Prices are not kept: SeatGeek's free API gives none, nor does
   Ticketmaster's for most events);
3. asks Last.fm for each headliner's listener count (artist.getInfo, the exact name, no
   autocorrect); a headliner Last.fm does not know is dropped with its events, and counted.

Every request failure stops the build, and so does a snapshot with no shows: no retries past the
API's own rate-limit answer, no partial or empty snapshot.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parents[1] / "data"
SNAPSHOT = DATA / "concerts.json.gz"
SOURCE = DATA / "SOURCE.json"
HOUSTON = ZoneInfo("America/Chicago")
WINDOW_DAYS = 30  # the window is start ... start + 30 days, inclusive
SEATGEEK = "https://api.seatgeek.com/2/events"
LASTFM = "https://ws.audioscrobbler.com/2.0/"
PER_PAGE = 200
DROP_STATUS = {"cancelled", "canceled", "postponed"}


def key(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set: export it in your shell first (see this file's docstring)")
    return value


def get_json(url: str, params: dict[str, str], *, pause: float) -> dict:
    """GET ``url`` with ``params``; one retry after the wait a 429 asks for, then fail."""
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "houston-concerts-build"}
    )
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                time.sleep(pause)
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt == 1:
                time.sleep(int(error.headers.get("Retry-After", "5")))
                continue
            raise SystemExit(f"{url} answered HTTP {error.code}: {error.read()[:300]!r}") from None
    raise AssertionError("unreachable")


def fetch_events(client_id: str, first: date, last: date) -> list[dict]:
    """Every Houston concert SeatGeek lists from ``first`` to ``last`` (local dates, inclusive)."""
    events, page = [], 1
    while True:
        params = {
            "client_id": client_id,
            "venue.city": "Houston",
            "venue.state": "TX",
            "taxonomies.name": "concert",
            "datetime_local.gte": f"{first.isoformat()}T00:00:00",
            "datetime_local.lte": f"{last.isoformat()}T23:59:59",
            "per_page": str(PER_PAGE),
            "page": str(page),
            "sort": "datetime_local.asc",
        }
        body = get_json(SEATGEEK, params, pause=0.5)
        if "events" not in body or "meta" not in body:
            raise SystemExit(f"SeatGeek answered without events or meta: {str(body)[:300]}")
        events += body["events"]
        # SeatGeek may cap per_page below what was asked: page by what it answered.
        if not body["events"] or len(events) >= body["meta"].get("total", 0):
            return events
        page += 1


def headliner(event: dict) -> str | None:
    performers = [p for p in event.get("performers") or [] if (p.get("name") or "").strip()]
    if not performers:
        return None
    primary = [p for p in performers if p.get("primary")]
    return (primary or performers)[0]["name"].strip()


def listeners_of(api_key: str, artist: str) -> int | None:
    params = {"method": "artist.getinfo", "artist": artist, "autocorrect": "0", "api_key": api_key, "format": "json"}
    body = get_json(LASTFM, params, pause=0.25)
    if "error" in body:
        if body["error"] == 6:  # "The artist you supplied could not be found"
            return None
        raise SystemExit(f"Last.fm error {body['error']} for {artist!r}: {body.get('message')}")
    return int(body["artist"]["stats"]["listeners"])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(first: date) -> None:
    seatgeek, lastfm = key("SEATGEEK_CLIENT_ID"), key("LASTFM_API_KEY")
    last = first + timedelta(days=WINDOW_DAYS)
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = fetch_events(seatgeek, first, last)
    counts: Counter[str] = Counter({"events fetched": len(raw)})
    shows, seen = [], set()
    for event in raw:
        event_id = str(event["id"])
        if event_id in seen:
            counts["dropped: listed twice"] += 1
            continue
        seen.add(event_id)
        local = (event.get("datetime_local") or "")[:10]
        venue = event.get("venue") or {}
        status = str(event.get("status") or "").lower()
        artist = headliner(event)
        if event.get("date_tbd") or not local:
            counts["dropped: date to be announced"] += 1
        elif not first.isoformat() <= local <= last.isoformat():
            counts["dropped: local date outside the window"] += 1
        elif (venue.get("city") or "").strip().lower() != "houston":
            counts[f"dropped: venue in {venue.get('city') or 'no city'}"] += 1
        elif status in DROP_STATUS:
            counts[f"dropped: status {status}"] += 1
        elif artist is None:
            counts["dropped: no performer (headliner)"] += 1
        else:
            shows.append(
                {
                    "event_id": event_id,
                    "artist": artist,
                    "date": local,
                    "time": "" if event.get("time_tbd") else event["datetime_local"][11:16],
                    "venue": (venue.get("name") or "Venue to be announced").strip(),
                }
            )
    listeners, unknown = {}, set()
    for artist in sorted({show["artist"] for show in shows}):
        count = listeners_of(lastfm, artist)
        if count is None:
            unknown.add(artist)
        else:
            listeners[artist] = count
    counts["dropped: headliner not on Last.fm"] = sum(1 for show in shows if show["artist"] in unknown)
    shows = sorted(
        (show for show in shows if show["artist"] in listeners),
        key=lambda show: (show["date"], show["time"], show["event_id"]),
    )
    counts["kept: shows"] = len(shows)
    counts["kept: artists"] = len(listeners)
    print(json.dumps(dict(counts), indent=2))
    if not shows:
        raise SystemExit("no show survived the filters: refusing to write an empty snapshot (see the counts above)")
    snapshot = {
        "window": {"start": first.isoformat(), "end": last.isoformat()},
        "fetched_at": fetched_at,
        "shows": shows,
        "listeners": dict(sorted(listeners.items())),
    }
    SNAPSHOT.write_bytes(gzip.compress(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
    source = {
        "fetched_at": fetched_at,
        "window": snapshot["window"],
        "seatgeek": {
            "url": SEATGEEK,
            "venue.city": "Houston",
            "venue.state": "TX",
            "taxonomies.name": "concert",
            "status dropped": sorted(DROP_STATUS),
        },
        "lastfm": {"url": LASTFM, "method": "artist.getinfo", "autocorrect": 0, "figure": "artist.stats.listeners"},
        "counts": dict(counts),
        "unknown_on_lastfm": sorted(unknown),
        "outputs": {SNAPSHOT.name: sha256(SNAPSHOT)},
    }
    SOURCE.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(
        f"snapshot: {SNAPSHOT.stat().st_size / 1e3:.1f} KB, {len(shows)} shows by {len(listeners)} artists, window {first} to {last}"
    )


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("usage: build_snapshot.py [first date YYYY-MM-DD, default today in Houston]")
    main(date.fromisoformat(sys.argv[1]) if len(sys.argv) == 2 else datetime.now(HOUSTON).date())
