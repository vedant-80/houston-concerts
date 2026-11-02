// How this plugin's page draws its tasks' outputs: the find-concerts answer (a FindOutput) as a ranked
// table of artists with their first show in the dates asked, and one artist's shows (an ArtistOutput). A
// find-concerts result ends with the verdict's checks.
import { dataTable, disclosure, h, statusPill } from "./kit/components.js";

const DAY = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
const day = (text) => DAY.format(new Date(`${text}T00:00:00Z`));
const people = new Intl.NumberFormat();

/** The verdict's named checks, each with whether it held and, if not, why. */
function checks(verdict) {
  const entries = verdict?.details?.checks;
  if (!Array.isArray(entries)) return null;
  const failed = entries.filter((entry) => entry.ok === false).length;
  return disclosure(
    { summary: failed ? `${failed} of ${entries.length} checks fail` : `All ${entries.length} checks hold` },
    h(
      "ul",
      { class: "checks" },
      entries.map((entry) =>
        h(
          "li",
          {},
          statusPill(entry.ok === true ? "Holds" : entry.ok === false ? "Fails" : "Skipped", entry.ok === true ? "ok" : entry.ok === false ? "bad" : "neutral"),
          " ",
          entry.constraint,
          entry.message ? h("div", { class: "muted", text: entry.message }) : null,
        ),
      ),
    ),
  );
}

function findOutput(answer, { verdict }) {
  const range = answer.start_date === answer.end_date ? day(answer.start_date) : `${day(answer.start_date)} to ${day(answer.end_date)}`;
  const heading = `${answer.total_artists} artist(s) playing Houston, ${range}`;
  const rows = answer.concerts.map((row, index) => ({ rank: index + 1, ...row }));
  const table = dataTable({
    caption: heading,
    columns: [
      { key: "rank", label: "#", numeric: true },
      { key: "artist", label: "Artist", primary: true },
      { key: "listeners", label: "Last.fm listeners", numeric: true, render: (row) => people.format(row.listeners) },
      { key: "date", label: "Date", render: (row) => day(row.date) },
      { key: "venue", label: "Venue" },
    ],
    rows,
    sort: { key: "rank", dir: "asc" },
    empty: "No concert falls on these dates.",
  });
  return h("div", { class: "concerts" }, h("h3", { text: heading }), table.element, checks(verdict));
}

function artistOutput(answer) {
  if (!answer.found) return h("p", { text: `${answer.artist} has no Houston show between ${day(answer.window.start)} and ${day(answer.window.end)}.` });
  return h(
    "div",
    { class: "concerts" },
    h("h3", { text: `${answer.artist} · ${people.format(answer.listeners)} Last.fm listeners` }),
    h("ul", { class: "shows" }, answer.shows.map((show) => h("li", {}, h("strong", { text: day(show.date) }), ` ${show.time || "time TBA"} · ${show.venue}`))),
  );
}

export default { FindOutput: findOutput, ArtistOutput: artistOutput };
