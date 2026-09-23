import subprocess   #gives Python access to the command line
import ipaddress    #gives Python access to IP address validation


def run_traceroute(target):

# --------------------- # POPEN # --------------------------------------------------- #
# Popen launches the system traceroute command as a separate process and lets Python read its command-line output while it is still running
    process = subprocess.Popen(
        ["traceroute", target], 
        stdout = subprocess.PIPE, stderr = subprocess.PIPE, 
        text=True)

# --------------------- # Hops List & Variable Initialization # ------------------- #
# Hops list is populated with parsed data from the live traceroute command output (subprocess.Popen) to build the route database
    hops =[]    

    for line in process.stdout:
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
    return hops

# -------------------- # Test Environment# ---------------------------------- #

# if __name__ == "__main__":
#     test_hops = run_traceroute("google.com")

#     for hop in test_hops:
#         print(hop)
