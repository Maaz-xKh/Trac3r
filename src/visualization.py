import folium #a Python library for making interactive maps in HTML

# ------------------# Creating the Map # ------------------ #

def create_map(hops):
    
    mappable_hops = [] #builds a second list containing only hops we can actually place on a map.

    for hop in hops:               
        if hop["latitude"] is not None and hop["longitude"] is not None:
            mappable_hops.append(hop)

    if not mappable_hops:
        print("No mappable hops found")
        return

    first_hop = mappable_hops[0]

    route_map = folium.Map(              #creates the map object
        location=[first_hop["latitude"],first_hop["longitude"]],
        zoom_start=4
    )

    for hop in mappable_hops:
        folium.Marker(
            location=[hop["latitude"],hop["longitude"]],
            popup=(
                f"Hop {hop["number"]}<br>"
                f"IP: {hop["IP"]}<br>"
                f"Hostname: {hop["hostname"]}<br>"
                f"ASN: {hop['asn']}<br>"
                f"Organization: {hop['organization']}<br>"
                f"City: {hop['city']}<br>"
                f"Region: {hop['region']}<br>"
                f"Country: {hop['country']}<br>"
                f"Avg Latency: {hop['AvgLatency']} ms"
            )
        ).add_to(route_map)

    route_map.save("Trac3r_Map.html")