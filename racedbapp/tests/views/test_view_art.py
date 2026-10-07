import csv
import io

import gspread
import pytest

from racedbapp.models import Config

NOTIFY_KEY = "test-notify-key"

ART_CSV = None  # built below


def art_csv():
    headings = [
        "Race Distance (in meters)",
        "Bib #",
        "Overall Place",
        "Finishing Time",
        "First Name",
        "Last Name",
        "Sex",
        "Eligible Division(s)",
        "Age",
        "Chip Time",
        "City",
        "Split Times",
    ]
    athletes = [
        ("1", 1, "Per", "Lap", "00:19:31", ["00:05:06", "00:04:29"]),
        ("2", 2, "Cum", "Runner", "00:19:31", ["00:05:06", "00:09:35"]),
    ]
    rows = [headings]
    for bib, place, first_name, last_name, guntime, splits in athletes:
        for split in splits:
            rows.append([
                "5000",
                bib,
                str(place),
                guntime,
                first_name,
                last_name,
                "X",
                "Open",
                "30",
                guntime,
                "City",
                split,
            ])
    content = io.StringIO()
    csv.writer(content).writerows(rows)
    return content.getvalue()


class FakeStatus:
    def __init__(self, progress):
        pass

    def progress(self):
        return 1.0


class FakeDownloader:
    def __init__(self, fh, request):
        fh.write(art_csv().encode())
        self.request = request

    def next_chunk(self):
        return FakeStatus(100), True


class FakeWorksheet:
    def __init__(self, title):
        self.title = title
        self._properties = {"sheetId": 42}
        self.frozen = False
        self.formats = []

    def freeze(self, rows):
        self.frozen = rows

    def format(self, range_, format_):
        self.formats.append((range_, format_))


class FakeSpreadsheet:
    def __init__(self):
        self.worksheets = {}
        self.updates = []
        self.batch_updates = []

    def add_worksheet(self, title, rows, cols, index=None):
        worksheet = FakeWorksheet(title)
        self.worksheets[title] = worksheet
        return worksheet

    def del_worksheet(self, worksheet):
        self.worksheets.pop(worksheet.title, None)

    def worksheet(self, title):
        if title not in self.worksheets:
            raise gspread.exceptions.WorksheetNotFound(title)
        return self.worksheets[title]

    def batch_update(self, body):
        self.batch_updates.append(body)

    def values_update(self, range_, params=None, body=None):
        self.updates.append((range_, body))


class FakeGC:
    def __init__(self):
        self.opened = []

    def open_by_url(self, url):
        self.opened.append(url)
        self.last_sheet = FakeSpreadsheet()
        return self.last_sheet


def fake_drive(files):
    def _build(service, version, credentials):
        drive = type("Drive", (), {})()
        files_resource = type("Files", (), {})()

        class ListRequest:
            def __init__(self, q, spaces, fields, pageToken):
                self.q = q

            def execute(self):
                return {"files": files}

        class GetMediaRequest:
            def __init__(self, fileId):
                self.fileId = fileId

        def list(**kwargs):
            return ListRequest(**kwargs)

        def get_media(fileId):
            return GetMediaRequest(fileId)

        files_resource.list = list
        files_resource.get_media = get_media
        drive.files = lambda: files_resource
        return drive

    return _build


@pytest.fixture
def art_setup(db, tmp_path, monkeypatch):
    Config.objects.bulk_create([Config(name="notifykey", value=NOTIFY_KEY)])
    gc = FakeGC()
    monkeypatch.setattr(
        "racedbapp.view_art.gspread.service_account", lambda path: gc
    )
    monkeypatch.setattr(
        "racedbapp.view_art.SERVICE_ACCOUNT_PATH", str(tmp_path / "sa.json")
    )
    monkeypatch.setattr(
        "racedbapp.view_art.service_account.Credentials.from_service_account_file",
        lambda path, scopes: None,
    )
    monkeypatch.setattr("racedbapp.view_art.CSV_PATH", str(tmp_path / "art.csv"))
    return gc


@pytest.mark.django_db
def test_art_requires_correct_notifykey(art_setup):
    from django.test import Client

    client = Client()
    response = client.get("/art/", {"art_folder_id": "folder-1"})
    assert response.status_code == 200
    assert response.content.decode() == "Correct notification key not sent"


@pytest.mark.django_db
def test_art_wrong_notifykey(art_setup):
    from django.test import Client

    client = Client()
    response = client.get(
        "/art/",
        {"notifykey": "wrong", "art_folder_id": "folder-1"},
    )
    assert response.status_code == 200
    assert response.content.decode() == "Correct notification key not sent"


@pytest.mark.django_db
def test_art_success_path(art_setup, monkeypatch):
    from django.test import Client

    monkeypatch.setattr(
        "racedbapp.view_art.build", fake_drive([{"id": "f1", "name": "art.csv"}])
    )
    monkeypatch.setattr(
        "racedbapp.view_art.MediaIoBaseDownload", FakeDownloader
    )
    client = Client()
    response = client.get(
        "/art/",
        {
            "notifykey": NOTIFY_KEY,
            "art_folder_id": "folder-1",
            "art_distance": "5000",
            "google_sheets_url": "https://docs.google.com/spreadsheets/d/test-sheet",
        },
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "<pre>" in content
    assert "Art Folder ID: folder-1" in content
    assert "Art Distance (Meters): 5000" in content
    assert "Processed 2 results from ART!" in content
    assert "Winner: Per Lap in 00:19:31" in content
    sh = art_setup.last_sheet
    assert art_setup.opened == ["https://docs.google.com/spreadsheets/d/test-sheet"]
    writes = [body for range_, body in sh.updates if range_.startswith("individual!")]
    assert len(writes) == 2  # headings + data
    data = writes[1]["body"] if "body" in writes[1] else writes[1]
    values = data["values"]
    flat = " ".join(cell for row in values for cell in row)
    assert "Per Lap" in flat
    assert "Cum Runner" in flat
    individual = sh.worksheets["individual"]
    assert individual.frozen == 1


@pytest.mark.django_db
def test_art_more_than_one_csv_errors(art_setup, monkeypatch):
    from django.test import Client

    monkeypatch.setattr(
        "racedbapp.view_art.build",
        fake_drive([
            {"id": "f1", "name": "a.csv"},
            {"id": "f2", "name": "b.csv"},
        ]),
    )
    client = Client()
    response = client.get(
        "/art/",
        {
            "notifykey": NOTIFY_KEY,
            "art_folder_id": "folder-1",
            "art_distance": "5000",
            "google_sheets_url": "https://docs.google.com/spreadsheets/d/test-sheet",
        },
    )
    content = response.content.decode()
    assert "contains more than one CSV file!" in content
    assert "Processed" not in content


@pytest.mark.django_db
def test_art_sheet_access_error(art_setup, monkeypatch):
    from django.test import Client

    class ErrorGC(FakeGC):
        def open_by_url(self, url):
            class FakeResponse:
                status_code = 403
                reason = "PERMISSION_DENIED"

                def json(self):
                    return {"error": {"code": 403, "message": "PERMISSION_DENIED"}}

                text = "PERMISSION_DENIED"

            raise gspread.exceptions.APIError(FakeResponse())

    monkeypatch.setattr(
        "racedbapp.view_art.gspread.service_account", lambda path: ErrorGC()
    )
    client = Client()
    response = client.get(
        "/art/",
        {
            "notifykey": NOTIFY_KEY,
            "art_folder_id": "folder-1",
            "art_distance": "5000",
            "google_sheets_url": "https://docs.google.com/spreadsheets/d/test-sheet",
        },
    )
    assert response.status_code == 200
