
from pathlib import Path

import fiona
import geopandas as gpd
import pandas as pd


def read_metadata(
    metadata_file,
    separator="\r\n",
    encoding="utf-8",
):
    """
    Reads metadata from a CSV file.

    The file contains one metadata entry per line.
    Entries are separated into column name and value
    using a semicolon.

    Parameters
    ----------
    metadata_file : str or Path
        Input metadata CSV file.

    separator : str
        Line separator.

    encoding : str
        File encoding.

    Returns
    -------
    list[str]
        Metadata entries.
    """

    metadata_file = Path(metadata_file)

    if not metadata_file.is_file():
        raise FileNotFoundError(metadata_file)

    metadata = pd.read_csv(
        metadata_file,
        sep=separator,
        skip_blank_lines=True,
        header=None,
        encoding=encoding,
        engine="python",
    )

    return metadata.values.flatten().tolist()


def parse_metadata(metadata):
    """
    Converts metadata entries into a dictionary.

    Expected format:
        column_name;value

    Entries without a semicolon are ignored.
    """

    metadata_dict = {}

    for entry in metadata:

        entry = entry.rstrip()

        if ";" not in entry:
            continue

        column, value = entry.split(";", 1)

        column = column.strip()
        value = value.strip()

        if not column:
            continue

        metadata_dict[column] = value

    return metadata_dict


def add_metadata_columns(
    dataframe,
    metadata,
):
    """
    Adds metadata columns to a GeoDataFrame.

    Existing columns are not overwritten.
    """

    for column, value in metadata.items():

        if column not in dataframe.columns:

            dataframe.insert(
                len(dataframe.columns),
                column,
                value,
            )

        else:

            dataframe[column] = value

    return dataframe


def add_flight_year(
    dataframe,
    date_column="datum_bildflug_von",
    year_column="bildflug_jahr",
):
    """
    Extracts the flight year from the flight date column.

    The original behavior is preserved:
    the year is taken from the first date entry.
    """

    if date_column not in dataframe.columns:
        raise KeyError(
            f"Missing metadata column: {date_column}"
        )

    if year_column in dataframe.columns:
        dataframe = dataframe.drop(
            columns=[year_column]
        )

    index = dataframe.columns.get_loc(
        date_column
    )

    dataframe.insert(
        index,
        year_column,
        "",
    )

    dataframe[year_column] = (
        dataframe[date_column]
        .str.split("-")[0][0]
    )

    return dataframe


def add_relative_path(
    dataframe,
    path_column="path",
    location_column="location",
    base_parts=4,
):
    """
    Creates a relative path from the original location.

    The original path convention is preserved:
    the first four Windows path components are removed.
    """

    if location_column not in dataframe.columns:
        raise KeyError(
            f"Missing path column: {location_column}"
        )

    if path_column in dataframe.columns:
        dataframe = dataframe.drop(
            columns=[path_column]
        )

    index = dataframe.columns.get_loc(
        location_column
    )

    dataframe.insert(
        index,
        path_column,
        "",
    )

    dataframe[path_column] = dataframe.apply(
        lambda row: "/".join(
            str(row[location_column]).split("\\")[base_parts:]
        ),
        axis=1,
    )

    dataframe.drop(
        columns=[location_column],
        inplace=True,
    )

    return dataframe


def update_epsg(
    dataframe,
    output_srs,
    epsg_column="epsg",
):
    """
    Updates the EPSG metadata column.
    """

    if epsg_column in dataframe.columns:

        dataframe.loc[
            dataframe[epsg_column] != str(output_srs),
            epsg_column,
        ] = str(output_srs)

    return dataframe


def process_metadata_layer(
    dataframe,
    metadata,
    output_srs,
    base_parts=4,
):
    """
    Applies metadata processing to one GeoPackage layer.
    """

    dataframe = add_metadata_columns(
        dataframe,
        metadata,
    )

    dataframe = add_flight_year(
        dataframe,
    )

    dataframe = add_relative_path(
        dataframe,
        base_parts=base_parts,
    )

    dataframe = update_epsg(
        dataframe,
        output_srs,
    )

    if "ID" in dataframe.columns:

        dataframe.drop(
            columns=["ID"],
            inplace=True,
        )

    return dataframe


def insert_metadata(
    geopackage,
    metadata,
    output_srs,
    base_parts=4,
):
    """
    Adds metadata to every layer in a GeoPackage.

    All layers are processed individually.
    """

    geopackage = Path(geopackage)

    if not geopackage.is_file():
        raise FileNotFoundError(geopackage)

    metadata_dict = parse_metadata(
        metadata
    )

    layers = fiona.listlayers(
        geopackage
    )

    for layer in layers:

        dataframe = gpd.read_file(
            geopackage,
            layer=layer,
        )

        dataframe = process_metadata_layer(
            dataframe=dataframe,
            metadata=metadata_dict,
            output_srs=output_srs,
            base_parts=base_parts,
        )

        dataframe.to_file(
            geopackage,
            layer=layer,
            driver="GPKG",
            mode="w",
        )

    return geopackage
