## Traceroute Basics

Traceroute discovers the path packets take toward a destination by sending probes with increasing TTL values.

TTL stands for **Time To Live**. Each router that forwards a packet decreases the TTL by 1. When the TTL reaches 0, that router can respond with an **ICMP - Internet Control Message Protocol** "Time Exceeded" message. Traceroute uses that response to identify the router at that hop.


## Why Traceroute Sometimes Shows `* * *`

For my system, three probes are sent with each hop, hence the three different Round-Trip-Time (RTT) or the three ***. Not every router responds to traceroute probes and show `* * *` (for example when I ran www.oracle.com) because some networks may:
- firewall or filter traceroute traffic
- suppress ICMP responses
- rate-limit ICMP responses
- configure routers not to reveal themselves
- allow normal HTTPS traffic while ignoring traceroute probes

This does not necessarily mean the route is broken or that the destination is unreachable. Normal traffic may still pass through those routers even though they do not respond to traceroute.

## Development Changes
**Initial Use of `subprocess.run()`**

The first version of Trac3r used:

`subprocess.run(...)` which starts an external program, waits for it to completely finish, and then returns the result to Python and it was used to run the system traceroute command from Python.

Example:

`subprocess.run(["traceroute", target], ...)`

The output was captured using:

`capture_output=True`

and accessed using:

`result.stdout`

`stdout` stands for **standard output**. It is the normal output produced by a program.


**Why `subprocess.run()` Became a Problem**

Some traceroutes do not finish quickly.

For example, a traceroute may initially receive responses normally and then encounter several routers that do not respond:

10  * * *  
11  * * *  
12  * * *

Traceroute continues trying additional hops and waits for unanswered probes to time out.

Because `subprocess.run()` waits for the entire traceroute process to finish before returning control to Python, Trac3r can appear frozen even though traceroute is still running.

An overall timeout such as:

`timeout=120`

can eventually cause Python to raise:

`subprocess.TimeoutExpired`

The problem is not necessarily that traceroute failed. It may simply still be waiting for responses from later hops.


**Switching to `subprocess.Popen()`**

Trac3r was changed from:

`subprocess.run(...)`

to:

`subprocess.Popen(...)`

`Popen()` starts the external process but allows Python to interact with it while the process is still running.

This is better for Trac3r because traceroute output can be processed as each hop appears instead of waiting for the entire traceroute to finish.

Example:

```python
process = subprocess.Popen(
    ["traceroute", target],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)