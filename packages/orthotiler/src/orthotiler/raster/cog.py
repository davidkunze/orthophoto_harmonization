
from pathlib import Path
import subprocess
import math

from osgeo import gdal


def calculate_tile_resolution(
    tile_size,
    x_res,
    y_res,
):
    """
    Adjusts the pixel resolution to fit the tile dimensions.

    This prevents gaps or overlaps between adjacent tiles
    when the tile size is not an integer multiple of
    the original pixel resolution.

    Returns
    -------
    tuple
        Adjusted x resolution, y resolution and resampling method.
    """

    cell_count_x = tile_size[0] / x_res
    cell_count_y = tile_size[1] / y_res

    resampling = "nearest"

    if (
        not cell_count_x.is_integer()
        or not cell_count_y.is_integer()
    ):

        # Calculate the adjusted pixel resolution
        pixels_x = max(1, math.floor(cell_count_x))
        pixels_y = max(1, math.floor(cell_count_y))

        x_remainder = (
            tile_size[0] - pixels_x * x_res
        )

        y_remainder = (
            tile_size[1] - pixels_y * y_res
        )

        x_res = (
            x_res + x_remainder / pixels_x
        )

        y_res = (
            y_res + y_remainder / pixels_y
        )

        resampling = "rms"

    return x_res, y_res, resampling


def create_cog(
    input_raster,
    output_raster,
    tile,
    output_srs=25832,
    bands=None,
    compression="ZSTD",
    predictor=2,
    bigtiff="YES",
    overview_resampling="average",
    overwrite=False,
    creation_options=None,
):
    """
    Creates a Cloud Optimized GeoTIFF from a raster tile.

    Parameters
    ----------
    input_raster : str or Path
        Input raster or VRT.

    output_raster : str or Path
        Output COG path.

    tile : Tile
        Tile geometry and boundaries.

    output_srs : int
        Target EPSG code.

    bands : tuple or list or None
        Raster bands to include.
        If None, all bands are used.

    compression : str
        TIFF compression algorithm.

    predictor : int
        TIFF predictor.

    bigtiff : str
        BigTIFF setting.

    overview_resampling : str
        Overview resampling method.

    overwrite : bool
        Overwrites an existing COG.

    creation_options : list or None
        Additional GDAL creation options.

    Returns
    -------
    Path
        Path to the generated COG.
    """

    input_raster = Path(input_raster)
    output_raster = Path(output_raster)

    if not input_raster.is_file():
        raise FileNotFoundError(input_raster)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if output_raster.exists() and not overwrite:
        return output_raster

    dataset = gdal.Open(str(input_raster))

    if dataset is None:
        raise RuntimeError(
            f"Cannot open input raster: {input_raster}"
        )

    transform = dataset.GetGeoTransform()

    x_res = abs(transform[1])
    y_res = abs(transform[5])

    if bands is None:
        bands = tuple(
            range(1, dataset.RasterCount + 1)
        )

    if not bands:
        raise ValueError(
            "No raster bands selected."
        )

    if any(
        band < 1 or band > dataset.RasterCount
        for band in bands
    ):
        raise ValueError(
            "Invalid raster band selection."
        )

    dataset = None

    # Calculate tile-specific pixel resolution
    x_res, y_res, resampling = calculate_tile_resolution(
        tile_size=(
            tile.xmax - tile.xmin,
            tile.ymax - tile.ymin,
        ),
        x_res=x_res,
        y_res=y_res,
    )

    # Build GDAL command
    cmd = [
        "gdal_translate",
        "-q",
        "-of",
        "COG",
        "-co",
        f"COMPRESS={compression}",
        "-co",
        f"PREDICTOR={predictor}",
        "-co",
        f"BIGTIFF={bigtiff}",
        "-co",
        f"OVERVIEW_COMPRESS={compression}",
        "-co",
        f"OVERVIEW_PREDICTOR={predictor}",
        "-co",
        f"OVERVIEW_RESAMPLING={overview_resampling}",
        "-co",
        "OVERVIEWS=IGNORE_EXISTING",
        "--config",
        "GDAL_TIFF_INTERNAL_MASK",
        "YES",
        "-r",
        resampling,
        "-a_srs",
        f"EPSG:{output_srs}",
    ]

    for band in bands:
        cmd.extend([
            "-b",
            str(band),
        ])

    cmd.extend([
        "-tr",
        str(x_res),
        str(y_res),
        "-projwin",
        str(tile.xmin),
        str(tile.ymax),
        str(tile.xmax),
        str(tile.ymin),
    ])

    if creation_options:
        for option in creation_options:
            cmd.extend([
                "-co",
                str(option),
            ])

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
            f"COG creation failed: {output_raster}"
        )

    return output_raster


def validate_cog(
    raster_path,
    strict=True,
):
    """
    Validates a Cloud Optimized GeoTIFF using GDAL.

    Parameters
    ----------
    raster_path : str or Path
        COG file to validate.

    strict : bool
        Enables strict validation.

    Returns
    -------
    bool
        True if validation succeeds.
    """

    raster_path = Path(raster_path)

    if not raster_path.is_file():
        raise FileNotFoundError(raster_path)

    cmd = [
        "gdal",
        "driver",
        "cog",
        "validate",
    ]

    if strict:
        cmd.append("--full-check")

    cmd.append(str(raster_path))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"COG validation failed:\n{result.stderr}"
        )

    return True
