use serde::Deserialize;
use std::env;
use serde_json::Value;

#[derive(Debug, Deserialize)]
struct Location {
    lat: f64,
    lng: f64,
}

#[derive(Debug, Deserialize)]
struct Geometry {
    location: Location,
}

#[derive(Debug, Deserialize)]
struct GeocodingResult {
    geometry: Geometry,
}

#[derive(Debug, Deserialize)]
struct GeocodingResponse {
    results: Vec<GeocodingResult>,
}

fn extract_lat_long(response: &GeocodingResponse) -> Vec<(f64, f64)> {
    let mut lat_longs = Vec::new();

    for result in &response.results {
        let lat = result.geometry.location.lat;
        let lng = result.geometry.location.lng;
        lat_longs.push((lat, lng));
    }

    lat_longs
}


async fn get_direction(
    origin: &str,
    destination: &str,
    waypoints: Vec<&str>,
) -> Result<String, Box<dyn std::error::Error>> {
    let waypoints_str = format!("{}|{}", "optimize:true", waypoints.join("|"));
    let base_url = "https://maps.googleapis.com/maps/api/directions/json";
    let google_map_api_key = env::var("GOOGLE_MAP_API_KEY").expect("GOOGLE_MAP_API_KEY not set");

    let encoded_destination = urlencoding::encode(destination);
    let encoded_origin = urlencoding::encode(origin);
    let encoded_waypoints = urlencoding::encode(&waypoints_str);
    let encoded_api_key = urlencoding::encode(&google_map_api_key);

    let url = format!(
        "{}?destination={}&origin={}&waypoints={}&key={}",
        base_url, encoded_destination, encoded_origin, encoded_waypoints, encoded_api_key
    );
    println!("URL: {}", url);
    let response = reqwest::get(&url).await?;

    if response.status().is_success() {
        let body = response.text().await?;
        println!("Body: {}", body);
        Ok(body)
    } else {
        let status_code = response.status().as_u16();
        let error_msg = format!("Request failed with status code: {}", status_code);
        println!("{}", error_msg);
        Err(error_msg.into())
    }
}

pub async fn get_geocoding (address: &str) -> Result<String, Box<dyn std::error::Error>> {
    let base_url = "https://maps.googleapis.com/maps/api/geocode/json";
    let google_map_api_key = env::var("GOOGLE_MAP_API_KEY").expect("GOOGLE_MAP_API_KEY not set");
    let encoded_address = urlencoding::encode(address);
    let encoded_api_key = urlencoding::encode(&google_map_api_key);
    let url = format!("{}?address={}&key={}", base_url, encoded_address, encoded_api_key);
    let response = reqwest::get(&url).await?;

    if response.status().is_success() {
        let body = response.text().await?;
        let body_json: Value = serde_json::from_str(&body)?;
        let geocoding_response: GeocodingResponse = serde_json::from_value(body_json)?;

        // Extract latitudes and longitudes
        let lat_longs = extract_lat_long(&geocoding_response);

        for (lat, lng) in lat_longs {
            println!("Latitude: {}, Longitude: {}", lat, lng);
        }
        Ok(body)
    } else {
        let status_code = response.status().as_u16();
        let error_msg = format!("Request failed with status code: {}", status_code);
        println!("{}", error_msg);
        Err(error_msg.into())
    }
}
