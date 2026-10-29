from pathlib import Path
import subprocess
import tempfile


def build_vrt(
    cog_folder,
    output_vrt,
    recursive=True,
    gdal_options=None,
):
    cog_folder = Path(cog_folder)
    output_vrt = Path(output_vrt)

    files = sorted(
        cog_folder.rglob("*.tif")
        if recursive
        else cog_folder.glob("*.tif")
    )

    if not files:
        raise RuntimeError("No COGs found")

    output_vrt.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Temporäre Liste der Eingabedateien erstellen
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        encoding="utf-8",
        delete=False,
    ) as file:
        input_list_txt = Path(file.name)

        for path in files:
            file.write(f"{path.resolve()}\n")

    try:
        cmd = [
            "gdalbuildvrt",
            "-overwrite",
        ]

        # Zusätzliche GDAL-Optionen übernehmen
        if gdal_options:
            cmd.extend(
                [str(option) for option in gdal_options]
            )

        # Eingabedateiliste und Ausgabe ergänzen
        cmd.extend([
            "-input_file_list",
            str(input_list_txt),
            str(output_vrt),
        ])

        subprocess.run(
            cmd,
            check=True,
        )

    finally:
        input_list_txt.unlink(missing_ok=True)


def build_overviews(
    vrt,
    levels,
    resampling="average",
    workers=8,
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
        str(vrt),
    ]

    cmd.extend(
        [str(x) for x in levels]
    )

    subprocess.run(
        cmd,
        check=True,
    )