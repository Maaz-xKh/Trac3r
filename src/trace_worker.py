# --------------------- # Imports # ---------------------------------- #

import ipaddress
import json
from pathlib import Path
import socket
import subprocess
import sys

from traceroute import run_traceroute

# --------------------- # Enrichment Timeout and Location Fields # ---------------------------------- #

ENRICHMENT_TIMEOUT = 4
LOCATION_FIELDS = ("asn", "organization", "city", "region", "country", "latitude", "longitude")


# --------------------- # Hop Enrichment with a Time Limit # ---------------------------------- #

def bounded_enrichment(hop):
    for field in LOCATION_FIELDS:
        hop[field] = None
    if not hop["IP"]:
        return hop
    address = ipaddress.ip_address(hop["IP"])
    if not address.is_global:
        hop.update(asn="Private" if address.is_private else "Special",
                   organization="Private Network" if address.is_private else "Non-public network")
        return hop
    # A separate process lets us stop the entire lookup after 4 seconds, including DNS and retries.
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--enrich"],
            input=json.dumps(hop), text=True, capture_output=True,
            timeout=ENRICHMENT_TIMEOUT, check=True,
        )
        hop.update(json.loads(result.stdout))
    except subprocess.TimeoutExpired:
        hop["enrichment_status"] = "timeout"
    except (subprocess.SubprocessError, ValueError):
        hop["enrichment_status"] = "unavailable"
    return hop


# --------------------- # Send Results to the Trace Service # ---------------------------------- #

def emit(event, data):
    print(json.dumps({"event": event, "data": data}), flush=True)


# --------------------- # Resolve Destination and Process Live Hops # ---------------------------------- #

def trace_target(target):
    try:
        destination = socket.gethostbyname(target)
    except OSError:
        emit("complete", {"status": "error", "message": "Could not resolve the destination's IPv4 address.", "hops": 0})
        return
    #--------# Live Hop Processing #------#
    emit("started", {"destination": destination})
    outcome = {}
    count = 0
    hops = run_traceroute(destination, outcome)
    try:
        for hop in hops:
            count += 1
            # Show the hop immediately; enrichment updates it without delaying discovery in the UI.
            emit("hop", dict(hop))
            emit("hop-update", bounded_enrichment(hop))
        emit("complete", {**outcome, "hops": count, "destination": destination})
    finally:
        hops.close()


# --------------------- # Run Trace or Individual Enrichment Lookup # ---------------------------------- #

if __name__ == "__main__":
    if sys.argv[1] == "--enrich":
        from enrichment import enrich_hop
        print(json.dumps(enrich_hop(json.load(sys.stdin))))
    else:
        try:
            trace_target(sys.argv[1])
        except Exception:
            emit("complete", {"status": "error", "message": "Trace failed. Check the destination and network connection."})
