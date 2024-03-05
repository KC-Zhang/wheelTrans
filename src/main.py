import requests
import os
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import optimization_v1

proxy_address = "http://127.0.0.1:7890"
# Set the environment variables to specify the proxy
os.environ["HTTP_PROXY"] = proxy_address
os.environ["HTTPS_PROXY"] = proxy_address
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/kaicheng/ProjectsFormal/wheelTrans/secrets/key.json"
os.environ["PROJECT_ID"] = "elderlyhometransportation"


def call_sync_api() -> None:
    request_file_name = "src/resources/request.json"
    fleet_routing_client = optimization_v1.FleetRoutingClient()

    with open(request_file_name) as f:
        fleet_routing_request = optimization_v1.OptimizeToursRequest.from_json(f.read())
        fleet_routing_request.parent = f"projects/elderlyhometransportation"
        fleet_routing_response = fleet_routing_client.optimize_tours(
            fleet_routing_request, timeout=10
        )
        print(fleet_routing_response)


def get_direction(origin, destination, waypoints):
    waypoints_str = "|".join(["optimize:true"] + waypoints)
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    google_map_api_key = os.getenv("GOOGLE_MAP_API_KEY")

    params = {
        "destination": destination,
        "origin": origin,
        "waypoints": waypoints_str,
        "key": google_map_api_key
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None


def get_geocoding(address):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    google_map_api_key = os.getenv("GOOGLE_MAP_API_KEY")

    params = {
        "address": address,
        "key": google_map_api_key
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        for result in results:
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            lat = location.get("lat")
            lng = location.get("lng")
            print(f"Latitude: {lat}, Longitude: {lng}")
        return response.text
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None


def main():
    origin = "8408 Garvey Ave. #101 Rosemead, CA 91770"
    destination = "8408 Garvey Ave. #101 Rosemead, CA 91770"
    address1 = "3843 Maxson Road #226 El Monte, CA 91732"
    address2 = "119 Garcelon Ave Apt B Monterey Park, CA 91754"
    waypoints = [address1, address2]
    # get_direction(origin, destination, waypoints)
    # get_geocoding(origin)
    # get_geocoding(address1)
    # get_geocoding(address2)

    response = call_sync_api()

if __name__ == "__main__":
    main()
