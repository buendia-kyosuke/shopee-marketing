#!/usr/bin/env python3
"""Google Sheets integration for Shopee product research."""

import argparse
import csv
import json
import sys
from pathlib import Path

import gspread

CREDENTIALS_PATH = Path(__file__).parent / "credentials" / "gcp_service_account.json"
CONFIG_PATH = Path(__file__).parent / "sheets_config.json"


def get_client() -> gspread.Client:
    return gspread.service_account(filename=str(CREDENTIALS_PATH))


def get_spreadsheet_id() -> str:
    if not CONFIG_PATH.exists():
        print("ERROR: sheets_config.json not found. Run: python sheets.py init <spreadsheet_url>", file=sys.stderr)
        sys.exit(1)
    config = json.loads(CONFIG_PATH.read_text())
    return config["spreadsheet_id"]


def cmd_init(url: str):
    """Initialize config with spreadsheet URL."""
    spreadsheet_id = url.split("/d/")[1].split("/")[0]
    CONFIG_PATH.write_text(json.dumps({"spreadsheet_id": spreadsheet_id}, indent=2))
    print(f"Config saved. Spreadsheet ID: {spreadsheet_id}")

    # Verify connection
    client = get_client()
    sh = client.open_by_key(spreadsheet_id)
    print(f"Connected to: {sh.title}")


def cmd_write(csv_path: str, market: str):
    """Write CSV data to a market-specific sheet tab, with duplicate detection by ASIN."""
    client = get_client()
    sh = client.open_by_key(get_spreadsheet_id())

    # Read CSV
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("ERROR: CSV is empty", file=sys.stderr)
        sys.exit(1)

    headers = rows[0]
    data_rows = rows[1:]

    # Get or create worksheet for this market
    sheet_name = market.upper()
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
        worksheet.append_row(headers, value_input_option="USER_ENTERED")
        print(f"Created new sheet tab: {sheet_name}")

    # Get existing ASINs for duplicate check
    existing = worksheet.get_all_values()
    asin_col = None
    if existing:
        header_row = existing[0]
        for i, h in enumerate(header_row):
            if "ASIN" in h:
                asin_col = i
                break

    existing_asins = set()
    if asin_col is not None:
        for row in existing[1:]:
            if len(row) > asin_col and row[asin_col]:
                existing_asins.add(row[asin_col])

    # Find ASIN column in CSV
    csv_asin_col = None
    for i, h in enumerate(headers):
        if "ASIN" in h:
            csv_asin_col = i
            break

    # Append new rows, skip duplicates
    new_count = 0
    skip_count = 0
    for row in data_rows:
        if not any(cell.strip() for cell in row):
            continue
        asin = row[csv_asin_col] if csv_asin_col is not None and len(row) > csv_asin_col else None
        if asin and asin in existing_asins:
            print(f"SKIP (duplicate): {asin}")
            skip_count += 1
            continue
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        new_count += 1

    print(f"Done: {new_count} added, {skip_count} skipped (duplicate)")


def cmd_check(asin: str, market: str = None) -> bool:
    """Check if an ASIN already exists. Returns True if found."""
    client = get_client()
    sh = client.open_by_key(get_spreadsheet_id())

    sheets_to_check = []
    if market:
        try:
            sheets_to_check.append(sh.worksheet(market.upper()))
        except gspread.WorksheetNotFound:
            print(f"Sheet {market.upper()} not found")
            return False
    else:
        sheets_to_check = sh.worksheets()

    for ws in sheets_to_check:
        all_values = ws.get_all_values()
        if not all_values:
            continue
        header_row = all_values[0]
        asin_col = None
        for i, h in enumerate(header_row):
            if "ASIN" in h:
                asin_col = i
                break
        if asin_col is None:
            continue
        for row in all_values[1:]:
            if len(row) > asin_col and row[asin_col] == asin:
                print(f"FOUND: {asin} in sheet {ws.title}")
                return True

    print(f"NOT FOUND: {asin}")
    return False


def cmd_clear(market: str):
    """Clear all data in a market sheet (keeps header)."""
    client = get_client()
    sh = client.open_by_key(get_spreadsheet_id())
    try:
        ws = sh.worksheet(market.upper())
    except gspread.WorksheetNotFound:
        print(f"Sheet {market.upper()} not found")
        return
    all_values = ws.get_all_values()
    if len(all_values) > 1:
        ws.delete_rows(2, len(all_values))
        print(f"Cleared {len(all_values) - 1} rows from {market.upper()}")
    # Also clear header so write can re-create it with new columns
    ws.clear()
    print(f"Sheet {market.upper()} cleared completely")


def cmd_list(market: str):
    """List all ASINs in a market sheet."""
    client = get_client()
    sh = client.open_by_key(get_spreadsheet_id())
    try:
        ws = sh.worksheet(market.upper())
    except gspread.WorksheetNotFound:
        print(f"Sheet {market.upper()} not found")
        return

    all_values = ws.get_all_values()
    if not all_values:
        return

    header_row = all_values[0]
    asin_col = None
    name_col = None
    for i, h in enumerate(header_row):
        if "ASIN" in h:
            asin_col = i
        if "商品名" in h:
            name_col = i

    for row in all_values[1:]:
        if not any(cell.strip() for cell in row):
            continue
        asin = row[asin_col] if asin_col is not None and len(row) > asin_col else "?"
        name = row[name_col] if name_col is not None and len(row) > name_col else "?"
        print(f"{asin}\t{name}")


def main():
    parser = argparse.ArgumentParser(description="Shopee research Google Sheets tool")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Initialize with spreadsheet URL")
    p_init.add_argument("url", help="Google Sheets URL")

    p_write = sub.add_parser("write", help="Write CSV to sheet")
    p_write.add_argument("csv_path", help="Path to CSV file")
    p_write.add_argument("--market", required=True, help="Market code (SG, PH, etc.)")

    p_check = sub.add_parser("check", help="Check if ASIN exists")
    p_check.add_argument("asin", help="ASIN to check")
    p_check.add_argument("--market", help="Limit to specific market")

    p_clear = sub.add_parser("clear", help="Clear a market sheet")
    p_clear.add_argument("market", help="Market code (SG, PH, etc.)")

    p_list = sub.add_parser("list", help="List ASINs in a market sheet")
    p_list.add_argument("market", help="Market code (SG, PH, etc.)")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args.url)
    elif args.command == "write":
        cmd_write(args.csv_path, args.market)
    elif args.command == "clear":
        cmd_clear(args.market)
    elif args.command == "check":
        cmd_check(args.asin, args.market)
    elif args.command == "list":
        cmd_list(args.market)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
