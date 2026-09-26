# --------------------- # Imports # ---------------------------------- #

import ipaddress
import os
import select
import subprocess
import time


# --------------------- # Hop Parsing - IP Address and Latency # ---------------------------------- #

def parse_hop(line):
    parts = line.split()
    if not parts or not parts[0].isdigit():
        return None
    address = None
    hostname = None
    latencies = []
    #--------# IP Address and Hostname Extraction #------#
    for part in parts[1:]:
        try:
            address = str(ipaddress.ip_address(part.strip("()")))
            break
        except ValueError:
            continue
    if len(parts) > 2 and parts[1] != "*" and not parts[1].startswith("("):
        try:
            ipaddress.ip_address(parts[1])
        except ValueError:
            hostname = parts[1]
    #--------# Average Latency Calculation #------#
    for index, part in enumerate(parts[:-1]):
        if parts[index + 1] == "ms":
            try:
                latencies.append(float(part))
            except ValueError:
                pass
    return {"number": int(parts[0]), "IP": address, "hostname": hostname,
            "AvgLatency": round(sum(latencies) / len(latencies), 2) if latencies else None}


# --------------------- # Traceroute Process and Safeguards # ---------------------------------- #

def run_traceroute(target, outcome=None):
    # outcome stores the reason the trace ended while yield sends each hop to the caller.
    if outcome is None:
        outcome = {}
    outcome.update(status="incomplete", message="Probing ended without confirming arrival at the destination.")
    process = subprocess.Popen(
        ["traceroute", "-n", "-m", "20", "-w", "2", target],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    #--------# Timeout and Missing-Hop Safeguards #------#
    deadline = time.monotonic() + 30
    consecutive_no_response = 0
    pending = b""
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                outcome.update(status="timeout", message="Trace timed out after 30 seconds. Partial hops are preserved.")
                return
            # Read only available bytes: readline() can block on a partial hop line.
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                if process.wait(timeout=1) != 0:
                    outcome.update(status="error", message="Traceroute failed. Check the destination and network permissions.")
                return
            pending += chunk
            while b"\n" in pending:
                if time.monotonic() >= deadline:
                    outcome.update(status="timeout", message="Trace timed out after 30 seconds. Partial hops are preserved.")
                    return
                raw, pending = pending.split(b"\n", 1)
                hop = parse_hop(raw.decode("utf-8", errors="replace"))
                if hop is None:
                    continue
                consecutive_no_response = consecutive_no_response + 1 if hop["IP"] is None else 0
                #--------# Trace Completion Status #------#
                if hop["IP"] == target:
                    outcome.update(status="success", message="Destination reached successfully.")
                elif consecutive_no_response >= 4:
                    outcome.update(status="unresponsive", message="Stopped after 4 consecutive unresponsive hops. The destination may still be reachable.")
                elif hop["number"] >= 20:
                    outcome.update(status="hop_limit", message="Stopped at the 20-hop limit without reaching the destination.")
                yield hop
                if outcome["status"] != "incomplete":
                    return
    #--------# Process Cleanup #------#
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        process.stdout.close()
