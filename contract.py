"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    FIND_CONCERTS = "find_concerts"
    ARTIST_SHOWS = "artist_shows"
    PIN_CONCERTS = "pin_concerts"


class Task(Enum):
    FIND_CONCERTS = "find-concerts"
    ARTIST_SHOWS = "artist-shows"


LISTENERS = "The artist's Last.fm listener count (all-time unique listeners, Last.fm's popularity figure)"


@dataclass
class Window(Output):
    start: Annotated[str, "The first Houston local date the snapshot covers, YYYY-MM-DD"]
    end: Annotated[str, "The last Houston local date the snapshot covers, YYYY-MM-DD (30 days after start)"]


@dataclass
class ConcertRow(Output):
    artist: Annotated[str, "The headliner, as SeatGeek names them"]
    listeners: Annotated[int, LISTENERS]
    date: Annotated[str, "The date of the artist's first show in the range, YYYY-MM-DD"]
    venue: Annotated[str, "The venue of that show"]


@dataclass
class FindInput(Output):
    start_date: Annotated[
        str, "The first day to search, a Houston local date YYYY-MM-DD inside the snapshot's window, e.g. 2026-11-07"
    ]
    end_date: Annotated[
        str,
        "The last day to search, YYYY-MM-DD, on or after start_date and inside the window (the same day for one day)",
    ]


@dataclass
class FindOutput(Output):
    start_date: Annotated[str, "The first day searched, exactly as given"]
    end_date: Annotated[str, "The last day searched, exactly as given"]
    window: Annotated[Window, "The dates the snapshot covers"]
    total_artists: Annotated[int, "How many artists headline a Houston show in the range, before the cut to 20"]
    concerts: Annotated[
        list[ConcertRow],
        "One row per artist, the top 20 by Last.fm listeners (most first, ties alphabetically by artist), each with "
        "their first show in the range; [] when no show falls in the range",
    ]


@dataclass
class ArtistInput(Output):
    artist: Annotated[str, "An artist's name, e.g. Khruangbin (case does not matter)"]


@dataclass
class Show(Output):
    artist: Annotated[str, "The headliner"]
    date: Annotated[str, "Houston local date, YYYY-MM-DD"]
    time: Annotated[str, 'Houston local start time HH:MM, or "" when not announced']
    venue: Annotated[str, "The venue"]
    event_id: Annotated[str, "SeatGeek's event id"]


@dataclass
class ArtistOutput(Output):
    artist: Annotated[str, "The artist as SeatGeek names them, or the query as given when not found"]
    found: Annotated[bool, "Whether the artist headlines a show in the window"]
    listeners: Annotated[int, "The artist's Last.fm listener count (all-time unique listeners); 0 when not found"]
    window: Annotated[Window, "The dates the shows come from"]
    shows: Annotated[list[Show], "Every show the artist headlines in the window, earliest first; [] when not found"]


@dataclass
class ArtistListeners(Output):
    artist: str
    listeners: Annotated[int, LISTENERS]


@dataclass
class PinOutput(Output):
    start_date: Annotated[str, "The first day searched, exactly as given"]
    end_date: Annotated[str, "The last day searched, exactly as given"]
    window: Window
    shows: Annotated[list[Show], "Every show in the window, whatever its date, in no particular order"]
    listeners: Annotated[list[ArtistListeners], "Every headliner's listener count"]


TOOLS = {
    Tool.FIND_CONCERTS: (FindInput, FindOutput),
    Tool.ARTIST_SHOWS: (ArtistInput, ArtistOutput),
    Tool.PIN_CONCERTS: (FindInput, PinOutput),
}
TASKS = {
    Task.FIND_CONCERTS: (FindInput, FindOutput),
    Task.ARTIST_SHOWS: (ArtistInput, ArtistOutput),
}
