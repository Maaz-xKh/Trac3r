from traceroute import run_traceroute
from enrichment import enrich_hop

print("\nTrac3r starting...\n")

# --------------------- #User Input and Error Handling# ---------------------------------- #

target = input("Enter a website or IP address to trace: ")

hops = run_traceroute(target)

for hop in hops:
    enrich_hop(hop)

for hop in hops:
    print(f"Hop {hop['number']}:",
          f"IP = {hop['IP'] if hop['IP'] else 'No IP found'} |",
          f"Hostname: {hop["hostname"]} |",
          f"Avg Latency {hop["AvgLatency"]} ms|" if hop["AvgLatency"] is not None else "N/A |",
          f"ASN: {hop["asn"]} |", f"Organization: {hop["organization"]}", 
          f"city: {hop["city"]} |", f"Region: {hop["region"]} |", f"Country: {hop["country"]}")
      
# -------------------- # Test Environment# ---------------------------------- #
