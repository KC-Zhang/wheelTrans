from fastapi import FastAPI, File, UploadFile, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import zipfile
import os
from app.routing.routing import getRoute
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
from dotenv import load_dotenv

load_dotenv()

security = HTTPBasic()


temp_directory = "app/temp"
invalidAddressPath = os.path.join(temp_directory, 'invalidAddress.csv')
invalidTransPath = os.path.join(temp_directory, 'invalidTransportation.csv')
signupPath = os.path.join(temp_directory, 'signups.csv')
notSignupPath = os.path.join(temp_directory, 'notSignups.csv')
failedSignupPath = os.path.join(temp_directory, 'failedSignups.csv')
directionsPath = os.path.join(temp_directory, 'directions.csv')

app = FastAPI()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "admin"
    correct_password = os.getenv("PASSWORD")

    
    if credentials.username == correct_username and credentials.password == correct_password:
        return credentials.username
    else:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


# Adjusting for the project structure
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Ensure the 'temp' directory exists
temp_directory = "app/temp"
os.makedirs(temp_directory, exist_ok=True)

@app.get("/", response_class=HTMLResponse, )
async def upload_form(request: Request, user: str = Depends(verify_credentials)):
    return templates.TemplateResponse("upload_form.html", {"request": request})

@app.post("/upload")
async def process_files(request: Request, file1: UploadFile = File(...), file2: UploadFile = File(...), user: str = Depends(verify_credentials)):
    df1 = pd.read_csv(file1.file)
    df2 = pd.read_csv(file2.file, header=None)
    
    vehiclesIds = getRoute(df1, df2)

    zip_path = os.path.join(temp_directory, "files.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(invalidAddressPath, arcname='invalidAddress.csv')
        zipf.write(invalidTransPath, arcname='invalidTransportation.csv')
        zipf.write(signupPath, arcname='signups.csv')
        zipf.write(notSignupPath, arcname='notSignups.csv')
        zipf.write(failedSignupPath, arcname='failedSignups.csv')
        zipf.write(directionsPath, arcname='directions.csv')
        for vehicleId in vehiclesIds:
            path = temp_directory +f'/waypointInfo{vehicleId}.pdf'
            zipf.write(path, arcname=f'waypointInfo{vehicleId}.pdf')
            os.remove(path)

    
    # Optionally, remove the CSV files after adding them to the ZIP
    os.remove(invalidAddressPath)
    os.remove(invalidTransPath)
    os.remove(signupPath)
    os.remove(notSignupPath)
    os.remove(failedSignupPath)
    os.remove(directionsPath)

    
    # Respond with the ZIP file for download
    return FileResponse(path=zip_path, media_type='application/zip', filename="files.zip")
