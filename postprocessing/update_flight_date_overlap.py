import os

import geopandas as gpd
import pandas as pd
import fiona
from pathlib import Path

INPUT_1 = Path(r"\\lb-srv\fern_2\luftbild\he\flugzeug\2024\he_lverm\tdop\doku\metadaten.gpkg")
INPUT_2 = Path(r"\\lb-srv\fern_2\luftbild\he\flugzeug\2024\he_lverm\tdop\daten\kacheluebersicht\he_flugzeug_2024_he_lverm_tdop_extent.gpkg")
# INPUT_2 = Path(r"\\lb-srv\fern_2\luftbild\he\flugzeug\2024\he_lverm\tdop\daten\kacheluebersicht\test.gpkg")


DATE_FIELD = "Metadaten_DOP_Juni-2026_Bildflugdatum"
DATE_FROM_FIELD = "datum_bildflug_von"
DATE_TO_FIELD = "datum_bildflug_bis"
date_format = "%d.%m.%Y"
PIXELSIZE_FIELD_gdf_1 = "bodenpixelgroesse_x"
PIXELSIZE_FIELD_gdf_2 = "original_raeumliche_aufloesung_cm"

fill_pixelsize = False  # Set to True if you want to fill the pixelsize field, False otherwise

input1_layer = fiona.listlayers(INPUT_1)[3]
input2_layers = fiona.listlayers(INPUT_2)


gdf_1 = gpd.read_file(INPUT_1, layer=input1_layer)
gdf_1[DATE_FIELD] = pd.to_datetime(gdf_1[DATE_FIELD],format=date_format, errors="coerce")
gdf_1 = gdf_1.dropna(subset=[DATE_FIELD]).copy()

for layer_name in input2_layers:
    gdf_2 = gpd.read_file(INPUT_2, layer=layer_name)

    old_date_from = gdf_2[DATE_FROM_FIELD].copy()
    old_date_to = gdf_2[DATE_TO_FIELD].copy()

    if gdf_1.crs != gdf_2.crs:
        gdf_1_work = gdf_1.to_crs(gdf_2.crs)
    else:
        gdf_1_work = gdf_1

    gdf_2 = gdf_2.reset_index(drop=True)
    gdf_2["_input2_id"] = gdf_2.index


    if fill_pixelsize:
        overlap = gpd.sjoin(
                gdf_2[["_input2_id", "geometry"]],
                gdf_1_work[[DATE_FIELD, PIXELSIZE_FIELD_gdf_1, "geometry"]],
                how="left",
                predicate="contains"
            )
        
        aggregation = (
            overlap.groupby("_input2_id")
            .agg(
                date_from=(DATE_FIELD, "min"),
                date_to=(DATE_FIELD, "max"),
                pixelsize=(PIXELSIZE_FIELD_gdf_1, "max")
            )
        )
        
    else:
        overlap = gpd.sjoin(
                gdf_2[["_input2_id", "geometry"]],
                gdf_1_work[[DATE_FIELD, "geometry"]],
                how="left",
                predicate="contains"
            )
        aggregation = (
            overlap.groupby("_input2_id")
            .agg(
                date_from=(DATE_FIELD, "min"),
                date_to=(DATE_FIELD, "max")
            )
        )
    
     
    gdf_2[DATE_FROM_FIELD] = gdf_2["_input2_id"].map(aggregation["date_from"])
    gdf_2[DATE_TO_FIELD] = gdf_2["_input2_id"].map(aggregation["date_to"])

    gdf_2[DATE_FROM_FIELD] = gdf_2[DATE_FROM_FIELD].where(
        gdf_2[DATE_FROM_FIELD].notna(),
        old_date_from
    )
    gdf_2[DATE_TO_FIELD] = gdf_2[DATE_TO_FIELD].where(
        gdf_2[DATE_TO_FIELD].notna(),
        old_date_to
    )

    if fill_pixelsize:

        gdf_2[PIXELSIZE_FIELD_gdf_2] = gdf_2["_input2_id"].map(
            aggregation["pixelsize"]
        )

        # Alten Wert behalten, wenn keine Überlappung gefunden wurde
        gdf_2[PIXELSIZE_FIELD_gdf_2] = gdf_2[PIXELSIZE_FIELD_gdf_2].where(
            gdf_2[PIXELSIZE_FIELD_gdf_2].notna(),
            PIXELSIZE_FIELD_gdf_2
        )

    gdf_2 = gdf_2.drop(columns="_input2_id")

    gdf_2[DATE_FROM_FIELD] = gdf_2[DATE_FROM_FIELD].astype(str)
    gdf_2[DATE_TO_FIELD] = gdf_2[DATE_TO_FIELD].astype(str)


    TEMP_OUTPUT = INPUT_2.with_name("temporary_output.gpkg")
    
    gdf_2.to_file(
        TEMP_OUTPUT,
        layer=layer_name,
        driver="GPKG",
        mode="w",
        engine="fiona",
    )

# replace the original file with the temporary output
fiona.remove(INPUT_2, driver="GPKG")
os.replace(TEMP_OUTPUT, INPUT_2)