import geopandas as gpd
import pandas as pd
import fiona
from pathlib import Path

INPUT_1 = Path(r"\\lb-srv\fern_2\luftbild\he\flugzeug\2023\he_lverm\tdop\doku\Metadaten_2023.gpkg")
INPUT_2 = Path(r"\\lb-srv\fern_2\luftbild\he\flugzeug\2023\he_lverm\tdop\daten\kacheluebersicht\he_flugzeug_2023_he_lverm_tdop_extent.gpkg")

DATE_FIELD = "Aktualitaet"
DATE_FROM_FIELD = "datum_bildflug_von"
DATE_TO_FIELD = "datum_bildflug_bis"

input1_layer = fiona.listlayers(INPUT_1)[0]
input2_layers = fiona.listlayers(INPUT_2)

gdf_1 = gpd.read_file(INPUT_1, layer=input1_layer)
gdf_1[DATE_FIELD] = pd.to_datetime(gdf_1[DATE_FIELD], errors="coerce")
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

    overlap = gpd.sjoin(
        gdf_2[["_input2_id", "geometry"]],
        gdf_1_work[[DATE_FIELD, "geometry"]],
        how="left",
        predicate="overlaps"
    )

    aggregation = (
        overlap.groupby("_input2_id")[DATE_FIELD]
        .agg(date_from="min", date_to="max")
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

    gdf_2 = gdf_2.drop(columns="_input2_id")

    gdf_2[DATE_FROM_FIELD] = gdf_2[DATE_FROM_FIELD].astype(str)
    gdf_2[DATE_TO_FIELD] = gdf_2[DATE_TO_FIELD].astype(str)

    gdf_2.to_file(
        INPUT_2,
        layer=layer_name,
        driver="GPKG",
        mode="w"
    )
