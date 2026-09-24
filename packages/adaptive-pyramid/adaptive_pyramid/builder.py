from pathlib import Path

import rasterio

from .models import CogInfo
from .planner import overview_plan



class PyramidBuilder:


    def __init__(
        self,
        cog_folder,
        target_pixels=3000
    ):

        self.cog_folder = Path(cog_folder)

        self.target_pixels = target_pixels

        self.cogs = []



    def scan(self):

        self.cogs = []


        for path in self.cog_folder.glob("*.tif"):


            with rasterio.open(path) as src:


                ovs = src.overviews(1)


                max_overview = (
                    max(ovs)
                    if ovs
                    else 1
                )


                self.cogs.append(

                    CogInfo(

                        path=path,

                        bounds=(

                            src.bounds.left,
                            src.bounds.bottom,
                            src.bounds.right,
                            src.bounds.top

                        ),

                        width=src.width,

                        height=src.height,

                        resolution=abs(
                            src.transform.a
                        ),

                        max_overview=max_overview
                    )
                )


        return self.cogs



    def plan(self):


        if not self.cogs:

            self.scan()



        minx=min(
            c.bounds[0]
            for c in self.cogs
        )

        miny=min(
            c.bounds[1]
            for c in self.cogs
        )

        maxx=max(
            c.bounds[2]
            for c in self.cogs
        )

        maxy=max(
            c.bounds[3]
            for c in self.cogs
        )



        resolution=self.cogs[0].resolution



        width=int(
            (maxx-minx)
            /
            resolution
        )


        height=int(
            (maxy-miny)
            /
            resolution
        )



        max_cog_level=min(
            c.max_overview
            for c in self.cogs
        )



        levels=overview_plan(

            width,

            height,

            resolution,

            max_cog_level,

            self.target_pixels

        )



        return {

            "cogs":
                len(self.cogs),

            "resolution":
                resolution,

            "size":
                (
                    width,
                    height
                ),

            "max_cog_overview":
                max_cog_level,

            "needed_overviews":
                levels

        }