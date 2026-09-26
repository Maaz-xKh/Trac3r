from traceroute import run_traceroute
from enrichment import enrich_hop
from urllib.parse import urlparse #takes a URL and separates it into components like scheme, hostname, path, etc.
import socket #gives Python access to lower-level networking functions. This checks if a hostname can be resolved to an IP address.
from visualization import create_map

print("\nTrac3r starting...\n")

# --------------------- #User Input and Error Handling# ---------------------------------- #

def clean_target(user_input):
    user_input = user_input.strip()  # Remove leading/trailing whitespace

    if "://" not in user_input:
        user_input = "http://" + user_input  # Add scheme if missing

    parsed_url = urlparse(user_input)
    return parsed_url.hostname  # Return only the hostname part

#--------# Error Handling #------#
while True:
    target = clean_target(input("Enter a website or IP address to trace: "))
    
    try:
        socket.getaddrinfo(target, None)
        break
    except socket.gaierror:
        print("Invalid website or IP Address. Please try again.\n")

hops = []
map_opened = False

# --------------------- # Live Hop Processing # ---------------------------------- #


for hop in run_traceroute(target):
    enrich_hop(hop)
    hops.append(hop)

    if hop["latitude"] is not None and hop["longitude"] is not None:
        if not map_opened:
            create_map(hops, open_browser=True)
            map_opened = True
        else:
            create_map(hops)

for hop in hops:
    print(f"Hop {hop['number']}:",
          f"IP = {hop['IP'] if hop['IP'] else 'No IP found'} |",
          f"Hostname: {hop["hostname"]} |",
          f"Avg Latency {hop["AvgLatency"]} ms|" if hop["AvgLatency"] is not None else "N/A |",
          f"ASN: {hop["asn"]} |", f"Organization: {hop["organization"]}", 
          f"city: {hop["city"]} |", f"Region: {hop["region"]} |", f"Country: {hop["country"]}")
      
# -------------------- # Test Environment# ---------------------------------- #

# test_url = "google.com"

# parsed = urlparse(test_url)

# print(parsed)
# print(parsed.hostname)