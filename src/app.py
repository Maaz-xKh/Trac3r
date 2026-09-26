# --------------------- # Imports # ---------------------------------- #

import ipaddress
import json
import re
from urllib.parse import urlsplit

from flask import Flask, Response, render_template, request

from trace_service import stream_trace

app = Flask(__name__)


# --------------------- # User Input and Target Validation # ---------------------------------- #

def clean_target(value):
    value = value.strip()
    if not value or any(character.isspace() for character in value):
        raise ValueError("Enter a website or IPv4 address without spaces.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        address = None
    if address is not None:
        if address.version != 4:
            raise ValueError("This traceroute currently supports IPv4 destinations only.")
        return str(address)

    parsed = urlsplit(value if "://" in value else "//" + value)
    if parsed.scheme not in ("", "http", "https") or parsed.username or parsed.password:
        raise ValueError("Use a hostname, IPv4 address, or HTTP(S) website URL.")
    hostname = parsed.hostname
    # Accessing port also validates malformed port numbers in pasted URLs.
    parsed.port
    if not hostname or ":" in hostname:
        raise ValueError("Enter a valid hostname or IPv4 address.")
    hostname = hostname.encode("idna").decode("ascii").rstrip(".").lower()
    labels = hostname.split(".")
    if (len(hostname) > 253 or not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    )):
        raise ValueError("Enter a valid hostname or IPv4 address.")
    if re.fullmatch(r"[0-9.]+", hostname):
        try:
            ipaddress.IPv4Address(hostname)
        except ValueError:
            raise ValueError("Enter a valid IPv4 address.") from None
    return hostname


# --------------------- # SSE Message Formatting # ---------------------------------- #

def sse_event(data, name=None):
    prefix = f"event: {name}\n" if name else ""
    return f"{prefix}data: {json.dumps(data)}\n\n"


# --------------------- # Home Page # ---------------------------------- #

@app.route("/")
def home():
    return render_template("index.html")


# --------------------- # Live Trace Streaming # ---------------------------------- #

@app.route("/trace")
def trace():
    # Send validation failures through SSE so EventSource can show useful errors.
    try:
        target = clean_target(request.args.get("target", ""))
        validation_error = None
    except (ValueError, UnicodeError) as error:
        target = None
        validation_error = str(error)

    def generate():
        if validation_error:
            yield sse_event({"message": validation_error}, "trace-error")
            return
        try:
            events = stream_trace(target)
            try:
                for name, data in events:
                    yield sse_event(data, None if name == "hop" else name)
            finally:
                if hasattr(events, "close"):
                    events.close()
        except Exception:
            app.logger.exception("Trace failed")
            yield sse_event({"message": "The trace failed. Check your connection and try again."}, "trace-error")

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


# --------------------- # Start Flask Server # ---------------------------------- #

if __name__ == "__main__":
    app.run(debug=True, port=5000)
