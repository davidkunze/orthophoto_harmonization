
from pathlib import Path


def scan_input_files(
    input_dir,
    formats=None,
    exclude_dirs=None,
    recursive=True,
):
    """
    Discovers raster files in an input directory.

    Parameters
    ----------
    input_dir : str or Path
        Root input directory.

    formats : tuple or list or None
        File patterns to search for.

    exclude_dirs : tuple or list or None
        Directory names to exclude.

    recursive : bool
        Enables recursive directory scanning.

    Returns
    -------
    list[Path]
        Sorted list of discovered raster files.
    """

    input_dir = Path(input_dir)

    if not input_dir.is_dir():
        raise NotADirectoryError(input_dir)

    if formats is None:
        formats = (
            "*.tif",
            "*.tiff",
            "*.jpg",
            "*.png",
            "*.img",
        )

    if exclude_dirs is None:
        exclude_dirs = ()

    # Normalize excluded directory names
    excluded_names = {
        str(name).lower()
        for name in exclude_dirs
    }

    input_files = []

    # Select the appropriate directory iterator
    iterator = (
        input_dir.rglob("*")
        if recursive
        else input_dir.glob("*")
    )

    for path in iterator:

        if not path.is_file():
            continue

        # Exclude files located in excluded directories
        relative_parts = path.relative_to(
            input_dir
        ).parts[:-1]

        if any(
            part.lower() in excluded_names
            for part in relative_parts
        ):
            continue

        # Match supported raster formats
        if any(
            path.match(pattern)
            for pattern in formats
        ):
            input_files.append(path)

    return sorted(
        input_files,
        key=lambda path: str(path).lower(),
    )


def scan_input_files_as_strings(
    input_dir,
    formats=None,
    exclude_dirs=None,
    recursive=True,
):
    """
    Discovers raster files and returns their paths as strings.
    """

    files = scan_input_files(
        input_dir=input_dir,
        formats=formats,
        exclude_dirs=exclude_dirs,
        recursive=recursive,
    )

    return [
        str(path)
        for path in files
    ]
