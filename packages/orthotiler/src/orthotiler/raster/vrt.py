from pathlib import Path
import subprocess
import tempfile


def build_vrt(
    input_files,
    output_vrt,
    bands=None,
    nodata_value=None,
    allow_projection_difference=True,
    overwrite=True,
):
    """
    Creates a VRT from multiple raster datasets.

    Parameters
    ----------
    input_files : list
        List of input raster files.

    output_vrt : str or Path
        Output VRT path.

    bands : tuple or list or None
        Raster bands to include.
        Example: (1, 2, 3, 4)

    nodata_value : str, int, float or None
        Optional source NoData value.
        The same value is applied to all selected bands.

    allow_projection_difference : bool
        Allows input datasets with different projections.

    overwrite : bool
        Overwrites an existing VRT.

    Returns
    -------
    Path
        Path to the generated VRT.
    """

    input_files = [
        Path(path).resolve()
        for path in input_files
    ]

    output_vrt = Path(output_vrt)

    if not input_files:
        raise ValueError(
            "No input files provided."
        )

    missing_files = [
        path for path in input_files
        if not path.is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            f"Input files not found: {missing_files[:5]}"
        )

    output_vrt.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if output_vrt.exists() and not overwrite:
        raise FileExistsError(output_vrt)

    cmd = [
        "gdalbuildvrt",
    ]

    if overwrite:
        cmd.append("-overwrite")

    if allow_projection_difference:
        cmd.append("-allow_projection_difference")

    if bands:
        for band in bands:
            cmd.extend([
                "-b",
                str(band),
            ])

    if nodata_value is not None:

        band_count = len(bands) if bands else 1

        nodata_values = " ".join(
            [str(nodata_value)] * band_count
        )

        cmd.extend([
            "-srcnodata",
            nodata_values,
        ])

    # Create a temporary input file list
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        encoding="utf-8",
        delete=False,
    ) as file:

        input_list = Path(file.name)

        for path in input_files:

            file.write(
                f"{path.as_posix()}\n"
            )

    try:

        cmd.extend([
            "-input_file_list",
            str(input_list),
            str(output_vrt),
        ])

        subprocess.run(
            cmd,
            check=True,
        )

    finally:

        input_list.unlink(
            missing_ok=True
        )

    if not output_vrt.exists():
        raise RuntimeError(
            f"VRT creation failed: {output_vrt}"
        )

    return output_vrt


def get_raster_info(raster_path):
    """
    Reads basic raster information using GDAL.

    Parameters
    ----------
    raster_path : str or Path
        Path to the raster dataset.

    Returns
    -------
    dict
        Raster metadata including dimensions,
        band count, data type, CRS and bounds.
    """

    from osgeo import gdal

    dataset = gdal.Open(str(raster_path))

    if dataset is None:
        raise RuntimeError(
            f"Cannot open raster: {raster_path}"
        )

    transform = dataset.GetGeoTransform()

    info = {
        "width": dataset.RasterXSize,
        "height": dataset.RasterYSize,
        "bands": dataset.RasterCount,
        "datatype": gdal.GetDataTypeName(
            dataset.GetRasterBand(1).DataType
        ),
        "geotransform": transform,
        "projection": dataset.GetProjection(),
        "bounds": (
            transform[0],
            transform[3] + dataset.RasterYSize * transform[5],
            transform[0] + dataset.RasterXSize * transform[1],
            transform[3],
        ),
        "resolution": (
            abs(transform[1]),
            abs(transform[5]),
        ),
    }

    dataset = None

    return info