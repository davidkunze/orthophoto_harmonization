
from pathlib import Path


def find_metadata_file(
    metadata_dir,
    filename="metadata.csv",
):
    """
    Finds the metadata CSV file.

    Parameters
    ----------
    metadata_dir : str or Path
        Metadata directory or direct file path.

    filename : str
        Expected metadata filename.

    Returns
    -------
    Path
        Path to the metadata file.
    """

    metadata_dir = Path(metadata_dir)

    if metadata_dir.is_file():
        return metadata_dir

    if not metadata_dir.is_dir():
        raise NotADirectoryError(metadata_dir)

    metadata_file = metadata_dir / filename

    if not metadata_file.is_file():
        raise FileNotFoundError(metadata_file)

    return metadata_file
