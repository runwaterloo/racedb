import gspread
from gspread.exceptions import APIError


def get_sheet(gc, url):
    try:
        sh = gc.open_by_url(url)
        test_worksheet = sh.add_worksheet(
            title="race_test_worksheet_creation", rows=100, cols=20
        )
        sh.del_worksheet(test_worksheet)
    except APIError as e:
        sh = None
        status = str(e)
    else:
        status = 0
    return status, sh


def write(sh, results):
    # get the worksheet, clear if it already exists
    try:
        worksheet = sh.worksheet("individual")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title="individual", rows=0, cols=0, index=0)
    else:
        body = {
            "requests": [
                {
                    "updateCells": {
                        "range": {"sheetId": worksheet._properties["sheetId"]},
                        "fields": "*",
                    }
                }
            ]
        }
        sh.batch_update(body)

    # write out headings
    headings = [list(vars(results[0]))]
    sh.values_update(
        "individual!A1",
        params={"valueInputOption": "RAW"},
        body={"values": headings},
    )

    # freeze first row
    worksheet.freeze(rows=1)

    # format first row
    worksheet.format(
        "A1:{}1".format(chr(ord("@") + len(headings[0]))),
        {
            "backgroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0},
            "textFormat": {
                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                "bold": True,
            },
        },
    )

    # write out data
    results_data = []
    for r in results:
        values = list(vars(r).values())
        values = [str(x).strip() for x in values]
        results_data.append(values)
    sh.values_update(
        "individual!A2",
        params={"valueInputOption": "USER_ENTERED"},
        body={"values": results_data},
    )

    # figure out precision (how many decimals to show)
    precision = ""  # seconds
    guntimes_with_decimal = [x.guntime for x in results if "." in x.guntime]
    if guntimes_with_decimal:
        decimals = [x.split(".")[1].rstrip("0") for x in guntimes_with_decimal]
        max_length = max([len(x) for x in decimals])
        if max_length == 1:
            precision = ".0"  # tenths of seconds
        elif max_length == 2:
            precision = ".00"  # hundreths of seconds
        elif max_length == 3:
            precision = ".000"  # thousandth of seconds

    # show decimals correctly for guntime, chiptime (if present)
    gspread_sheet_id = worksheet._properties["sheetId"]
    cols_to_correct = []
    guntime_col = headings[0].index("guntime")
    cols_to_correct.append(guntime_col)
    if "chiptime" in headings[0]:
        chiptime_col = headings[0].index("chiptime")
        cols_to_correct.append(chiptime_col)
    for col in cols_to_correct:
        body = {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": gspread_sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": len(results) + 1,
                            "startColumnIndex": col,
                            "endColumnIndex": col + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE",
                                    "pattern": "h:mm:ss{}".format(precision),
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            ]
        }
        sh.batch_update(body)

    # resize columns
    gspread_sheet_id = worksheet._properties["sheetId"]
    body = {
        "requests": [
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": gspread_sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 25,
                    },
                }
            }
        ]
    }
    return sh.batch_update(body)
