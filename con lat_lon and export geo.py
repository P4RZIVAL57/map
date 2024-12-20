import math
import csv
import json
from shapely.wkt import loads
from shapely.errors import ShapelyError

def utm_to_latlon(utm_easting, utm_northing, hemisphere, central_meridian):
    # Constants
    a = 6378137.0000
    b = 6356752.3141
    e = math.sqrt(1 - (b**2) / (a**2))
    x = 500000 - utm_easting
    y = utm_northing
    
    # Adjust for Southern Hemisphere
    if hemisphere.upper() in ["S", "SOUTH", "SUL"]:
        y = 10000000 - y
    
    M = y / 0.9996
    mu = M / (a * (1 - (e**2) / 4 - 3 * (e**4) / 64 - 5 * (e**6) / 256))
    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))
    
    # Series expansion for latitude
    j1 = (3 * e1 / 2 - 27 * e1**3 / 32)
    j2 = (21 * e1**2 / 16 - 55 * e1**4 / 32)
    j3 = (151 * e1**3 / 96)
    j4 = (1097 * e1**4 / 512)
    fp = mu + j1 * math.sin(2 * mu) + j2 * math.sin(4 * mu) + j3 * math.sin(6 * mu) + j4 * math.sin(8 * mu)
    
    e2 = e**2 / (1 - e**2)
    c1 = e2 * math.cos(fp)**2
    t1 = (math.sin(fp) / math.cos(fp))**2
    r1 = a * (1 - e**2) / ((1 - e**2 * math.sin(fp)**2)**(3 / 2))
    n1 = a / ((1 - e**2 * math.sin(fp)**2)**(1 / 2))
    d = x / (n1 * 0.9996)
    
    q1 = n1 * (math.sin(fp) / math.cos(fp)) / r1
    q2 = d**2 / 2
    q3 = (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * e2) * d**4 / 24
    q4 = (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 3 * c1**2 - 252 * e2) * d**6 / 720
    latrad = fp - q1 * (q2 - q3 + q4)
    
    lat = -1 * (latrad * (180 / math.pi)) if hemisphere.upper() in ["S", "SOUTH", "SUL"] else (latrad * (180 / math.pi))
    
    q5 = d
    q6 = (1 + 2 * t1 + c1) * d**3 / 6
    q7 = (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * e2 + 24 * t1**2) * d**5 / 120
    longrad1 = (q5 - q6 + q7) / math.cos(fp)
    longrad2 = longrad1 * (180 / math.pi)
    longi = central_meridian - longrad2 if central_meridian < 0 else central_meridian + longrad2
    
    return lat, longi

# Input/Output files
input_file = "lanes.csv"  # Input CSV file
output_file = "lanes.json"  # Output GeoJSON file

# Hemisphere and central meridian
hemisphere = "S"
central_meridian = -69

# Initialize data for GeoJSON
data = []

try:
    with open(input_file, "r") as file:
        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            try:
                wkt_data = row.get("geometry", "").strip()
                if not wkt_data:
                    raise ValueError("Invalid geometry")
                
                lane_id = row.get("LANE_ID", "")
                lane_type = row.get("TYPE", "")
                
                # Convert WKT to Shapely geometry
                geom = loads(wkt_data)
                
                # Convert UTM to Latitude/Longitude
                coordinates = []
                if geom.geom_type == "Polygon":
                    for ring in geom.exterior.coords:
                        lat, lon = utm_to_latlon(ring[0], ring[1], hemisphere, central_meridian)
                        coordinates.append([lon, lat])
                    geom_geojson = {"type": "Polygon", "coordinates": [coordinates]}
                elif geom.geom_type == "LineString":
                    for point in geom.coords:
                        lat, lon = utm_to_latlon(point[0], point[1], hemisphere, central_meridian)
                        coordinates.append([lon, lat])
                    geom_geojson = {"type": "LineString", "coordinates": coordinates}
                else:
                    raise ValueError("Unsupported geometry type")

                # Add feature to GeoJSON
                feature = {
                    "type": "Feature",
                    "properties": {
                        "LANE_ID": lane_id,
                        "TYPE": lane_type
                    },
                    "geometry": geom_geojson
                }
                data.append(feature)

            except Exception as e:
                print(f"Skipping row due to error: {e}")

    # Save to GeoJSON file
    with open(output_file, "w") as f:
        json.dump({"type": "FeatureCollection", "features": data}, f, indent=2)
    print(f"GeoJSON file saved to {output_file}")

except Exception as e:
    print(f"Error processing file: {e}")
