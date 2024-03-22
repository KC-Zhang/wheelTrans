import os
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import optimization_v1
import googlemaps
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pandas
import numpy as np
from IPython.display import display
import json  
import re
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from app.routing.resources.vehicles import vehicles
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

load_dotenv()
proxy_address = "http://127.0.0.1:7890"
# Set the environment variables to specify the proxy
os.environ["HTTP_PROXY"] = proxy_address
os.environ["HTTPS_PROXY"] = proxy_address
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/kaicheng/ProjectsFormal/wheelTrans/secrets/key.json"
os.environ["PROJECT_ID"] = "elderlyhometransportation"
googleMapKey = os.getenv("GOOGLE_MAP_API_KEY")

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
residentDataPath = ROOT_PATH + "/resources/TransportList.csv"
signupSheetPath = ROOT_PATH + "/resources/MondaySignup.csv"
outputDir = ROOT_PATH + "/output"
temp_directory = "app/temp"
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAP_API_KEY"))

invalidAddressPath = os.path.join(temp_directory, 'invalidAddress.csv')
invalidTransPath = os.path.join(temp_directory, 'invalidTransportation.csv')
signupPath = os.path.join(temp_directory, 'signups.csv')
notSignupPath = os.path.join(temp_directory, 'notSignups.csv')
failedSignupPath = os.path.join(temp_directory, 'failedSignups.csv')
directionsPath = os.path.join(temp_directory, 'directions.csv')

def getRoute(df, dfSignup):
    flat = dfSignup.stack().dropna().astype(int).tolist()
    #legacy code for day filter
    # weekday = 'M' # 'M', 'T', 'W', 'R', 'F'
    # attendingAMdf = df[df[weekday].notna() & (df['Trans Method'].str.contains('am', case=False))]
    cleanDf, invalidAddressDf, invalidTrans, notSignupDF, failedSignupList = etl(df, flat)
    geocodedDf, invalidGeoCodeDf = geocodeDf(cleanDf)
    requestJson = getRequestBody(geocodedDf)
    
    fleet_routing_client = optimization_v1.FleetRoutingClient()
    fleetOptimizationRequest = optimization_v1.OptimizeToursRequest.from_json(requestJson)
    fleetOptimizationResponse = fleet_routing_client.optimize_tours(
        fleetOptimizationRequest, timeout=100,
    )

    optimizedDf =  etlResult(fleetOptimizationResponse, geocodedDf)
    vehiclesIds= plotResults(optimizedDf)

    return vehiclesIds


def loadData():
    dailySignupDf = pandas.read_csv(signupSheetPath)
    flat = dailySignupDf.stack().dropna().astype(int).tolist()
    #legacy code for day filter
    # weekday = 'M' # 'M', 'T', 'W', 'R', 'F'
    # attendingAMdf = df[df[weekday].notna() & (df['Trans Method'].str.contains('am', case=False))]
    df = pandas.read_csv(residentDataPath)
    display('original df',df, df.shape)
    return df, flat

def etl(df, flat):
    validAddressDf, invalidAddressDf = validateAddress(df)
    validDf, invalidTrans = validateTransMethod(validAddressDf)
    attendingAMdf = validDf[validDf['Trans Method'].str.contains('am', case=False, na=False)]
    mrInt = attendingAMdf['MR #'].str.replace(r'\D','' , regex=True).astype(int)
    signupDF = attendingAMdf[mrInt.isin(flat)]
    notSignupDF = attendingAMdf[~mrInt.isin(flat)]
    cleanDf = signupDF.loc[:, ['MR #','Address','Trans Method', 'M', 'T', 'W', 'R', 'F', 'Notes', "Driver"]]
    failedSignupList= set(flat) - set(validDf['MR #'].str.replace(r'\D','' , regex=True).astype(int))
    saveSignups(cleanDf, notSignupDF, failedSignupList)
    return cleanDf, invalidAddressDf, invalidTrans, notSignupDF, failedSignupList

def validateAddress(df):
    invalidAddressDf = df[df['Address'].isna()]
    print ("invalid address", invalidAddressDf)
    invalidAddressDf.to_csv(invalidAddressPath, index=False)
    return df[df['Address'].notna()], invalidAddressDf
def validateTransMethod(df_):
    invalidTrans = df_[df_['Trans Method'].isna()]
    invalidTrans.to_csv(invalidTransPath, index=False)
    print('trans method invalid',invalidTrans)
    return df_[df_['Trans Method'].notna()], invalidTrans
def saveSignups(signupDf, notSignupDF, failedSignupList):
    signupDf.to_csv(signupPath, index=False)
    notSignupDF.to_csv(notSignupPath, index=False)
    with open(failedSignupPath, 'w') as f:
        for item in failedSignupList:
            f.write("%s\n" % item)
    return signupDf, notSignupDF, failedSignupList

def geocodeDf(cleanDf):
    columns = cleanDf.columns
    geocodedDf = pandas.DataFrame(columns=columns)
    invalidGeoCodeDf = pandas.DataFrame(columns=columns)
    origin = "8408 Garvey Ave. #101 Rosemead, CA 91770"
    for ind, row in cleanDf.iterrows():
        latlng = get_geocoding(gmaps,  row['Address'])
        if latlng:
            row['lat'] = latlng[0]
            row['lng'] = latlng[1]
            geocodedDf = pandas.concat([geocodedDf, pandas.DataFrame([row])], ignore_index=True, axis=0)
        else:
            print(f"Failed to get geocoding for {row['Address']}")
            invalidGeoCodeDf = pandas.concat([invalidGeoCodeDf, pandas.DataFrame([row])], ignore_index=True, axis=0)

    invalidGeoCodeDf.to_csv(invalidAddressPath, index=False, mode='a', header=False)
    return geocodedDf, invalidGeoCodeDf
def get_geocoding(gmaps, address):
    result = gmaps.geocode(address)
    if not result or len(result) != 1:
        print(f"Failed to get geocoding for {address}")
        return None
    location = result[0]['geometry']['location']
    lat = location["lat"]
    lng = location["lng"]
    return [lat, lng]

def getRequestBody(geocodedDf):
    shipments = []
    for ind, row in geocodedDf.iterrows():
        allowedVehicleIndices = list(range(len(vehicles)))
        drivers = [vehicle.get('label', '') for vehicle in vehicles]
        driverRequested = row['Driver']
        if ~pandas.isna(driverRequested) and driverRequested in drivers:
            allowedVehicleIndices = [drivers.index(driverRequested)]
        shipment = {
            "loadDemands": {
                "weight": {
                    "amount": "1"
                }
            },
            "pickups": [
                {
                    "arrivalLocation": {
                        "latitude": row['lat'],
                        "longitude": row['lng']
                    },
                    "duration": "60s",
                }
            ],
            "deliveries": [
                {
                    "arrival_location": {
                        "latitude": 34.0623483,
                        "longitude": -118.0859541
                    },
                    "duration": "10s",
                }
            ],
            "allowed_vehicle_indices": allowedVehicleIndices
        }

        note = row['Notes'] if row['Notes'] is not np.nan else ''
        isValidTime = check_time_format(note)
        if isValidTime:
            pickupTime = note.strip('+-')
            if note.endswith('-'):
                startTime = "2024-03-08T7:15:00Z"
                endTime = f"2024-03-08T{pickupTime}:00Z"
            elif note.endswith('+'):
                startTime = f"2024-03-08T{pickupTime}:00Z"
                endTime = "2024-03-08T9:30:00Z"
            else:
                startTime, endTime = getTimewindow(f"2024-03-08T{pickupTime}:00Z")
            shipment['pickups'][0]["timeWindows"] = [{
                    "startTime": startTime,
                    "endTime": endTime
                }]
            print(f"shipment {ind} start time {startTime} end time {endTime}")
        else:
            if note:  print(f"Invalid time format in the note {note} for {row['MR #']}")
        shipments.append(shipment)

    requestDict = {
        "parent": "projects/elderlyhometransportation",
        "model": {
            "shipments": shipments,
            "vehicles": vehicles,
            "global_start_time":"2024-03-08T7:15:00Z",
            "global_end_time":"2024-03-08T9:30:00Z",
            "global_duration_cost_per_hour": "60",
        },
        "populatePolylines": True,
        # "searchMode":2
    }
    requestJson = json.dumps(requestDict)
    return requestJson

def check_time_format(time_str):
    pattern = r'^\d{1,2}:\d{2}[+-]$'
    patternWindow = r'^\d{1,2}:\d{2}$'
    if re.match(pattern, time_str):
        return True
    elif re.match(patternWindow, time_str):
        return True
    else:
        return False
    
def getTimewindow(pickupTime):
    pickup_time = datetime.strptime(pickupTime, "%Y-%m-%dT%H:%M:%SZ")
    
    # Calculate the time window before 20 minutes
    before_window = pickup_time - timedelta(minutes=20)
    
    # Calculate the time window after 20 minutes
    after_window = pickup_time + timedelta(minutes=20)
    
    # Format the time windows in the same format as the input
    before_window_str = before_window.strftime("%Y-%m-%dT%H:%M:00Z")
    after_window_str = after_window.strftime("%Y-%m-%dT%H:%M:00Z")
    
    return before_window_str, after_window_str

def etlResult(fleetOptimizationResponse, geocodedDf):
    optimizedList=[]
    for vehicleRoute in fleetOptimizationResponse.routes:
        points = vehicleRoute.route_polyline.points
        startingMarker = f'34.0623483,-118.0859541'
        vehicleIndex = vehicleRoute.vehicle_index or 0

        #trim duplicate dropoff
        prev_isPickup = None
        visits = []
        for element in vehicleRoute.visits:
            isPickup = element.is_pickup
            if isPickup or isPickup != prev_isPickup:
                visits.append(element)
            prev_isPickup = isPickup
        tripNumber = 0        
        # write result to df
        for index, visit in enumerate(visits):
            #increment trip number upon dropoff
            if not visit.is_pickup: #dropoff
                data = {
                    "MR #": "",
                    "Arrival Time": visit.start_time,
                    "vehicle": vehicleIndex,
                    "order": index,
                    "routePolyline": points,
                    "tripNumber": tripNumber,
                    "Address": "-> Return to 8408 Garvey Ave. #101 Rosemead, CA 91770",
                    "lat":'34.0623483',
                    "lng": '-118.0859541'
                }
                row = pandas.Series(data)
                optimizedList.append(row)
                tripNumber += 1
                continue

            shipmentId = visit.shipment_index or 0
            row = geocodedDf.loc[shipmentId].copy()
            row["Arrival Time"]= visit.start_time
            row["vehicle"]= vehicleIndex
            row["order"]= index
            row["routePolyline"]= points
            row["tripNumber"]= tripNumber
            optimizedList.append(row)
        
    optimizedDf = pandas.DataFrame(optimizedList)
    return optimizedDf


def plotResults(optimizedDf):
    origin = (34.0623483, -118.0859541)  # Los Angeles, CA
    destination = (34.0623483, -118.0859541)  # Los Angeles, CA
    vehiclesIds = optimizedDf['vehicle'].unique()

    with open(directionsPath, "w") as f:
        f.write('')

    for vehicleId in vehiclesIds:
        number_of_seats = vehicles[vehicleId]['loadLimits']['weight']['maxLoad']
        sortedDf = optimizedDf[optimizedDf['vehicle'] == vehicleId].sort_values(by='order')
        tripIds = np.sort(sortedDf['tripNumber'].unique())
        routePolyline = sortedDf['routePolyline'].values[0]
        NOfPickups = 0
        # with open(outputDir +f'/waypointInfo{vehicleId}.csv', 'w') as f:
        #     f.write(f'Vehicle {vehicleId+1} \n')
        #     f.write(f'{number_of_seats} seats\n')
        table_data = []
        pdf_table = []
        
        table_data.append(list([f'Vehicle {vehicleId+1}. ']))
        # if vehicles[vehicleId].get('label', False):
        #     table_data.append(list([f'Driver {vehicles[vehicleId]['label']}']))
        table_data.append(list([f'{number_of_seats} seats']))

        with open(directionsPath, "a") as f:
            f.write(f'\nVehicle {vehicleId+1}\n')

        for tripId in tripIds:
            tripDf = sortedDf[sortedDf['tripNumber'] == tripId]
            waypoints = [[lat, lon] for lat, lon in tripDf[['lat', 'lng']].values]
            navigationUrl = create_google_maps_url(waypoints)
            # byteImage=generate_static_map(origin=origin, destination=destination, routePolyline=routePolyline,waypoints=waypoints, filename=f'map_with_route{vehicleId}.png' )
            # dfMeta = pandas.DataFrame([[],[f"Trip {tripId+1}"]])
            # dfMeta.to_csv(outputDir +f'/waypointInfo{vehicleId}.csv',header=False, index=False, mode='a')
            tripDf['Arrival Time'] = tripDf['Arrival Time'].dt.strftime('%H:%M')
            tripDf['order'] = tripDf['order'] + 1
            table_data.append([])
            table_data.append([f"Trip {tripId+1}"])
            table_data.append(['order', 'MR #', 'Address', 'Arrival Time', 'Notes', 'Driver'])
            for i, row in tripDf[['order', 'MR #', 'Address', 'Arrival Time', 'Notes', 'Driver']].iterrows():
                table_data.append(list(row.fillna('')))
            
            # tripDf[['order', 'MR #', 'Address', 'Arrival Time', 'Notes']].to_csv(outputDir +f'/waypointInfo{vehicleId}.csv', header=True, index=False, mode='a')
            dfMetaTail = pandas.DataFrame([[f"Trip {tripId+1}", navigationUrl]])
            dfMetaTail.to_csv(directionsPath, header=False, index=False, mode='a')
            #row count
            NOfPickups+=tripDf[tripDf['MR #']!=''].shape[0]

            
            # # save to image
            # with open(outputDir +f"/{vehicleId}.png", "wb") as f:
            #     f.write(byteImage)
            # #draw overlay
            # header=[f'vehicle Id:{vehicleId +1}       number of seats: {number_of_seats}\n\n\n\n\n'
            #         ,'order        '+'MR #        ' +' Address                                                          '+    'timeOfArrival        '+    'notes\n'] 
            # displayWaypointInfo=header+[f"{order}        {MR}        {Address if Address is not np.nan else ' '}            {arrivalTime}            {Notes if Notes is not np.nan else ' '}" for order, MR, Address, arrivalTime, Notes in tripDf[['order', 'MR #', 'Address', 'arrival time', 'Notes']].values]
            # drawToImage(byteImage, f'vehicle_{vehicleId+1}_seat_{number_of_seats}_tripId{tripId+1}', displayWaypointInfo)
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('TOPPADDING', (0, 1), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1),
        ])

        table = Table(table_data)
        table.setStyle(table_style)
        pdf_table.append(table)
        pdf = SimpleDocTemplate(temp_directory +f'/waypointInfo{vehicleId}.pdf', pagesize=letter)
        pdf.build(pdf_table)

        print(f"Vehicle {vehicleId+1} has {NOfPickups} passengers")
    return vehiclesIds

def drawToImage(byteImage, filename, waypoints):
    image = Image.open(io.BytesIO(byteImage))
    image = image.convert("RGB")
    padded_image = ImageOps.expand(image, (800, 0,0,500), fill="white")
    draw = ImageDraw.Draw(padded_image)
    text ='\n'.join(waypoints)
    font = ImageFont.load_default()
    font_size = 15
    font = font.font_variant(size=font_size)
    text_position = (10, 10)
    text_color = (0, 0, 0)
    draw.text(text_position, text, fill=text_color, font=font)

    padded_image.save(temp_directory + f"/{filename}.png")

def generate_static_map(origin, destination, routePolyline, waypoints,filename):
    startingMarker = f'34.0623483,-118.0859541'
    # Add markers for each waypoint with labels
    markers = []
    for i, waypoint in enumerate(waypoints):
        markers.append(f"markers=label:{i}|color:red|{waypoint[0]},{waypoint[1]}")
    markers_str = '&'.join(markers)
    static_map_url = f'https://maps.googleapis.com/maps/api/staticmap?size=1200x800&path=enc:{routePolyline}&{markers_str}&markers=color:blue|{startingMarker}&key={googleMapKey}'
    print (static_map_url)
    # Download the map image
    map_image = requests.get(static_map_url)
    return map_image.content
def create_google_maps_url(waypoints):
    base_url = "https://www.google.com/maps/dir/?api=1"
    origin = "origin=34.0623483,-118.0859541"
    destination = "destination=34.0623483,-118.0859541"
    parameters = "|".join([f"{waypoint[0]},{waypoint[1]}" for waypoint in waypoints])
    return f"{base_url}&{origin}&waypoints={parameters}&{destination}"

def createPdf(vehicleId, number_of_seats, df_ ):
    table_data = []
    # for i, row in data.iterrows():
    table_data.append(list([f'Vehicle {vehicleId+1} ']))
    table_data.append(list([f'{number_of_seats} seats']))
    for i, row in df_.iterrows():
        table_data.append(list(row))

    table = Table(table_data)
    pdf_table = []
    pdf_table.append(table)

    pdf = SimpleDocTemplate(temp_directory +f'/waypointInfo{vehicleId}.pdf', pagesize=letter)
    pdf.build(pdf_table)

if __name__ == '__main__':
    getRoute()