use reqwest;
use urlencoding;
use serde::Deserialize;
use serde_json::Value;
use std::{env, fs};

mod lib;

fn load_env() {
    dotenv::dotenv().ok();
}

fn read_request_body() -> Result<Value, Box<dyn std::error::Error>> {
    let contents =
        fs::read_to_string("src/resources/request.json").expect("Unable to read request body file");
    let json: Value = serde_json::from_str(&contents)?;
    Ok(json)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    load_env();
    // Fetch the Google Maps API key from the environment
    let destination = "8408 Garvey Ave. #101 Rosemead, CA 91770";
    let origin = "8408 Garvey Ave. #101 Rosemead, CA 91770";
    let address1 = "3843 Maxson Road #226  El Monte, CA 91732";
    let address2 = "119 Garcelon Ave Apt B  Monterey Park, CA 91754";

    let _waypoints = vec![
        "3843 Maxson Road #226  El Monte, CA 91732",
        "119 Garcelon Ave Apt B  Monterey Park, CA 91754",
    ];
    // get_direction(origin, destination, waypoints).await?;
    // lib::get_geocoding(origin).await?;
    // lib::get_geocoding(address1).await?;
    // lib::get_geocoding(address2).await?;

    let url = "https://cloudoptimization.googleapis.com/v1/projects/elderlyhometransportation:optimizeTours";
    let body = read_request_body()?;
    lib::make_post_request(url, body).await?;

    Ok(())
}
