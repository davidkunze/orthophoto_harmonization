
from pathlib import Path

from .cog import create_cog


def process_tile(
    input_vrt,
    tile,
    output_dir,
    output_srs=25832,
    compression="ZSTD",
    predictor=2,
    bigtiff="YES",
    overview_resampling="average",
    overwrite=False,
):
    """
    Creates one COG tile.

    Parameters
    ----------
    input_vrt : str or Path
        Input raster VRT.

    tile : Tile
        Tile geometry and boundaries.

    output_dir : str or Path
        Output directory.

    Returns
    -------
    dict
        Processing result.
    """

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / f"tile_{tile.name_suffix}.tif"
    )

    try:

        create_cog(
            input_raster=input_vrt,
            output_raster=output_file,
            tile=tile,
            output_srs=output_srs,
            compression=compression,
            predictor=predictor,
            bigtiff=bigtiff,
            overview_resampling=overview_resampling,
            overwrite=overwrite,
        )

        return {
            "success": True,
            "tile": tile.name_suffix,
            "path": output_file,
            "error": None,
        }

    except Exception as error:

        return {
            "success": False,
            "tile": tile.name_suffix,
            "path": None,
            "error": str(error),
        }
