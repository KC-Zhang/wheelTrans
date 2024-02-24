use reqwest;
use std::env;
use urlencoding;

fn load_env() {
    dotenv::dotenv().ok();
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

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    load_env();
    // Fetch the Google Maps API key from the environment
    let destination = "8408 Garvey Ave. #101 Rosemead, CA 91770";
    let origin = "8408 Garvey Ave. #101 Rosemead, CA 91770";
    let waypoints = vec![
        "3843 Maxson Road #226  El Monte, CA 91732",
        "119 Garcelon Ave Apt B  Monterey Park, CA 91754",
        "119 Garcelon Ave Apt B  Monterey Park, CA 91754",
    ]; // Waypoints as a list
    get_direction(origin, destination, waypoints).await?;

    Ok(())
}