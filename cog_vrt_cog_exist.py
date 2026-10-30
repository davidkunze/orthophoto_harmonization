import os

# Problem with Fiona and GDAL on Windows if other software (e.g., PCI Geomatics) is installed that also uses packages like gdal or fiona.
os.environ["PATH"] = os.pathsep.join(
    p for p in os.environ["PATH"].split(os.pathsep)
    if not p.lower().startswith("c:\\pci geomatics\\")
)

from glob import glob
import pathlib
import multiprocessing as mp
import time
import fiona
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import geopandas
import pandas
import numpy
import subprocess
import rasterio
from shapely.validation import make_valid 
from osgeo import gdal, osr, ogr

from adaptive_pyramid import PyramidBuilder

gdal.UseExceptions()
# gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")
# gdal.SetConfigOption("GDAL_CACHEMAX", "60000")

start_time = time.time()
#insert path as server path: e.g.: "\\lb-srv\Luftbilder\luft..." (do not use drive letter)
path_data = r'\\lb-srv\fern_2\luftbild\ni\flugzeug\2026\harz_np\dop\daten'
path_out = path_data
# path_out = r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\daten"
# naming scheme for tiles: bundesland_tragersystem_jahr_gebiet_auftrageber_datentyp_x-wert_y-wert
    # For abbreviations open "\\lb-server\LB-Projekte\SGB4_InterneVerwaltung\EDV\KON-GEO\2024\vrt_benennung\vrt_benennung.txt"
    # x-wert und y-wert will be added later
tile_name = 'ni_flugzeug_2026_harz_np_dop'
vrt_name = tile_name
# fill string if special nodata-value such as "255" is used in data
# if nodata-value is "nodata" use empty string ''
nodata_value = '0' 
nodata_clip_option = 0 # if nodata_clip_option = 1, nodata values will be clipped from the tiles


in_srs_specified = 25832 #in some cases, the coordinate system does not apper GDAL-readable, in such cases, specify coordinate system 
out_srs = 25832 #EPSG-code of output projection

path_meta = os.path.join(os.path.dirname(path_out),"doku")
cog_folder = 'kacheln'
footprint_folder = 'kacheluebersicht'

#create subfolder
def create_folder(output_f, folder_name):
    if not os.path.isdir(os.path.join(output_f, folder_name)):
        os.mkdir(os.path.join(output_f, folder_name))

folder_list = [cog_folder, footprint_folder]
for x in folder_list:
    create_folder(path_out,x)
dir_cog = os.path.join(path_out,cog_folder)
dir_footprint = os.path.join(path_out,footprint_folder)



formats = ['*.tif']
path_data = pathlib.Path(path_data)

# Collect all files matching the formats
input_windows_path = [p for pattern in formats for p in path_data.rglob(pattern)]

# Filter and convert to strings
input_data = [
    str(p)
    for p in input_windows_path
    if cog_folder in p.parent.as_posix()
]


# get_angle function
def get_angles(vec_1, vec_2):
    # Return the angle, in degrees, between two vectors
    # Convert 2D vectors to 3D by adding a 0 in the third dimension
    vec_1_3d = numpy.array([vec_1[0], vec_1[1], 0])
    vec_2_3d = numpy.array([vec_2[0], vec_2[1], 0])
    dot = numpy.dot(vec_1_3d, vec_2_3d)
    det = numpy.cross(vec_1_3d, vec_2_3d)[2]  # Take the z-component of the cross product
    angle_in_rad = numpy.arctan2(det, dot)
    return numpy.degrees(angle_in_rad)

# Function for removing superfluous corner points along a straight line that would require a large amount of memory space
def simplify_by_angle(poly_in, deg_tol=1):
    # poly_in: shapely Polygon
    # deg_tol: degree tolerance for comparison between successive vectors
    ext_poly_coords = poly_in.exterior.coords[:]
    vector_rep = numpy.diff(ext_poly_coords, axis=0)
    num_vectors = len(vector_rep)
    angles_list = []
    for i in range(0, num_vectors):
        angles_list.append(numpy.abs(get_angles(vector_rep[i], vector_rep[(i + 1) % num_vectors])))
    # get mask satisfying tolerance
    thresh_vals_by_deg = numpy.where(numpy.array(angles_list) > deg_tol)
    new_idx = list(thresh_vals_by_deg[0] + 1)
    new_vertices = [ext_poly_coords[idx] for idx in new_idx]
    return Polygon(new_vertices)

def remove_inner_rings(geom):
    if isinstance(geom, Polygon):
        geom = simplify_by_angle(geom)
        return Polygon(geom.exterior)
    elif isinstance(geom, MultiPolygon):
        geom = MultiPolygon([simplify_by_angle(p) for p in geom.geoms])
        return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])
    else:
        return geom

def outline_from_raster(raster_path):
    # create polygon from data extent
    output_name = os.path.basename(raster_path).replace('.tif', '')
    outline = os.path.join(dir_footprint, f"{output_name}.gpkg")
    if not os.path.isfile(outline): #calculate file just if it exists
        gdalvectorString = f'gdal_contour -q -fl 0 -b 1 -f "GPKG" -p {raster_path} {outline}'
        subprocess.run(gdalvectorString, shell=True)
        # Simplifying contour polygon to reduce number of vertices
        gdf = geopandas.read_file(outline, layer='contour')
        simplified_geometries = []
        # Apply the simplification function to each geometry in the GeoDataFrame
        for geometry in gdf['geometry']:
            # For MultiPolygon, simplify each individual Polygon in the MultiPolygon
            simplified_multipolygon = MultiPolygon([simplify_by_angle(p) for p in geometry.geoms])
            simplified_geometries.append(simplified_multipolygon)
        gdf['geometry'] = simplified_geometries
        # Save the modified geodata frame back to the file
        gdf.to_file(outline, layer='contour', driver="GPKG")

    df = geopandas.read_file(outline, layer='contour')
    # remove empty vector tiles, raster tiles
    
    if 'location' not in df.columns:
        df.insert(1, 'location', raster_path)
        df.to_file(outline, layer='contour', driver='GPKG')  


# ###############
# create 2x2 km cog tiles from temporary vrt that was created from input data  
if __name__ == '__main__':
    count = mp.cpu_count()
    pool = mp.Pool(count-count+6)
    pool.starmap(outline_from_raster, [(x,) for x in input_data])
    pool.close()
    pool.join()

    # create extent vector layer which contains following three layers
    #   outline of complete dataset
    #   outline of each tile
    #   all 2x2 km tiles which contain data 
    vector_data = glob(os.path.join(dir_footprint, '*000.gpkg'))
    tiles_valid = []
    for x in vector_data:
        df = geopandas.read_file(x, layer='contour')
        tif_path = os.path.join(dir_cog, f"{os.path.basename(x)[:-5]}.tif")
        # remove empty vector tiles, raster tiles
        if df.empty:
            # continue
            os.remove(x)
            os.remove(tif_path)
        else:
            if 'location' not in df:
                df.insert(1, 'location', tif_path)
            tiles_valid.append(df)
    

    extent = os.path.join(dir_footprint, f'{tile_name}_extent.gpkg')

    # merge all tile outlines 
    df_merged = pandas.concat(tiles_valid)
    df_merged['geometry'] = df_merged['geometry'].make_valid()
    df_merged.to_file(extent, layer='footprint_outline', driver="GPKG")
    # dissolve tile outlines to dataset outline
    df_outline = df_merged.dissolve(by='ID')
    df_outline['location'] = os.path.join(path_data, f"{vrt_name}.vrt")
    df_outline['geometry'] =df_outline['geometry'].make_valid()
    df_outline.to_file(extent, layer='outline', driver="GPKG")
    # get all 2x2 km tiles which contain data
    if nodata_clip_option == 1:
        footprints = glob(os.path.join(dir_footprint, '*footprint.gpkg'))
        tiles_footprint = []
        for x in footprints:
            df = geopandas.read_file(x, layer='footprint')
            tiles_footprint.append(df)
        extent = os.path.join(dir_footprint, f'{tile_name}_extent.gpkg')
        df_footprint = pandas.concat(tiles_footprint)
        df_footprint.to_file(extent, layer='footprints', driver="GPKG") 
    else:
        gdalindex_string = f'gdaltindex -tileindex location -lyr_name footprints {extent} {os.path.join(dir_cog)}/*.tif'
        subprocess.run(gdalindex_string, shell=True)

    # read metadaten files
    metadata = glob(os.path.join(path_meta, '*.csv'))
    metadata = pandas.read_csv(metadata[0], sep='\r\n', skip_blank_lines=True, header=None, encoding='utf-8', engine='python')
    metadata = metadata.values.flatten().tolist()

    # add metadata to vector tiles
    def insert_medata(file):
        layers = fiona.listlayers(file)
        for table in layers:
            dataframe = geopandas.read_file(file, layer=table)
            for x in metadata:
                x = x.rstrip()
                if ';' in x:
                    y = x.split(';')
                    column = y[0]
                    value = y[1]
                    dataframe.insert(len(dataframe.columns), column, '') #add column to dataframe
                    dataframe[column] = value  #fill coulumn
            index = dataframe.columns.get_loc('datum_bildflug_von') #get column position
            dataframe.insert(index, 'bildflug_jahr', '')  # add column to dataframe
            dataframe['bildflug_jahr'] = dataframe['datum_bildflug_von'].str.split('-')[0][0]  # fill coulumn
            # if table != 'outline':
            index = dataframe.columns.get_loc('location')
            dataframe.insert(index, 'path', '')  # add column to dataframe
            dataframe['path'] = dataframe.apply(lambda row: '/'.join(row.location.split('\\')[4:]), axis = 1)
            dataframe.drop(['location'],axis=1,inplace=True)
            dataframe.loc[dataframe['epsg']!= str(out_srs),'epsg'] = str(out_srs)
            if 'ID' in dataframe.columns:
                dataframe.drop(['ID'],axis=1,inplace=True)
            dataframe.to_file(file, layer=table, driver="GPKG")

    insert_medata(extent)

    vrt = os.path.join(path_out, f"{vrt_name}.vrt")
    builder = PyramidBuilder(
        dir_cog
    )

    result = builder.plan()
    for k,v in result.items():

        print(
            k,
            ":",
            v
        )

    vrt_options = [
        "-srcnodata", nodata_value,  
    ]

    builder.create_vrt(
        vrt,
        gdal_options=vrt_options
    )


    builder.create_overviews(
        vrt,
        workers=mp.cpu_count()-2
    )

    # remove temporary layers
    vector_list = glob(os.path.join(dir_footprint, '*'))
    for x in vector_list:
        if x != extent:
            os.remove(x)

    

    hours, rem = divmod(time.time() - start_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print("{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))
