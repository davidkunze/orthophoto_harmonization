
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .config import OrthoConfig
from .processing import get_worker_count, process_tile


class Orthotiler:
    """
    Controls the complete orthophoto tiling workflow.
    """

    def __init__(self, config: OrthoConfig):

        self.config = config

        self.input_files = []
        self.input_vrt = None
        self.processed_vrt = None
        self.working_raster = None

        self.raster_info = None
        self.input_srs = None

        self.tiles = []

        self.nodata_mask = None
        self.nodata_cutline = None
        self.nodata_raster = None

        self.extent_file = None
        self.metadata = None

        self.warnings = []
        self.results = {}

        self.tile_results = []
        self.failed_tiles = []

        self.config.validate()

    def prepare_output(self):
        """Creates the required output directories."""

        self.config.create_output_directories()

    def discover_inputs(self):
        """
        Discovers all supported input raster files.
        """

        from .input import scan_input_files

        self.input_files = scan_input_files(
            input_dir=self.config.input_dir,
            formats=self.config.input_formats,
            exclude_dirs=(
                self.config.cog_folder,
                self.config.vrt_folder,
                self.config.footprint_folder,
            ),
            recursive=True,
        )

        if not self.input_files:
            raise RuntimeError(
                f"No input raster files found in "
                f"{self.config.input_dir}"
            )

        print(
            f"Input files found: {len(self.input_files)}"
        )

        return self.input_files

    def create_input_vrt(self):
        """
        Creates a temporary VRT from the input rasters.
        """

        from .raster.vrt import (
            build_vrt,
            get_raster_info,
        )

        self.input_vrt = (
            self.config.vrt_dir / "temp.vrt"
        )

        build_vrt(
            input_files=self.input_files,
            output_vrt=self.input_vrt,
            bands=(1, 2, 3, 4),
            nodata_value=(
                self.config.nodata_value or None
            ),
            allow_projection_difference=True,
        )

        self.raster_info = get_raster_info(
            self.input_vrt
        )

        return self.input_vrt

    def prepare_projection(self):
        """
        Checks and prepares the output projection.
        """

        from .raster.projection import (
            get_raster_srs,
            reproject_raster,
        )

        detected_srs = get_raster_srs(
            self.input_vrt
        )

        self.input_srs = detected_srs

        if detected_srs == self.config.output_srs:

            self.processed_vrt = self.input_vrt

            return self.processed_vrt

        result = reproject_raster(
            input_raster=self.input_vrt,
            output_raster=(
                self.config.vrt_dir
                / f"temp_{self.config.output_srs}.vrt"
            ),
            output_srs=self.config.output_srs,
            input_srs=self.config.input_srs,
            fallback_srs=self.config.input_srs_specified,
        )

        self.processed_vrt = result["output_path"]

        if result["warning"]:
            self.warnings.append(
                result["warning"]
            )

        return self.processed_vrt

    def prepare_nodata(self):
        """
        Prepares NoData processing.

        This step is optional and is only executed
        when nodata_clip is enabled.
        """

        if not self.config.nodata_clip:

            self.working_raster = self.processed_vrt

            print(
                "NoData clipping disabled."
            )

            return self.working_raster

        from .raster.nodata import (
            create_nodata_mask,
            create_nodata_cutline,
            get_destination_nodata,
            clip_nodata,
        )

        print(
            "Preparing NoData processing."
        )

        temp_dir = self.config.vrt_dir

        self.nodata_mask = (
            temp_dir / "nodata_mask.tif"
        )

        self.nodata_cutline = (
            temp_dir / "nodata_cutline.gpkg"
        )

        self.nodata_raster = (
            temp_dir / "nodata_clipped.tif"
        )

        nodata_value = get_destination_nodata(
            self.processed_vrt,
            nodata_value=(
                self.config.nodata_value or None
            ),
        )

        create_nodata_mask(
            input_raster=self.processed_vrt,
            output_mask=self.nodata_mask,
            nodata_value=nodata_value,
        )

        create_nodata_cutline(
            mask_raster=self.nodata_mask,
            output_cutline=self.nodata_cutline,
            avoid_holes=(
                self.config.nodata_clip_avoid_holes
            ),
        )

        clip_nodata(
            input_raster=self.processed_vrt,
            output_raster=self.nodata_raster,
            cutline=self.nodata_cutline,
            destination_nodata=nodata_value,
            crop_to_cutline=False,
        )

        self.working_raster = self.nodata_raster

        print(
            "NoData processing completed."
        )

        return self.working_raster

    def calculate_tile_grid(self):
        """
        Calculates the tile grid covering the input raster.
        """

        from .raster.vrt import get_raster_info
        from .raster.tiling import calculate_tiles

        if self.working_raster is None:
            raise RuntimeError(
                "No working raster available."
            )

        self.raster_info = get_raster_info(
            self.working_raster
        )

        self.tiles = calculate_tiles(
            bounds=self.raster_info["bounds"],
            tile_size=(
                self.config.tile_width,
                self.config.tile_height,
            ),
            grid_origin=self.config.grid_origin,
        )

        if not self.tiles:
            raise RuntimeError(
                "No tiles could be calculated."
            )

        print(
            f"Tiles calculated: {len(self.tiles)}"
        )

        print(
            f"Tile size: "
            f"{self.config.tile_width} x "
            f"{self.config.tile_height}"
        )

        return self.tiles

    def create_tiles(self):
        """
        Creates COG tiles in parallel.
        """

        if not self.tiles:
            raise RuntimeError(
                "No tiles available. Calculate the tile grid first."
            )

        workers = get_worker_count(
            workers=self.config.workers,
            task_count=len(self.tiles),
        )

        print(
            f"Creating {len(self.tiles)} COG tiles "
            f"using {workers} workers."
        )

        self.tile_results = []
        self.failed_tiles = []

        with ProcessPoolExecutor(
            max_workers=workers
        ) as executor:

            futures = {

                executor.submit(
                    process_tile,
                    input_vrt=str(self.working_raster),
                    tile=tile,
                    output_dir=str(self.config.cog_dir),
                    output_srs=self.config.output_srs,
                    compression=self.config.compression,
                    predictor=self.config.predictor,
                    bigtiff=self.config.bigtiff,
                    overview_resampling=(
                        self.config.overview_resampling
                    ),
                ): tile

                for tile in self.tiles
            }

            for future in as_completed(futures):

                tile = futures[future]

                try:

                    result = future.result()

                except Exception as error:

                    result = {
                        "success": False,
                        "tile": tile.name_suffix,
                        "path": None,
                        "error": str(error),
                    }

                self.tile_results.append(result)

                if not result["success"]:

                    self.failed_tiles.append(result)

                    print(
                        f"Tile failed: {result['tile']} "
                        f"- {result['error']}"
                    )

        successful = sum(
            result["success"]
            for result in self.tile_results
        )

        print(
            f"COG creation completed: "
            f"{successful}/{len(self.tiles)} successful."
        )

        return self.tile_results


    def create_footprints(self):
        """
        Creates individual tile footprints and
        merges them into a dataset outline.
        """

        from .vector.footprints import (
            create_tile_footprint,
            merge_tile_footprints,
            create_dataset_outline,
        )

        successful_tiles = [
            result
            for result in self.tile_results
            if result["success"]
        ]

        if not successful_tiles:
            raise RuntimeError(
                "No successful COG tiles available."
            )

        footprint_files = []

        print("Creating tile footprints.")

        for result in successful_tiles:

            raster_path = Path(result["path"])

            footprint_path = (
                self.config.footprint_dir
                / f"{raster_path.stem}.gpkg"
            )

            try:

                create_tile_footprint(
                    raster_path=raster_path,
                    output_path=footprint_path,
                    simplify=True,
                    deg_tol=1,
                )

                footprint_files.append(
                    footprint_path
                )

            except Exception as error:

                self.warnings.append(
                    f"Footprint failed for "
                    f"{raster_path.name}: {error}"
                )

        if not footprint_files:
            raise RuntimeError(
                "No tile footprints could be created."
            )

        merged_path = (
            self.config.footprint_dir
            / "tile_footprints.gpkg"
        )

        merged = merge_tile_footprints(
            footprint_files=footprint_files,
            output_path=merged_path,
        )

        self.extent_file = merged_path

        outline_path = (
            self.config.footprint_dir
            / "dataset_outline.gpkg"
        )

        create_dataset_outline(
            footprint_dataframe=merged,
            output_path=outline_path,
        )

        self.results["footprint_files"] = (
            footprint_files
        )

        self.results["footprints"] = merged_path
        self.results["outline"] = outline_path

        print("Footprint creation completed.")

        return outline_path

    
    def process_metadata(self):
        """
        Inserts metadata into the footprint GeoPackage.
        """

        if self.config.metadata_dir is None:
            print("Metadata processing skipped.")
            return None

        from .metadata import (
            read_metadata,
            insert_metadata,
        )

        metadata_file = Path(self.config.metadata_dir)

        if metadata_file.is_dir():
            metadata_file = (
                metadata_file / "metadata.csv"
            )

        if not metadata_file.is_file():
            raise FileNotFoundError(metadata_file)

        metadata = read_metadata(
            metadata_file,
            separator=self.config.metadata_separator,
            encoding=self.config.metadata_encoding,
        )

        self.metadata = metadata

        if self.extent_file is None:
            raise RuntimeError(
                "No footprint GeoPackage available."
            )

        insert_metadata(
            geopackage=self.extent_file,
            metadata=metadata,
            output_srs=self.config.output_srs,
            base_parts=self.config.metadata_base_parts,
        )

        print("Metadata processing completed.")

        return self.extent_file


    def create_output_vrt(self):
        """
        Creates a VRT from all successfully generated COG tiles.
        """

        from .raster.vrt import build_vrt

        cog_files = [
            Path(result["path"])
            for result in self.tile_results
            if result["success"]
            and result["path"] is not None
        ]

        if not cog_files:
            raise RuntimeError(
                "No COG files available for output VRT."
            )

        output_vrt = (
            self.config.vrt_dir
            / f"{self.config.vrt_name}.vrt"
        )

        build_vrt(
            input_files=cog_files,
            output_vrt=output_vrt,
            allow_projection_difference=False,
            overwrite=True,
        )

        self.output_vrt = output_vrt

        print(
            f"Output VRT created: {output_vrt}"
        )

        return output_vrt


    def create_output_overviews(self):
        """
        Creates additional overviews for the output VRT.
        """

        from .raster.vrt import build_overviews

        if self.output_vrt is None:
            raise RuntimeError(
                "Output VRT has not been created."
            )

        width = self.raster_info["width"]
        height = self.raster_info["height"]

        resolution = self.raster_info["resolution"][0]

        levels = []
        current = max(width, height)
        level = 1

        while current > self.config.target_overview_pixels:

            level *= 2

            levels.append(level)

            current /= 2

        if levels:

            build_overviews(
                vrt=self.output_vrt,
                levels=levels,
                resampling=self.config.overview_resampling,
                workers=self.config.workers,
            )

        print(
            f"Output overviews created: {levels}"
        )

        return levels

    
    def run(self):
        """
        Executes the complete orthophoto tiling workflow.
        """

        print("Starting Orthotiler.")

        # Step 1: Prepare output directories
        self.prepare_output()

        # Step 2: Discover input raster files
        self.discover_inputs()

        # Step 3: Create input VRT
        self.create_input_vrt()

        # Step 4: Prepare output projection
        self.prepare_projection()

        # Step 5: Prepare NoData processing
        self.prepare_nodata()

        # Step 6: Calculate tile grid
        self.calculate_tile_grid()

        # Step 7: Create COG tiles
        self.create_tiles()

        self.create_output_vrt()

        self.create_output_overviews()

        # Step 8: Create tile footprints
        self.create_footprints()

        # Step 9: Insert metadata
        self.process_metadata()

        # Collect final results
        self.results.update({
            "input_files": self.input_files,
            "input_vrt": self.input_vrt,
            "processed_vrt": self.processed_vrt,
            "working_raster": self.working_raster,
            "raster_info": self.raster_info,
            "input_srs": self.input_srs,
            "tiles": self.tiles,
            "tile_results": self.tile_results,
            "failed_tiles": self.failed_tiles,
            "nodata_mask": self.nodata_mask,
            "nodata_cutline": self.nodata_cutline,
            "nodata_raster": self.nodata_raster,
            "footprints": self.extent_file,
            "warnings": self.warnings,
        })

        print("Orthotiler processing completed.")

        return self.results
