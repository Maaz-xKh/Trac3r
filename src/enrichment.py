
import ipaddress
from ipwhois import IPWhois #perform RDAP: Registration Data Access Protocol which lookups for an 
                            #IP address and give us information such as the ASN and organization/network name
import requests     #is a Python library for making HTTP requests to websites and APIs

# -------------------- # Enrichment function # --------------------- #
# Enriches traceroute hop data with additional network ownership and geolocation information
def enrich_hop(hop):
    hop_IP = hop["IP"]

    hop_ASN = None
    hop_organization = None
    hop_city = None
    hop_region = None
    hop_country = None
    hop_longitude = None
    hop_latitude = None

# -------------------- # ASN and Org Extraction # --------------------- #
    if hop_IP:
        ip_obj = ipaddress.ip_address(hop_IP)

        if ip_obj.is_private:
            hop_ASN = "Private"
            hop_organization = "Private Network"

        else:
            try:
                lookup = IPWhois(hop_IP, timeout=2)
                data = lookup.lookup_rdap(depth=0, retry_count=0)

                hop_ASN = data["asn"]
                hop_organization = data["asn_description"]

            except Exception:
                hop_ASN = None
                hop_organization = None

# -------------------- # Geolocation data # --------------------- #
    if hop_IP and ipaddress.ip_address(hop_IP).is_global:
        try:
            response = requests.get(f"https://ipwho.is/{hop_IP}", timeout=(2, 2))
            location_data = response.json()

            if location_data["success"]:
                hop_city = location_data["city"]
                hop_region = location_data["region"]
                hop_country = location_data["country"]
                hop_longitude = location_data["longitude"]
                hop_latitude = location_data["latitude"]

        except Exception:
            hop_city = None
            hop_region = None
            hop_country = None
            hop_longitude = None
            hop_latitude = None

    hop["asn"] = hop_ASN
    hop["organization"] = hop_organization
    hop["city"] = hop_city
    hop["region"] = hop_region
    hop["country"] = hop_country
    hop["longitude"] = hop_longitude
    hop["latitude"] = hop_latitude

    return hop        


# -------------------- # Test Environment# ---------------------------------- #
# if __name__ == "__main__":
#     test_hop = {"number": 1, "IP": "209.148.229.109", "hostname": "rogers.com", "AvgLatency": 10.5}
#     enriched_hop = enrich_hop(test_hop)
#     print(enriched_hop)