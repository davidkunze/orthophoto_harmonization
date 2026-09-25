from pathlib import Path
import xml.etree.ElementTree as ET
import geopandas as gpd
import pandas as pd
import os 

XML_DIR = Path(r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\doku\metadaten")
INPUT_GPKG = Path(r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\doku\2025.gpkg")
INPUT_LAYER = "lglnopengeodatadop20rgbi"
OUTPUT_GPKG = Path(r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\doku\2025.gpkg")
OUTPUT_LAYER = "tiles_metadata"
KEY = "kachelname"

records = []
for f in XML_DIR.glob("*.xml"):
    root = ET.parse(f).getroot()
    data = {e.tag: e.text for e in root}
    data.setdefault("kachelname", f.stem)
    records.append(data)

xml_df = pd.DataFrame(records)
gdf = gpd.read_file(INPUT_GPKG, layer=INPUT_LAYER)
gdf[KEY] = gdf["rgbi"].apply(lambda x: os.path.basename(x)[:-4])

if KEY not in gdf.columns:
    raise ValueError(f"Column '{KEY}' not found in GeoPackage.")

gdf[KEY] = gdf[KEY].astype(str).str.strip()
xml_df[KEY] = xml_df[KEY].astype(str).str.strip()

xml_df = xml_df.rename(columns={c: f"xml_{c}" for c in xml_df.columns if c != KEY and c in gdf.columns})

gdf = gdf.merge(xml_df, on=KEY, how="left")

def make_unique_columns(columns):
    counts = {}
    result = []

    for col in columns:
        if col not in counts:
            counts[col] = 0
            result.append(col)
        else:
            counts[col] += 1
            result.append(f"{col}_{counts[col]}")

    return result


gdf.columns = make_unique_columns(gdf.columns)


gdf.to_file(OUTPUT_GPKG, layer=OUTPUT_LAYER, driver="GPKG")

print(f"Done: {len(gdf)} features written to {OUTPUT_GPKG}")
