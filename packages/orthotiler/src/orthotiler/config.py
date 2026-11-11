
from dataclasses import dataclass, field
from pathlib import Path
import os
import multiprocessing as mp
from .processing import get_worker_count

@dataclass
class OrthoConfig:
    """
    Central configuration for the Orthotiler package.
    """

    # Input and output paths
    input_dir: Path = None
    output_dir: Path = None
    metadata_dir: Path = None

    # Dataset naming
    tile_name: str = "orthotiler"
    vrt_name: str = None

    # Coordinate reference systems
    input_srs: int = None
    input_srs_specified: int = 25832
    output_srs: int = 25832

    # Tile grid configuration
    tile_width: float = 2000
    tile_height: float = 2000
    grid_origin: tuple = (0, 0)

    # Raster configuration
    input_formats: tuple = (
        "*.tif",
        "*.tiff",
        "*.jpg",
        "*.png",
        "*.img",
    )

    nodata_value: str = "0"

    # NoData clipping
    nodata_clip: bool = False
    nodata_clip_avoid_holes: bool = False

    # COG configuration
    compression: str = "ZSTD"
    predictor: int = 2
    bigtiff: str = "YES"

    # Overview configuration
    overview_resampling: str = "average"
    target_overview_pixels: int = 3000

    # Processing configuration
    workers: int = field(
        default_factory=get_worker_count
    )

    # Metadata configuration
    metadata_encoding: str = "utf-8"
    metadata_separator: str = "\r\n"
    metadata_base_parts: int = 4

    # Output folder names
    cog_folder: str = "kacheln"
    vrt_folder: str = "temp"
    footprint_folder: str = "kacheluebersicht"

    def __post_init__(self):

        # Convert paths to Path objects
        if self.input_dir is not None:
            self.input_dir = Path(self.input_dir)

        if self.output_dir is not None:
            self.output_dir = Path(self.output_dir)

        if self.metadata_dir is not None:
            self.metadata_dir = Path(self.metadata_dir)

        if self.vrt_name is None:
            self.vrt_name = self.tile_name

        self.validate()

    @property
    def cog_dir(self):
        return self.output_dir / self.cog_folder

    @property
    def vrt_dir(self):
        return self.output_dir / self.vrt_folder

    @property
    def footprint_dir(self):
        return self.output_dir / self.footprint_folder

def validate(self):
    """
    Validates the configuration parameters.
    """

    # Validate input directory
    if self.input_dir is None:
        raise ValueError(
            "input_dir must be configured."
        )

    if not self.input_dir.is_dir():
        raise FileNotFoundError(
            self.input_dir
        )

    # Validate output directory
    if self.output_dir is None:
        raise ValueError(
            "output_dir must be configured."
        )

    # Validate tile dimensions
    if self.tile_width <= 0:
        raise ValueError(
            "tile_width must be greater than zero."
        )

    if self.tile_height <= 0:
        raise ValueError(
            "tile_height must be greater than zero."
        )

    # Validate worker count
    if self.workers < 1:
        raise ValueError(
            "workers must be at least 1."
        )

    # Validate output CRS
    if self.output_srs <= 0:
        raise ValueError(
            "output_srs must be a valid EPSG code."
        )

    # Validate overview configuration
    if self.target_overview_pixels < 1:
        raise ValueError(
            "target_overview_pixels must be greater than zero."
        )
    
    def create_output_directories(self):
        """
        Creates all required output directories.
        """

        if self.output_dir is None:
            raise ValueError(
                "output_dir has not been configured."
            )

        for directory in (
            self.output_dir,
            self.cog_dir,
            self.vrt_dir,
            self.footprint_dir,
        ):

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        return self
