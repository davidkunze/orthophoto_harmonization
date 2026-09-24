from pathlib import Path
import xml.etree.ElementTree as ET
import geopandas as gpd
import pandas as pd

XML_DIR = Path(r"C:\GIS\XML")
INPUT_GPKG = Path(r"C:\GIS\tiles.gpkg")
INPUT_LAYER = "tiles"
OUTPUT_GPKG = Path(r"C:\GIS\tiles_metadata.gpkg")
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

if KEY not in gdf.columns:
    raise ValueError(f"Column '{KEY}' not found in GeoPackage.")

gdf[KEY] = gdf[KEY].astype(str).str.strip()
xml_df[KEY] = xml_df[KEY].astype(str).str.strip()

xml_df = xml_df.rename(columns={c: f"xml_{c}" for c in xml_df.columns if c != KEY and c in gdf.columns})

gdf = gdf.merge(xml_df, on=KEY, how="left")

gdf.to_file(OUTPUT_GPKG, layer=OUTPUT_LAYER, driver="GPKG")

print(f"Done: {len(gdf)} features written to {OUTPUT_GPKG}")
