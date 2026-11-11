from .extents import (
    create_input_extent,
)

from .geometry import (
    get_angles,
    simplify_by_angle,
    remove_inner_rings,
)

from .footprints import (
    create_tile_footprint,
    merge_tile_footprints,
    create_dataset_outline,
)

__all__ = [
    "create_input_extent",
    "get_angles",
    "simplify_by_angle",
    "remove_inner_rings",
    "create_tile_footprint",
    "merge_tile_footprints",
    "create_dataset_outline",
]