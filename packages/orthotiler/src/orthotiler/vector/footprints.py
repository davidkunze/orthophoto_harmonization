
from pathlib import Path

import geopandas as gpd
import pandas as pd

from shapely.geometry import MultiPolygon


def create_tile_footprint(
    raster_path,
    output_path,
    simplify=True,
    deg_tol=1,
):
    """
    Creates a polygon footprint from a raster tile.

    Parameters
    ----------
    raster_path : str or Path
        Input raster.

    output_path : str or Path
        Output GeoPackage.

    simplify : bool
        Applies angle-based geometry simplification.

    deg_tol : float
        Angular simplification tolerance.

    Returns
    -------
    Path
        Output footprint path.
    """

    import subprocess

    from .geometry import simplify_by_angle

    raster_path = Path(raster_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmd = [
        "gdal_contour",
        "-q",
        "-fl",
        "0",
        "-b",
        "1",
        "-f",
        "GPKG",
        "-p",
        str(raster_path),
        str(output_path),
    ]

    subprocess.run(
        cmd,
        check=True,
    )

    dataframe = gpd.read_file(
        output_path,
        layer="contour",
    )

    if simplify:

        simplified_geometries = []

        for geometry in dataframe.geometry:

            if isinstance(geometry, MultiPolygon):

                simplified = MultiPolygon([
                    simplify_by_angle(
                        polygon,
                        deg_tol=deg_tol,
                    )
                    for polygon in geometry.geoms
                ])

            else:

                simplified = simplify_by_angle(
                    geometry,
                    deg_tol=deg_tol,
                )

            simplified_geometries.append(
                simplified
            )

        dataframe["geometry"] = simplified_geometries

        dataframe.to_file(
            output_path,
            layer="contour",
            driver="GPKG",
            mode="w",
        )

    return output_path


def merge_tile_footprints(
    footprint_files,
    output_path,
    output_layer="footprint_outline",
):
    """
    Merges individual tile footprints into one GeoPackage layer.

    Empty footprints are ignored.
    """

    output_path = Path(output_path)

    dataframes = []

    for file in footprint_files:

        file = Path(file)

        if not file.exists():
            continue

        dataframe = gpd.read_file(
            file,
            layer="contour",
        )

        if dataframe.empty:
            continue

        dataframes.append(dataframe)

    if not dataframes:
        raise RuntimeError(
            "No valid tile footprints found."
        )

    merged = gpd.GeoDataFrame(
        pd.concat(
            dataframes,
            ignore_index=True,
        ),
        crs=dataframes[0].crs,
    )

    merged["geometry"] = (
        merged.geometry.make_valid()
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    merged.to_file(
        output_path,
        layer=output_layer,
        driver="GPKG",
    )

    return merged


def create_dataset_outline(
    footprint_dataframe,
    output_path,
    output_layer="outline",
    group_by=None,
):
    """
    Dissolves tile footprints into a dataset outline.

    Parameters
    ----------
    footprint_dataframe : GeoDataFrame
        Merged tile footprints.

    output_path : str or Path
        Output GeoPackage.

    output_layer : str
        Output layer name.

    group_by : str or None
        Optional grouping column.
    """

    output_path = Path(output_path)

    if group_by and group_by in footprint_dataframe.columns:

        outline = footprint_dataframe.dissolve(
            by=group_by
        )

    else:

        outline = footprint_dataframe.dissolve()

    outline["geometry"] = (
        outline.geometry.make_valid()
    )

    outline.to_file(
        output_path,
        layer=output_layer,
        driver="GPKG",
    )

    return outline
