from pathlib import Path

import rasterio

from .models import CogInfo
from .planner import overview_plan
from .vrt import build_vrt, build_overviews


class PyramidBuilder:
    """
    Analysiert COG-Mosaike und erzeugt
    VRTs sowie passende Overviews.
    """

    def __init__(
        self,
        cog_folder,
        target_pixels=3000
    ):
        self.cog_folder = Path(cog_folder)
        self.target_pixels = target_pixels
        self.cogs = []


    def scan(self):
        """
        Liest alle COG-Metadaten.
        """

        self.cogs = []

        tif_files = list(
            self.cog_folder.rglob("*.tif")
        )

        if not tif_files:
            raise RuntimeError(
                f"Keine TIFF-Dateien gefunden: {self.cog_folder}"
            )


        for path in tif_files:

            with rasterio.open(path) as src:

                overviews = src.overviews(1)

                max_overview = (
                    max(overviews)
                    if overviews
                    else 1
                )


                cog = CogInfo(
                    path=path,

                    bounds=(
                        src.bounds.left,
                        src.bounds.bottom,
                        src.bounds.right,
                        src.bounds.top,
                    ),

                    width=src.width,

                    height=src.height,

                    resolution=abs(
                        src.transform.a
                    ),

                    max_overview=max_overview,
                )


                self.cogs.append(cog)


        return self.cogs



    def plan(self):
        """
        Berechnet benötigte zusätzliche
        Overview-Level.
        """

        if not self.cogs:
            self.scan()


        minx = min(
            c.bounds[0]
            for c in self.cogs
        )

        miny = min(
            c.bounds[1]
            for c in self.cogs
        )

        maxx = max(
            c.bounds[2]
            for c in self.cogs
        )

        maxy = max(
            c.bounds[3]
            for c in self.cogs
        )


        resolution = self.cogs[0].resolution


        width = int(
            (maxx - minx)
            /
            resolution
        )

        height = int(
            (maxy - miny)
            /
            resolution
        )


        max_cog_overview = min(
            c.max_overview
            for c in self.cogs
        )


        levels = overview_plan(
            width,
            height,
            resolution,
            max_cog_overview,
            self.target_pixels,
        )


        return {

            "cogs":
                len(self.cogs),

            "resolution":
                resolution,

            "size":
                (
                    width,
                    height,
                ),

            "max_cog_overview":
                max_cog_overview,

            "needed_overviews":
                levels,
        }



    def create_vrt(
        self,
        output_vrt
    ):
        """
        Erstellt ein VRT aus den COGs.
        """

        output_vrt = Path(output_vrt)

        return build_vrt(
            self.cog_folder,
            output_vrt
        )



    def create_overviews(
        self,
        vrt,
        workers=8,
        resampling="average"
    ):
        """
        Erzeugt nur notwendige VRT-Overviews.
        """

        plan = self.plan()

        levels = plan[
            "needed_overviews"
        ]


        if not levels:

            print(
                "Keine zusätzlichen Overviews notwendig."
            )

            return []


        print(
            "Erzeuge Overviews:",
            levels
        )


        build_overviews(
            vrt=vrt,
            levels=levels,
            resampling=resampling,
            workers=workers,
        )


        return levels