import folium #a Python library for making interactive maps in HTML
import subprocess #is a Python module that lets Python start and interact with external programs/commands on your computer
# ------------------# Creating the Map # ------------------ #

def create_map(hops):
    
    mappable_hops = [] #builds a second list containing only hops we can actually place on a map.

    for hop in hops:               
        if hop["latitude"] is not None and hop["longitude"] is not None:
            mappable_hops.append(hop)

    if not mappable_hops:
        print("No mappable hops found")
        return

    first_hop = mappable_hops[0] #is only being used to decide where the map initially centers when it opens.
    
    route_map = folium.Map(              #creates the map object
        location=[first_hop["latitude"],first_hop["longitude"]],
        zoom_start=4,
        tiles="OpenTopoMap")

    route_coordinates = []

    for hop in mappable_hops:
        route_coordinates.append([hop["latitude"],hop["longitude"]])

    route_map.fit_bounds(route_coordinates) #zoom and position the map so all these coordinates are visible.

    folium.PolyLine(route_coordinates, weight=3).add_to(route_map)

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
            ),
            icon=folium.DivIcon(    #lets you use custom HTML instead of Folium’s default pin icon. 
                html=f"""<div style="
                    background-color: white; 
                    border: 2px solid black;
                    border-radius: 50%;
                    width: 28px;
                    height: 28px;
                    text-align: center;
                    line-height: 24px;
                    font-weight: bold;
                ">
                    {hop["number"]}
                </div>
                """
            )
        ).add_to(route_map)

    route_map.save("Trac3r_Map.html")

    subprocess.run([
        "open", "-a", "Google Chrome", "Trac3r_Map.html"
    ])