"""
Port of the grace art cloud function.

Takes ART (Race Roster) results CSV from a Google Drive folder, parses
it, and writes a formatted Google Sheet of individual results. The
Google Sheet remains the editable staging layer that sheet imports
consume. It does not touch racedb's database.
"""
import io
import urllib.parse

import gspread
from django.http import HttpResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from . import art_parse, google_sheets
from .models import Config

CSV_PATH = "/tmp/art.csv"
SERVICE_ACCOUNT_PATH = "/root/google_service_account.json"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    notifykey = Config.objects.filter(name="notifykey")[0].value
    if "notifykey" not in qstring or qstring["notifykey"][0] != notifykey:
        return HttpResponse("Correct notification key not sent")
    art_folder_id, art_distance, google_sheets_url = get_vars(qstring)
    output = "<pre>"
    output += f"Art Folder ID: {art_folder_id}"
    output += f"\nArt Distance (Meters): {art_distance}"
    output += f"\nGoogle Sheets URL: <a href='{google_sheets_url}' target='_blank'>{google_sheets_url}</a>"
    gc = gspread.service_account(SERVICE_ACCOUNT_PATH)
    status, sh = google_sheets.get_sheet(gc, google_sheets_url)
    if status != 0:
        output += "\n\nERROR: Something went wrong accessing the Google Sheet\n"
        output += status
        return HttpResponse(output + "</pre>")
    try:
        output = download_file(art_folder_id, output)
    except ValueError as e:
        return HttpResponse(output + str(e) + "</pre>")
    try:
        results, logs = art_parse.main(art_distance, csv_path=CSV_PATH)
    except ValueError as e:
        return HttpResponse(output + str(e) + "</pre>")
    if logs:
        output += logs
    if results:
        google_sheets.write(sh, results)
    output += f"\nProcessed {len(results)} results from ART!"
    if len(results) > 0:
        output += "\nWinner: {} in {}".format(results[0].athlete, results[0].guntime)
    return HttpResponse(output + "</pre>")


def download_file(folder_id, output):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH, scopes=SCOPES
    )
    drive_service = build("drive", "v3", credentials=credentials)
    page_token = None
    response = (
        drive_service.files()
        .list(
            q="'{}' in parents".format(folder_id),
            spaces="drive",
            fields="nextPageToken, " "files(id, name)",
            pageToken=page_token,
        )
        .execute()
    )
    files = response.get("files", [])
    files = [x for x in files if x.get("name").endswith(".csv")]
    if len(files) != 1:
        raise ValueError(
            "\n\nERROR: Folder https://drive.google.com/drive/folders/{} contains more than one CSV file!\n".format(
                folder_id
            )
        )
    file_id = files[0].get("id")
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(CSV_PATH, "wb")  # this can be used to write to disk
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))
    return output


def get_vars(qstring):
    """Get the input variables"""
    art_folder_id = qstring.get("art_folder_id", ["No art_folder_id!"])[0]
    art_distance = qstring.get("art_distance", ["No art_distance!"])[0]
    google_sheets_url = qstring.get("google_sheets_url", ["No google_sheets_url!"])[0]
    return art_folder_id, art_distance, google_sheets_url
