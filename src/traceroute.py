import subprocess   #gives Python access to the command line
import ipaddress    #gives Python access to IP address validation
import time         #lets us measure elapsed time
import select       #lets Python wait for output from traceroute without blocking forever

def run_traceroute(target):

# --------------------- # POPEN # --------------------------------------------------- #
# Popen launches the system traceroute command as a separate process and lets Python read its command-line output while it is still running
    process = subprocess.Popen(
        ["traceroute", "-m", "20", "-w", "2",target], 
        stdout = subprocess.PIPE, stderr = subprocess.PIPE, 
        text=True)

# --------------------- # Hops List & Variable Initialization # ------------------- #
# --------------------- # Safeguarding # ------------------------------------------ #
# Hops list is populated with parsed data from the live traceroute command output (subprocess.Popen) to build the route database
    hops =[]    

    consecutive_no_response = 0

# Trace safeguards:
# -m 20 in Popen limits traceroute to a maximum of 20 hops.
# 4 consecutive missing hops stops the trace if the route becomes persistently unresponsive.
# A 30-second global timeout provides a final safety limit if traceroute itself gets stuck.

    trace_timeout = 30
    start_time = time.monotonic()

    while True:
        elapsed_time = time.monotonic() - start_time
        remaining_time = trace_timeout - elapsed_time

        if remaining_time <=0:
            print("\nTrace stopped after exceeding the 30-second time limit.")
            print(
                "The destination may still be reachable, but some routers may be "
                "filtering, rate-limiting, or ignoring traceroute probes.")
            process.terminate()
            break

        ready, _, _ = select.select([process.stdout], [], [],remaining_time)

        if not ready:
            print("\nTrace stopped after exceeding the 30-second time limit.")
            print(
                "The destination may still be reachable, but some routers may be "
                "filtering, rate-limiting, or ignoring traceroute probes.")
            process.terminate()
            break

        line = process.stdout.readline()

        if line == "" and process.poll() is not None: #checks whether the external traceroute process has finished
            break

        parts = line.split()

        if parts and parts[0].isdigit():
            hop_number = int(parts[0])
            hop_IP = None
            hop_hostname = None
            hop_latencies = []


# -------------------- # IP Address Extraction # --------------------- #
            if len(parts) > 2 and not parts[1].startswith("(") and not parts[1] == "*":
                try:
                    ipaddress.ip_address(parts[1].strip("()"))
                except ValueError:
                    hop_hostname = parts[1]

# -------------------- # IP Address Extraction # --------------------- #
            for part in parts[1:]:
                candidate = part.strip("()")

                try:
                    ipaddress.ip_address(candidate)
                    hop_IP = candidate
                    break
                except ValueError:
                    continue

        if hop_IP is None:
            consecutive_no_response += 1
        else:
            consecutive_no_response = 0
# -------------------- # Latency Extraction # --------------------- #
            for i in range(len(parts)-1):
                if parts[i + 1] == "ms":
                    try:
                        hop_latencies.append(float(parts[i]))
                    except ValueError:
                        continue

            if hop_latencies:
                average_latency = round((sum(hop_latencies)/len(hop_latencies)),2)
            else:
                average_latency = None

            hop = {"number": hop_number, "IP": hop_IP, "hostname": hop_hostname, "AvgLatency": average_latency}

            hops.append(hop)
            print(f"Hop {hop_number}: {hop_IP if hop_IP else 'No IP found'}")

            if consecutive_no_response >= 4:
                print("\nTrace stopped after 4 consecutive unresponsive hops")
                print("The route may continue but the intermediate routers may be "
                      "filtering, rate-limiting, or ignoring traceroute probes.")
                process.terminate()
                break
    return hops

# -------------------- # Test Environment# ---------------------------------- #

# if __name__ == "__main__":
#     test_hops = run_traceroute("google.com")

#     for hop in test_hops:
#         print(hop)
