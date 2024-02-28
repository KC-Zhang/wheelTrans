use reqwest;
use urlencoding;
use serde::Deserialize;
use google_apis::fleetengine::*;
use yup_oauth2::{read_service_account_key, ServiceAccountAuthenticator};

mod lib;

fn load_env() {
    dotenv::dotenv().ok();
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
    lib::get_geocoding(origin).await?;
    lib::get_geocoding(address1).await?;
    lib::get_geocoding(address2).await?;


    Ok(())
}

async fn create_fleet_engine_client() -> Result<FleetEngine, Box<dyn std::error::Error>> {
    // Read the service account key file
    let sa_key = read_service_account_key("path/to/your/service-account-key.json")
        .await
        .expect("Failed to read service account key file");

    // Create an authenticator using the service account credentials
    let authenticator = ServiceAccountAuthenticator::builder(sa_key)
        .build()
        .await?;

    // Create a FleetEngine client
    let client = FleetEngine::new(
        hyper::Client::builder().build(hyper_rustls::HttpsConnector::with_native_roots()),
        authenticator,
    );

    Ok(client)
}