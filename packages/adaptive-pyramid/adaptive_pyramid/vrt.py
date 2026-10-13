from pathlib import Path
import subprocess
import tempfile


def build_vrt(
    cog_folder,
    output_vrt,
    recursive=True
):


    cog_folder = Path(cog_folder)
    output_vrt = Path(output_vrt)

    files = list(
        cog_folder.rglob("*.tif")
        if recursive
        else cog_folder.glob("*.tif")
    )

    if not files:
        raise RuntimeError(
            "No COGs found"
        )

    # Create a temporary file containing the input file paths.
    # delete=False is required so GDAL can access the file.
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        encoding="utf-8",
        delete=False
    ) as file:

        input_list_txt = Path(file.name)

        for path in files:
            file.write(f"{path.resolve()}\n")

    try:
        cmd = [
            "gdalbuildvrt",
            "-overwrite",
            "-input_file_list",
            str(input_list_txt),
            str(output_vrt),
        ]

        subprocess.run(
            cmd,
            check=True
        )

    finally:
        # Always remove the temporary input file,
        # even if gdalbuildvrt fails.
        input_list_txt.unlink(missing_ok=True)


def build_overviews(
    vrt,
    levels,
    resampling="average",
    workers=8
):
    """
    Creates VRT overviews (.ovr).
    """

    if not levels:
        return

    cmd = [
        "gdaladdo",
        "-r",
        resampling,
        "--config",
        "GDAL_NUM_THREADS",
        str(workers),
        str(vrt)
    ]

    cmd.extend(
        [
            str(x)
            for x in levels
        ]
    )

    subprocess.run(
        cmd,
        check=True
    )