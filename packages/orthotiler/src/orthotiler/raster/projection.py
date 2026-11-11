
from pathlib import Path
import subprocess

from osgeo import gdal, osr


def get_raster_srs(raster_path):
    """
    Determines the EPSG code of a raster dataset.

    Parameters
    ----------
    raster_path : str or Path
        Input raster path.

    Returns
    -------
    int or None
        Detected EPSG code, or None if unavailable.
    """

    dataset = gdal.Open(str(raster_path))

    if dataset is None:
        raise RuntimeError(
            f"Cannot open raster: {raster_path}"
        )

    projection = dataset.GetProjection()

    if not projection:
        dataset = None
        return None

    spatial_ref = osr.SpatialReference(
        wkt=projection
    )

    spatial_ref.AutoIdentifyEPSG()

    authority = spatial_ref.GetAuthorityCode(None)

    if authority is None:
        dataset = None
        return None

    dataset = None

    return int(authority)


def reproject_raster(
    input_raster,
    output_raster,
    output_srs=25832,
    input_srs=None,
    fallback_srs=None,
    resampling="near",
    overwrite=True,
):
    """
    Reprojects a raster dataset using GDAL.

    Special handling is provided for EPSG:4314 and EPSG:9122.

    Parameters
    ----------
    input_raster : str or Path
        Input raster or VRT.

    output_raster : str or Path
        Output raster or VRT.

    output_srs : int
        Target EPSG code.

    input_srs : int or None
        Optional explicitly defined input EPSG code.

    fallback_srs : int or None
        CRS used if the input dataset has no identifiable CRS.

    resampling : str
        GDAL resampling algorithm.

    overwrite : bool
        Overwrites an existing output.

    Returns
    -------
    dict
        Reprojection information.
    """

    input_raster = Path(input_raster)
    output_raster = Path(output_raster)

    if not input_raster.is_file():
        raise FileNotFoundError(input_raster)

    if output_raster.exists() and not overwrite:
        raise FileExistsError(output_raster)

    output_raster.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Determine the input CRS
    detected_srs = get_raster_srs(
        input_raster
    )

    warning = ""

    if detected_srs is None:

        if fallback_srs is None and input_srs is None:
            raise ValueError(
                "Input CRS could not be identified. "
                "Please specify input_srs or fallback_srs."
            )

        source_srs = (
            input_srs
            if input_srs is not None
            else fallback_srs
        )

        warning = (
            "WARNING: The input dataset has no identifiable CRS. "
            "The manually specified CRS will be used. "
            "Please verify the spatial alignment of the output."
        )

    else:
        source_srs = (
            input_srs
            if input_srs is not None
            else detected_srs
        )

    # Apply the original special CRS handling
    if source_srs in (4314, 9122):

        source_srs = 31467

        warning += (
            "\nWARNING: EPSG:4314 or EPSG:9122 detected. "
            "EPSG:31467 is used as the source CRS "
            "according to the original processing workflow."
        )

    # Skip reprojection if source and target CRS are identical
    if source_srs == output_srs:

        return {
            "reprojected": False,
            "input_srs": detected_srs,
            "source_srs": source_srs,
            "output_srs": output_srs,
            "output_path": input_raster,
            "warning": warning,
        }

    # Build the GDAL command
    cmd = [
        "gdalwarp",
        "-overwrite",
        "-of",
        "VRT",
        "-s_srs",
        f"EPSG:{source_srs}",
        "-t_srs",
        f"EPSG:{output_srs}",
        "-r",
        resampling,
        str(input_raster),
        str(output_raster),
    ]

    subprocess.run(
        cmd,
        check=True,
    )

    if not output_raster.exists():
        raise RuntimeError(
            f"Reprojection failed: {output_raster}"
        )

    return {
        "reprojected": True,
        "input_srs": detected_srs,
        "source_srs": source_srs,
        "output_srs": output_srs,
        "output_path": output_raster,
        "warning": warning,
    }


def reproject_vector(
    input_vector,
    output_vector,
    output_srs=25832,
    input_srs=None,
    layer=None,
    overwrite=True,
):
    """
    Reprojects a vector dataset using ogr2ogr.

    Parameters
    ----------
    input_vector : str or Path
        Input vector dataset.

    output_vector : str or Path
        Output GeoPackage.

    output_srs : int
        Target EPSG code.

    input_srs : int or None
        Optional explicitly defined input EPSG code.

    layer : str or None
        Input layer name.

    overwrite : bool
        Overwrites an existing output.

    Returns
    -------
    Path
        Path to the output GeoPackage.
    """

    input_vector = Path(input_vector)
    output_vector = Path(output_vector)

    if not input_vector.is_file():
        raise FileNotFoundError(input_vector)

    if output_vector.exists() and not overwrite:
        raise FileExistsError(output_vector)

    output_vector.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmd = [
        "ogr2ogr",
        "-f",
        "GPKG",
    ]

    if overwrite:
        cmd.append("-overwrite")

    if input_srs is not None:
        cmd.extend([
            "-s_srs",
            f"EPSG:{input_srs}",
        ])

    cmd.extend([
        "-t_srs",
        f"EPSG:{output_srs}",
        str(output_vector),
        str(input_vector),
    ])

    if layer:
        cmd.append(layer)

    subprocess.run(
        cmd,
        check=True,
    )

    if not output_vector.exists():
        raise RuntimeError(
            f"Vector reprojection failed: {output_vector}"
        )

    return output_vector
