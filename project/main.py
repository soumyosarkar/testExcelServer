from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

# ---------------- CONFIG ---------------- #

import os
import json
from google.oauth2.service_account import Credentials
from pathlib import Path

# ---------------- CONFIG ---------------- #

SPREADSHEET_NAME = "hotel_data"
SHEET_NAME = "Sheet1"

# Credential handling for Render (Env Var) vs Local (File)
# We expect the content of credentials.json to be in the GOOGLE_CREDENTIALS_JSON env var
google_credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")

if google_credentials_json:
    # If env var exists, load from the string
    creds_dict = json.loads(google_credentials_json)
    BASE_CREDS = Credentials.from_service_account_info(creds_dict)
else:
    # Fallback to local file
    CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
    if not CREDENTIALS_FILE.exists():
         # Try looking in the parent directory just in case, or absolute path fallback if needed
        CREDENTIALS_FILE = Path(r"C:\Users\Mihup\OneDrive\Desktop\Excel_Server\project\credentials.json")
    
    if CREDENTIALS_FILE.exists():
         BASE_CREDS = Credentials.from_service_account_file(CREDENTIALS_FILE)
    else:
        raise FileNotFoundError("credentials.json not found in env vars or local path")

# ---------------- SETUP ---------------- #

app = FastAPI()

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = BASE_CREDS.with_scopes(scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)


# ---------------- MODELS ---------------- #

class User(BaseModel):
    booking_id: str
    name: str
    phone_number: str
    checkin_date: str
    checkout_date: str
    apartment_type: str
    nights: int


# ---------------- ROUTES ---------------- #

@app.get("/bookings")
def get_all_bookings():
    # Returns the raw data from the sheet
    return sheet.get_all_records()


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: str):
    records = sheet.get_all_records()
    
    # We look for the key "Booking Id" because that is what is written in the Sheet header
    for row in records:
        if str(row["Booking Id"]) == booking_id:
            return row

    raise HTTPException(status_code=404, detail="Booking not found")


@app.post("/bookings")
def create_booking(user: User):
    # We manually map the Python data to the Spreadsheet columns
    # Order MUST match the columns: A, B, C, D, E, F, G
    row_data = [
        user.booking_id,      # Column A: Booking Id
        user.name,            # Column B: Name
        user.phone_number,    # Column C: Phone Number
        user.checkin_date,    # Column D: Checkin Date
        user.checkout_date,   # Column E: Checkout Date
        user.apartment_type,  # Column F: Apartment Type
        user.nights           # Column G: Nights
    ]

    sheet.append_row(row_data)
    return {"message": "Booking created", "data": user}


@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: str):
    records = sheet.get_all_records()

    for index, row in enumerate(records):
        # We check "Booking Id" (from the sheet header)
        if str(row["Booking Id"]) == booking_id:
            # +2 because spreadsheet is 1-indexed AND has a header row
            sheet.delete_rows(index + 2)
            return {"message": f"Booking {booking_id} deleted"}

    raise HTTPException(status_code=404, detail="Booking not found")