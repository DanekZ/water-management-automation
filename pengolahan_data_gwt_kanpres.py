
import os
import json
import pandas as pd
import gspread

from google.oauth2.service_account import Credentials


# ==========================================
# 1. GOOGLE AUTHENTICATION
# ==========================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials_info = json.loads(
    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
)

credentials = Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

gc = gspread.authorize(credentials)


# ==========================================
# 2. READ GOOGLE SPREADSHEET
# ==========================================

spreadsheet_url = os.environ["SPREADSHEET_URL"]

spreadsheet = gc.open_by_url(spreadsheet_url)

worksheet = spreadsheet.worksheet("kanpres_gwt_table")

data = worksheet.get_all_records()

df = pd.DataFrame(data)

print(f"Jumlah data mentah: {len(df)}")


# ==========================================
# 3. DATA TRANSFORMATION
# ==========================================

# Mengubah struktur wide menjadi long
data_long = pd.wide_to_long(
    df,
    stubnames=["persentase_gwt", "volume_gwt"],
    i="Tanggal",
    j="Tangki",
    sep="_",
    suffix=".+"
).reset_index()


# Mengubah tanggal menjadi datetime
data_long["Tanggal"] = pd.to_datetime(
    data_long["Tanggal"],
    dayfirst=True,
    errors="coerce"
)

# Konversi persentase menjadi numerik
data_long["persentase"] = (
    data_long["persentase_gwt"]
    .astype(str)
    .str.replace("%", "", regex=False)
    .str.replace(",", ".", regex=False)
)

data_long["persentase"] = pd.to_numeric(
    data_long["persentase"],
    errors="coerce"
)


# Konversi volume menjadi numerik
data_long["volume"] = (
    data_long["volume_gwt"]
    .astype(str)
    .str.replace(" m³", "", regex=False)
    .str.replace(",", ".", regex=False)
)

data_long["volume"] = pd.to_numeric(
    data_long["volume"],
    errors="coerce"
)


# Mengurutkan data berdasarkan tanggal asli
data_long = data_long.sort_values(
    ["Tanggal", "Tangki"]
).reset_index(drop=True)


# Mengubah tanggal menjadi format tampilan
data_long["Tanggal"] = data_long["Tanggal"].dt.strftime(
    "%m/%d/%Y"
)


# Memilih kolom output
data_long = data_long[
    ["Tanggal", "Tangki", "persentase", "volume", "Latest Record"]
]

print(f"Jumlah data hasil transformasi: {len(data_long)}")


# ==========================================
# 4. WRITE TO GOOGLE SPREADSHEET
# ==========================================

sheet_name = "result_gwt_data"

try:
    result_sheet = spreadsheet.worksheet(sheet_name)

except gspread.WorksheetNotFound:
    result_sheet = spreadsheet.add_worksheet(
        title=sheet_name,
        rows=max(1000, len(data_long) + 1),
        cols=len(data_long.columns)
    )


# Menyiapkan data untuk Google Sheets
output_df = data_long.astype(object).where(
    pd.notna(data_long), ""
)

output = [
    output_df.columns.tolist()
] + output_df.values.tolist()


# Memperbarui ukuran sheet jika diperlukan
result_sheet.resize(
    rows=max(1, len(output)),
    cols=len(data_long.columns)
)

# Menghapus data lama
result_sheet.clear()

# Menulis data terbaru
result_sheet.update(
    values=output,
    range_name="A1"
)

print("Data berhasil diperbarui!")
