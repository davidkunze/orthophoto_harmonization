
from pathlib import Path
import subprocess

import geopandas as gpd
import numpy as np
import rasterio

from osgeo import gdal

from shapely.validation import make_valid

from ..vector.geometry import remove_inner_rings


def create_nodata_mask(
    input_raster,
    output_mask,
    nodata_value,
    block_size=1024,
):
    """
    Creates a raster mask identifying NoData pixels.

    A pixel is classified as NoData only if all raster bands
    contain the specified NoData value.

    Processing is performed block by block to reduce memory usage.
    """

    input_raster = Path(input_raster)
    output_mask = Path(output_mask)

    if block_size < 1:
        raise ValueError(
            "block_size must be greater than zero."
        )

    dataset = gdal.Open(str(input_raster))

    if dataset is None:
        raise RuntimeError(
            f"Cannot open raster: {input_raster}"
        )

    band_count = dataset.RasterCount

    if band_count < 1:
        dataset = None
        raise RuntimeError("Input raster contains no bands.")

    driver = gdal.GetDriverByName("GTiff")

    output_mask.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mask_dataset = driver.Create(
        str(output_mask),
        dataset.RasterXSize,
        dataset.RasterYSize,
        1,
        gdal.GDT_Byte,
        options=[
            "TILED=YES",
            "COMPRESS=DEFLATE",
        ],
    )

    if mask_dataset is None:
        dataset = None
        raise RuntimeError(
            f"Cannot create mask: {output_mask}"
        )

    mask_dataset.SetGeoTransform(
        dataset.GetGeoTransform()
    )

    mask_dataset.SetProjection(
        dataset.GetProjection()
    )

    try:
        for y in range(
            0,
            dataset.RasterYSize,
            block_size,
        ):
            rows = min(
                block_size,
                dataset.RasterYSize - y,
            )

            for x in range(
                0,
                dataset.RasterXSize,
                block_size,
            ):
                cols = min(
                    block_size,
                    dataset.RasterXSize - x,
                )

                band_masks = []

                for band_index in range(
                    1,
                    band_count + 1,
                ):
                    band = dataset.GetRasterBand(
                        band_index
                    )

                    array = band.ReadAsArray(
                        x,
                        y,
                        cols,
                        rows,
                    )

                    band_masks.append(
                        array == nodata_value
                    )

                mask = np.logical_and.reduce(
                    band_masks
                ).astype(np.uint8)

                mask_dataset.GetRasterBand(
                    1
                ).WriteArray(
                    mask,
                    x,
                    y,
                )

        mask_dataset.GetRasterBand(
            1
        ).SetNoDataValue(1)

    finally:
        mask_dataset = None
        dataset = None

    return output_mask


def create_nodata_cutline(
    mask_raster,
    output_cutline,
    avoid_holes=False,
):
    """
    Converts a NoData mask into a polygon cutline.

    GDAL contour is used to generate polygons.
    Invalid geometries are repaired.
    Inner rings can optionally be removed.
    """

    mask_raster = Path(mask_raster)
    output_cutline = Path(output_cutline)

    if not mask_raster.is_file():
        raise FileNotFoundError(mask_raster)

    output_cutline.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmd = [
        "gdal_contour",
        "-q",
        "-fl",
        "1",
        "-b",
        "1",
        "-f",
        "GPKG",
        "-p",
        str(mask_raster),
        str(output_cutline),
    ]

    subprocess.run(
        cmd,
        check=True,
    )

    if not output_cutline.is_file():
        raise RuntimeError(
            f"Cutline creation failed: {output_cutline}"
        )

    dataframe = gpd.read_file(
        output_cutline,
        layer="contour",
    )

    if dataframe.empty:
        return output_cutline

    dataframe["geometry"] = (
        dataframe.geometry.apply(
            lambda geometry: (
                make_valid(geometry)
                if geometry is not None
                else None
            )
        )
    )

    dataframe = dataframe[
        dataframe.geometry.notna()
        & ~dataframe.geometry.is_empty
    ].copy()

    if avoid_holes:
        dataframe["geometry"] = (
            dataframe.geometry.apply(
                remove_inner_rings
            )
        )

    dataframe.to_file(
        output_cutline,
        layer="contour",
        driver="GPKG",
        mode="w",
    )

    return output_cutline


def get_destination_nodata(
    input_raster,
    nodata_value=None,
):
    """
    Determines the destination NoData value.

    Uses the explicitly supplied value if available.
    Otherwise, the first band's NoData value is used.
    """

    input_raster = Path(input_raster)

    if nodata_value is not None:
        return nodata_value

    with rasterio.open(input_raster) as src:
        if src.nodata is not None:
            return src.nodata

    return 0


def clip_nodata(
    input_raster,
    output_raster,
    cutline,
    destination_nodata=None,
    crop_to_cutline=False,
    overwrite=True,
):
    """
    Clips a raster using a NoData cutline.

    The cutline is used as a GDAL mask.
    Pixels outside the valid geometry receive
    the destination NoData value.
    """

    input_raster = Path(input_raster)
    output_raster = Path(output_raster)
    cutline = Path(cutline)

    if not input_raster.is_file():
        raise FileNotFoundError(input_raster)

    if not cutline.is_file():
        raise FileNotFoundError(cutline)

    if output_raster.exists() and not overwrite:
        raise FileExistsError(output_raster)

    if destination_nodata is None:
        destination_nodata = get_destination_nodata(
            input_raster
        )

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmd = [
        "gdalwarp",
        "-overwrite",
        "-of",
        "GTiff",
        "-cutline",
        str(cutline),
        "-dstnodata",
        str(destination_nodata),
        "-multi",
        "-wo",
        "NUM_THREADS=ALL_CPUS",
    ]

    if crop_to_cutline:
        cmd.append("-crop_to_cutline")

    cmd.extend([
        str(input_raster),
        str(output_raster),
    ])

    subprocess.run(
        cmd,
        check=True,
    )

    if not output_raster.is_file():
        raise RuntimeError(
            f"NoData clipping failed: {output_raster}"
        )

    return output_raster
