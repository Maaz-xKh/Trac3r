# Trac3r
A visual traceroute and network path analysis tool that maps hops, IP ownership, and routing paths across the internet.

## Running the Web Interface

On macOS, install `flask`, `ipwhois`, and `requests`, then run:

```sh
python3 src/app.py
```

Open `http://localhost:5000` and enter a website or IPv4 address. The trace starts from the computer running Flask.

## Project Files

| File | Purpose |
|---|---|
| `src/app.py` | Validates the destination, serves the webpage, and sends live results to the browser using SSE. |
| `src/traceroute.py` | Runs macOS traceroute, parses each hop, and records why probing stopped. |
| `src/enrichment.py` | Looks up the network owner, ASN, and approximate location of an IP address. |
| `src/trace_service.py` | Supervises the trace and stops its processes if the overall deadline is reached or the browser disconnects. |
| `src/trace_worker.py` | Resolves the destination, runs the trace, and gives each enrichment lookup a time limit. |
| `src/templates/index.html` | Defines the map, destination input, and hop sidebar. |
| `src/static/style.css` | Styles the interface. |
| `src/static/script.js` | Receives live hops, updates the sidebar, and draws the animated route. |
| `src/main.py`, `src/visualization.py` | Original terminal interface and Folium map generation. |

The web flow is `app.py → trace_service.py → trace_worker.py → traceroute.py / enrichment.py`.
The service and worker run separately so Flask can stop a stalled lookup instead of waiting indefinitely.

## Trace Safeguards

- Maximum 20 hops, 2-second probe wait, and a cutoff after four consecutive unresponsive hops.
- 30-second probing deadline, 4 seconds per enrichment lookup, and 40 seconds overall for the web trace.
- A 45-second browser fallback restores the controls if no completion message arrives.
- Completion distinguishes destination reached, timeout, unresponsive cutoff, hop limit, incomplete, and error.

Select a hop to see its details, including possible reasons for a missing response. Nearby markers spread apart for readability without changing their real coordinates. Zoom stops at city/region scale. Lines show hop order, not physical cables; their animation does not represent packet speed.

The original terminal interface also needs `folium`. Generated maps, local tests, and test reports are excluded from new Git additions by `.gitignore`; files already tracked by Git must be untracked separately.
