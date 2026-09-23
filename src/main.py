print("Trac3r starting...")

import subprocess #gives Python access to the command line
import ipaddress #gives Python access to IP address validation

target = input("Enter a website or IP address to trace: ")

process = subprocess.Popen(
    ["traceroute", target], 
    stdout = subprocess.PIPE, stderr = subprocess.PIPE, 
    text=True)

for line in process.stdout:
    hops =[]
    parts = line.split()

    if parts and parts[0].isdigit():
        hop_number = parts[0]
        hop_IP = None

        for part in parts[1:]:
            candidate = part.strip("()")

            try:
                ipaddress.ip_address(candidate)
                hop_IP = candidate
                break
            except ValueError:
                continue
            
        print(f"Hop {hop_number}: {hop_IP if hop_IP else 'No IP found'}")



