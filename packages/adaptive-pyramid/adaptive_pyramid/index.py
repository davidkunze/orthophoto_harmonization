from shapely.geometry import box
from shapely.strtree import STRtree



class CogIndex:


    def __init__(self, cogs):

        self.cogs = cogs


        geometries = [

            box(*c.bounds)

            for c in cogs

        ]


        self.tree = STRtree(
            geometries
        )



    def query(self, bounds):


        geom = box(*bounds)


        return self.tree.query(
            geom
        )