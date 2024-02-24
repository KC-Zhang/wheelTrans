use reqwest;
use std::env;

fn load_env() {
    dotenv::dotenv().ok();
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    load_env();
    // Fetch the Google Maps API key from the environment
    let google_map_api_key = env::var("GOOGLE_MAP_API_KEY").expect("GOOGLE_MAP_API_KEY not set");
    let destination = "Concord, MA";
    let origin = "Boston, MA";
    let waypoints = vec!["Charlestown,MA", "Lexington,MA"]; // Waypoints as a list
    let waypoints_str = waypoints.join("|");
    let base_url = "https://maps.googleapis.com/maps/api/directions/json";

    let params = format!(
        "destination={}&origin={}&waypoints={}&key={}",
        destination,
        origin,
        waypoints_str,
        google_map_api_key
    );

    let url = format!("{}?{}", base_url, params);
    let response = reqwest::get(&url).await?;
    if response.status().is_success() {
        let body = response.text().await?;
        println!("Response body: {}", body);
    } else {
        println!("Request failed with status code: {}", response.status());
    }

    Ok(())
}
