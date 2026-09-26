# --------------------- # Imports # ---------------------------------- #

import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

# --------------------- # Overall Trace Timeout # ---------------------------------- #

TRACE_TIMEOUT = 40


# --------------------- # Start Trace Worker and Stream Its Results # ---------------------------------- #

def stream_trace(target, timeout=TRACE_TIMEOUT):
    # Run the trace separately so a stuck network lookup cannot block Flask indefinitely.
    worker = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("trace_worker.py")), target],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    deadline = time.monotonic() + timeout
    pending = b""
    #--------# Read Live Results Until Completion or Timeout #------#
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield "complete", {"status": "timeout", "message": f"Trace timed out after {timeout:g} seconds, including DNS and enrichment. Partial hops are preserved."}
                return
            if not select.select([worker.stdout], [], [], min(remaining, 1))[0]:
                yield "heartbeat", {}
                continue
            chunk = os.read(worker.stdout.fileno(), 65536)
            if not chunk:
                yield "complete", {"status": "error", "message": "The trace worker stopped unexpectedly. Partial hops are preserved."}
                return
            pending += chunk
            while b"\n" in pending:
                raw, pending = pending.split(b"\n", 1)
                message = json.loads(raw)
                yield message["event"], message["data"]
                if message["event"] == "complete":
                    return
    #--------# Stop the Worker and Its Child Processes #------#
    finally:
        # The worker, traceroute and enrichment share a group; clean up all of them
        # on completion, timeout, or browser disconnect (generator.close()).
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        worker.wait()
        worker.stdout.close()
