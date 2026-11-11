
from dataclasses import dataclass
from math import floor, ceil

from shapely.geometry import box


@dataclass
class Tile:
    """
    Represents a single raster tile.

    Attributes
    ----------
    xmin, ymin, xmax, ymax : float
        Tile boundaries in map units.

    row, col : int
        Position within the tile grid.
    """

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    row: int
    col: int

    @property
    def bounds(self):
        return (
            self.xmin,
            self.ymin,
            self.xmax,
            self.ymax,
        )

    @property
    def geometry(self):
        return box(*self.bounds)

    @property
    def name_suffix(self):
        return f"{int(self.xmin)}_{int(self.ymax)}"


def calculate_tiles(
    bounds,
    tile_size=(2000, 2000),
    grid_origin=(0, 0),
    include_empty=False,
):
    """
    Calculates a regular tile grid covering a given extent.

    Parameters
    ----------
    bounds : tuple
        Input extent:
        (xmin, ymin, xmax, ymax).

    tile_size : tuple
        Tile width and height in map units.
        Default: 2000 x 2000.

    grid_origin : tuple
        Origin of the regular tile grid.
        Default: (0, 0).

    include_empty : bool
        If True, all grid tiles are returned.
        If False, only intersecting tiles are returned.

    Returns
    -------
    list[Tile]
        Calculated tiles.
    """

    xmin, ymin, xmax, ymax = bounds

    tile_width, tile_height = tile_size

    origin_x, origin_y = grid_origin

    if xmax <= xmin or ymax <= ymin:
        raise ValueError(
            "Invalid raster bounds."
        )

    if tile_width <= 0 or tile_height <= 0:
        raise ValueError(
            "Tile dimensions must be positive."
        )

    # Calculate the grid indices
    col_min = floor(
        (xmin - origin_x) / tile_width
    )

    col_max = ceil(
        (xmax - origin_x) / tile_width
    )

    row_min = floor(
        (ymin - origin_y) / tile_height
    )

    row_max = ceil(
        (ymax - origin_y) / tile_height
    )

    tiles = []

    # Generate tiles from bottom to top and left to right
    for row in range(row_min, row_max):

        for col in range(col_min, col_max):

            tile_xmin = (
                origin_x + col * tile_width
            )

            tile_ymin = (
                origin_y + row * tile_height
            )

            tile_xmax = (
                tile_xmin + tile_width
            )

            tile_ymax = (
                tile_ymin + tile_height
            )

            tile = Tile(
                xmin=tile_xmin,
                ymin=tile_ymin,
                xmax=tile_xmax,
                ymax=tile_ymax,
                row=row,
                col=col,
            )

            # Exclude tiles that do not intersect the input extent
            if not include_empty:

                if not tile.geometry.intersects(
                    box(*bounds)
                ):
                    continue

            tiles.append(tile)

    return tiles


def filter_tiles_by_geometry(
    tiles,
    geometry,
    exclude_touches=True,
):
    """
    Filters tiles based on intersection with a geometry.

    Parameters
    ----------
    tiles : list[Tile]
        Calculated tiles.

    geometry : shapely geometry
        Input data footprint.

    exclude_touches : bool
        Excludes tiles that only touch the footprint boundary.

    Returns
    -------
    list[Tile]
        Selected tiles.
    """

    if geometry is None or geometry.is_empty:
        return []

    selected = []

    for tile in tiles:

        tile_geometry = tile.geometry

        if not tile_geometry.intersects(geometry):
            continue

        # Exclude tiles with boundary-only intersections
        if exclude_touches and tile_geometry.touches(geometry):
            continue

        selected.append(tile)

    return selected


def calculate_tiles_from_bounds(
    bounds,
    tile_size=(2000, 2000),
    grid_origin=(0, 0),
):
    """
    Calculates all tiles covering the input bounds.

    Returns both the complete grid and the selected tiles.
    """

    all_tiles = calculate_tiles(
        bounds=bounds,
        tile_size=tile_size,
        grid_origin=grid_origin,
        include_empty=True,
    )

    selected_tiles = calculate_tiles(
        bounds=bounds,
        tile_size=tile_size,
        grid_origin=grid_origin,
        include_empty=False,
    )

    return {
        "all_tiles": all_tiles,
        "selected_tiles": selected_tiles,
    }
