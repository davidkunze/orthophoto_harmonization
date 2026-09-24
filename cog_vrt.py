import os
import sys
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
gdal.UseExceptions()

start_time = time.time()
#insert path as server path: e.g.: "\\lb-srv\Luftbilder\luft..." (do not use drive letter)
path_data = r'\\lb-srv\LB-Ortho\ni\lverm\orthos_landesweit_stand_2022_0815\DOP_2021'
path_out = path_data
path_out = r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2021\ni_lverm\tdop\daten"
# naming scheme for tiles: bundesland_tragersystem_jahr_gebiet_auftrageber_datentyp_x-wert_y-wert
    # For abbreviations open "\\lb-server\LB-Projekte\SGB4_InterneVerwaltung\EDV\KON-GEO\2024\vrt_benennung\vrt_benennung.txt"
    # x-wert und y-wert will be added later
tile_name = 'ni_flugzeug_2021_ni_lverm_tdop'
vrt_name = tile_name
# fill string if special nodata-value such as "255" is used in data
# if nodata-value is "nodata" use empty string ''
nodata_value = '0' 
nodata_clip_option = 0 # if nodata_clip_option = 1, nodata values will be clipped from the tiles


in_srs_specified = 25832 #in some cases, the coordinate system does not apper GDAL-readable, in such cases, specify coordinate system 
out_srs = 25832 #EPSG-code of output projection

path_meta = os.path.join(os.path.dirname(path_out),"doku")
cog_folder = 'kacheln'
vrt_folder = 'temp'
footprint_folder = 'kacheluebersicht'

#create subfolder
def create_folder(output_f, folder_name):
    if not os.path.isdir(os.path.join(output_f, folder_name)):
        os.mkdir(os.path.join(output_f, folder_name))

folder_list = [cog_folder, vrt_folder, footprint_folder]
for x in folder_list:
    create_folder(path_out,x)
dir_cog = os.path.join(path_out,cog_folder)
dir_vrt = os.path.join(path_out,vrt_folder)
dir_footprint = os.path.join(path_out,footprint_folder)



formats = ['*.tif', '*.jpg', '*.png', '*.img', '*.ovr']
path_data = pathlib.Path(path_data)

# Collect all files matching the formats
input_windows_path = [p for pattern in formats for p in path_data.rglob(pattern)]

# Filter and convert to strings
input_data = [
    str(p)
    for p in input_windows_path
    if cog_folder not in p.parent.as_posix()
]


# create temporary vrt from raw data
vrt_temp = os.path.join(dir_vrt, 'temp.vrt')
input_data_str = '\n'.join(input_data)
input_list_txt = os.path.join(dir_vrt, 'input_list.txt')

with open(input_list_txt, 'w') as file:
    file.write(input_data_str)
    file.close()

buildvrtString = f'gdalbuildvrt -overwrite -allow_projection_difference -input_file_list {input_list_txt} {vrt_temp}'
subprocess.run(buildvrtString)

# buildvrtString = f'gdal raster mosaic --overwrite --input-file-list {input_list_txt} -f VRT {vrt_temp}'
# subprocess.run(buildvrtString, shell=True, check=True)

folder_list.append(os.path.basename(vrt_temp))

### get metadata of the input data
vrt_temp_ds = gdal.Open(vrt_temp)
# get input data projection
proj = osr.SpatialReference(wkt=vrt_temp_ds.GetProjection())
in_srs = proj.GetAttrValue('AUTHORITY',1)

# get input data datatype
band = vrt_temp_ds.GetRasterBand(1)
dtype = gdal.GetDataTypeName(band.DataType)
# get count of raster bands to know which band is alpha raster
band_count = vrt_temp_ds.RasterCount
# get nodata value
if nodata_value == '':
    nodata_value = vrt_temp_ds.GetRasterBand(1).GetNoDataValue()
else:
    i = 1
    nodata_list = []
    while i < band_count+1:
        nodata_list.append(nodata_value)
        i += 1
    buildvrtString = f'gdalbuildvrt -srcnodata "{ " ".join(nodata_list) }" -overwrite -allow_projection_difference -input_file_list {input_list_txt} {vrt_temp}'
    subprocess.run(buildvrtString, shell=True)
    print(f'nodata is existing: {nodata_value}')


# get input data extent to check which output tiles contain data
inputdata_extent = os.path.join(dir_vrt, 'inputdata_extent.gpkg') 
gdaltindexString = f'gdaltindex -f "GPKG" {inputdata_extent} -t_srs EPSG:{in_srs} --optfile {input_list_txt}'
subprocess.run(gdaltindexString, shell=True)

### reproject raw data if not EPSG: 25832
# function to check whether raw data is stored in subfolders
print(f'in_srs: {in_srs}')
print(f'out_srs: {out_srs}')
warning = ''
if not in_srs in [str(out_srs)]:
    inputdata_extent_proj = os.path.join(dir_vrt, f'inputdata_extent_{str(out_srs)}.gpkg') 
    vrt_temp_proj = os.path.join(dir_vrt, f'temp_{str(out_srs)}.vrt')
    if in_srs == None:
        gdalwarpString = f'gdalwarp -of VRT -s_srs EPSG:{in_srs_specified} -t_srs EPSG:{out_srs} {vrt_temp} {vrt_temp_proj}'
        subprocess.run(gdalwarpString, shell=True)
        ogr2ogrString = f'ogr2ogr -f "GPKG" -s_srs EPSG:{in_srs_specified} -t_srs EPSG:{out_srs} {inputdata_extent_proj} {inputdata_extent} inputdata_extent'
        print(ogr2ogrString)
        subprocess.run(ogr2ogrString, shell=True)
        print("in_srs is NONE")   
    elif in_srs in [4314, 9122]:
        # direct projection from 4314, 9122 to 25832 is defective, therefore the projection 31476 is used as in_srs
        in_srs = 31467
        gdalwarpString = f'gdalwarp -of VRT -s_srs EPSG:{in_srs} -t_srs EPSG:{out_srs} {vrt_temp} {vrt_temp_proj}'
        subprocess.run(gdalwarpString, shell=True)
        print(f'gdalwarpString: {gdalwarpString}')
        ogr2ogrString = f'ogr2ogr -f "GPKG" -s_srs EPSG:{in_srs} -t_srs EPSG:{out_srs} {inputdata_extent_proj} {inputdata_extent} inputdata_extent'
        subprocess.run(ogr2ogrString, shell=True)
        print("in_srs is 4314 or 9122")    
    else:
        gdalwarpString = f'gdalwarp -of VRT -s_srs EPSG:{in_srs_specified} -t_srs EPSG:{out_srs} {vrt_temp} {vrt_temp_proj}'
        subprocess.run(gdalwarpString, shell=True)
        ogr2ogrString = f'ogr2ogr -f "GPKG" -s_srs EPSG:{in_srs_specified} -t_srs EPSG:{out_srs} {inputdata_extent_proj} {inputdata_extent} inputdata_extent'
        subprocess.run(ogr2ogrString, shell=True)
        print(f'in_srs is {in_srs}')    
    warning =  '\n\n\n\n\n WARNHINWEIS! Ausgangsdaten haben kein Koordinatensystem zugewiesen, bitte nachpruefen, ob Daten vollstaendig und lagerichtig berechnet wurden! \n\n\n\n\n'
    vrt_temp = vrt_temp_proj
    inputdata_extent = inputdata_extent_proj
dataframe = geopandas.read_file(inputdata_extent, layer='inputdata_extent')
dataframe = dataframe.dissolve(by=None)
dataframe.to_file(inputdata_extent, layer='inputdata_extent', driver="GPKG")


### tiling temporary vrt into cog tiles
# get extent, raster origin
vrt_temp_ds_2 = gdal.Open(vrt_temp)
ulx, xres, xskew, uly, yskew, yres  = vrt_temp_ds_2.GetGeoTransform()
print(f'ulx: {int(ulx)}')

# tranform width and height from count of pixel into map unit (for epsg "25832": metre)
width = abs(int(vrt_temp_ds.RasterXSize*xres))
height = abs(int(vrt_temp_ds.RasterYSize*yres))
print(f'ulx_int+width: {int(ulx+width)}')
tilesize = 2000

# Convert height to a number with an even number of thousands
if height < 1000:
    height = 1000

if (int(str(height)[:-3]) % 2) == 0:
    height = int(f"{str(height)[:-3]}000")+4000
else:
    height = int(f"{str(height)[:-3]}000")+3000

# Convert width to a number with an even number of thousands
print(f'width: {width}')
if width < 1000:
    width = 1000

if (int(str(width)[:-3]) % 2) == 0:
    width = int(f"{str(width)[:-3]}000")+4000
else:
    width = int(f"{str(width)[:-3]}000")+3000
print(f'width_int_add: {width}')

# Convert ulx, uly to a number with an even number of thousands

ulx_int = int(f"{str(int(ulx))[:-3]}000")
if (int(str(ulx_int)[:-3]) % 2) == 0:
    ulx_int = int(f"{str(ulx_int)[:-3]}000")
else:
    ulx_int = int(f"{str(ulx_int)[:-3]}000")-1000
print(f'ulx_int: {ulx_int}')

uly_int = int(f"{str(int(uly))[:-3]}000")+tilesize
if (int(str(uly_int)[:-3]) % 2) == 0:
    uly_int = int(f"{str(uly_int)[:-3]}000")+2000
    height = height+2000
else:
    uly_int = int(f"{str(uly_int)[:-3]}000")+1000

tiles = []
tiles_polygon =[]
tiles_polygon_select =[]
tiles_all = []
# geotransform=[]

print(f'ulx_int+width: {ulx_int+width}')

# get tile extent for gdal translate
for i in range(ulx_int, ulx_int+width, tilesize):
    for j in range(uly_int-height, uly_int, tilesize):
        lrx = i+tilesize
        lry = j-tilesize
        tile_ext=[]
        tile_ext.append(i)
        tile_ext.append(j)
        tile_ext.append(lrx)
        tile_ext.append(lry)
        tiles_all.append(tile_ext)

# check if tile intersect with data outline
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(i, j)
        ring.AddPoint(i, lry)
        ring.AddPoint(lrx, lry)
        ring.AddPoint(lrx, j)
        ring.AddPoint(i, j)
        extentGeometry = ogr.Geometry(ogr.wkbPolygon)
        extentGeometry.AddGeometry(ring)
        vector = ogr.Open(inputdata_extent)
        layer = vector.GetLayer()
        feature = layer.GetFeature(1)
        vectorGeometry = feature.GetGeometryRef()
        
        polygon_points = []
        polygon_points.append([i, j])
        polygon_points.append([i, lry])
        polygon_points.append([lrx, lry])
        polygon_points.append([lrx, j])
        polygon_points.append([i, j])
        tiles_polygon.append(Polygon(polygon_points))
        if extentGeometry.Intersect(vectorGeometry) == True:
            tiles.append(tile_ext)
            tiles_polygon_select.append(Polygon(polygon_points))
        del vector
polygon=[]
for x in tiles_polygon:
    polygon.append(geopandas.GeoDataFrame(crs=f'epsg:{str(out_srs)}', geometry=[x]))
df_polygons = pandas.concat(polygon)        
df_polygons.to_file(filename=os.path.join(dir_vrt,'polygon.gpkg'), driver="GPKG")
polygon=[]
for x in tiles_polygon_select:
    polygon.append(geopandas.GeoDataFrame(crs=f'epsg:{str(out_srs)}', geometry=[x]))
df_polygons = pandas.concat(polygon)        
df_polygons.to_file(filename=os.path.join(dir_vrt,'polygon_select.gpkg'), driver="GPKG")
print(f'all tiles: {len(tiles_all)}')
print(f'selected tiles: {len(tiles)}')

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

# Function to clip nodata values from raster files
def clip_nodata(input, nodata_value, cutline_dir = None):
    input_path = os.path.dirname(input)
    input_name = os.path.basename(input)
    if cutline_dir is None:
        cutline_dir = input_path
    rename = os.path.join(input_path, f"{input_name.split('.')[0]}_rename.{input_name.split('.')[-1]}")
    os.rename(input, rename)
    mask_tif = os.path.join(input_path, f"{input_name.split('.')[0]}_mask.{input_name.split('.')[-1]}")
    cutline = os.path.join(cutline_dir,f"{input_name.split('.')[0]}.gpkg")
    print(cutline)
   
    dataset = gdal.Open(rename)
    
    # Create a mask for nodata values across all bands
    band_count = dataset.RasterCount
    driver = gdal.GetDriverByName("GTiff")
    
    out_ds = driver.Create(
        mask_tif,
        dataset.RasterXSize,
        dataset.RasterYSize,
        1,
        gdal.GDT_Byte,
        options=["TILED=YES", "COMPRESS=DEFLATE"]
    )
    out_ds.SetGeoTransform(dataset.GetGeoTransform())
    out_ds.SetProjection(dataset.GetProjection())

    # Read nodata values and create a mask
    block_size = 1024

    for y in range(0, dataset.RasterYSize, block_size):
        rows = min(block_size, dataset.RasterYSize - y)
        for x in range(0, dataset.RasterXSize, block_size):
            cols = min(block_size, dataset.RasterXSize - x)
            band_list = []
            for band in range(1, band_count + 1):
                b = dataset.GetRasterBand(band).ReadAsArray(x, y, cols, rows)
                band_list.append(b == pandas.to_numeric(nodata_value))
            mask = numpy.logical_and.reduce(band_list).astype(numpy.uint8)
            out_ds.GetRasterBand(1).WriteArray(mask, x, y)
    out_ds.GetRasterBand(1).SetNoDataValue(1)
    out_ds = None
    dataset = None

    # Create a cutline from the mask
    gdalcontour_String = f'gdal_contour -p -fl 1 -b 1 -f "GPKG" {mask_tif} {cutline}'
    subprocess.run(gdalcontour_String, shell=True)
    # repair invalid geometries in the cutline
    gdf = geopandas.read_file(cutline, layer='contour')
     # Simplifying contour polygon to reduce number of vertices
    simplified_geometries = []
    # Apply the simplification function to each geometry in the GeoDataFrame
    for geometry in gdf['geometry']:
        # For MultiPolygon, simplify each individual Polygon in the MultiPolygon
        simplified_multipolygon = MultiPolygon([simplify_by_angle(p) for p in geometry.geoms])
        simplified_geometries.append(simplified_multipolygon)
    gdf['geometry'] = simplified_geometries
    gdf['geometry'] = gdf['geometry'].apply(make_valid)
    # gdf['geometry'] = gdf['geometry'].apply(remove_inner_rings).apply(make_valid).apply(remove_inner_rings)
    # Save the modified geodata frame back to the file
    gdf.to_file(cutline, layer='contour', driver="GPKG")
    
    if nodata_value == '0':
        src = rasterio.open(rename) 
        dtype = src.dtypes[0]
        # dst_nodata = numpy.iinfo(dtype).max
        dst_nodata = -9999
        print(f"Using nodata value: {dst_nodata} for dtype: {dtype}")
        src.close()
    else:
        dst_nodata = 0
    
    gdalwarpString = f"gdalwarp -overwrite -of COG -srcnodata None -dstnodata {dst_nodata} -co COMPRESS=ZSTD -co PREDICTOR=2 -co BIGTIFF=YES --config OVERVIEW_COMPRESS ZSTD -co OVERVIEW_PREDICTOR=2 -co OVERVIEW_RESAMPLING=average -co OVERVIEW_QUALITY=50  -cutline {cutline} -cl contour -crop_to_cutline {rename} {input}"
    print(gdalwarpString)
    subprocess.run(gdalwarpString, shell=True)

    # Clean up temporary files
    os.remove(mask_tif)
    os.remove(rename)

def tiling(input, out_path, extent, count_bands, tile_size, x_res, y_res, nodata_clip_option=None, nodata_value=None):
    i = 1
    bands = []
    while i < count_bands + 2:
        x = f'-b {str(i)}'
        bands.append(x)
        i += 1
    # bands from raw data
    bands = ' '.join(bands[0:count_bands])
    output_name = f"{tile_name}_{extent[0]}_{extent[3]}"
    output = os.path.join(out_path, f"{output_name}.tif")

    # if tile size divided by raster resolution is float the raster cell size needs to be adjusted to prevent empty rows/column between tiles
    resamp_method ='nearest'
    cell_count_x = tile_size/x_res # number of pixels per row
    cell_count_y = tile_size/y_res # number of pixels per column
    if (cell_count_x).is_integer() == False or (cell_count_y).is_integer()== False:
        x1 = cell_count_x - int(cell_count_x) # get remaining pixel
        x2 = x1*x_res # get remainder in crs unit (e.g. metre)
        x3 = x2/int(cell_count_x) # remainder per pixel cell
        x_res = x_res + x3 # new cell size = original cell size + remainder per pixel cell
        y1 = cell_count_y - int(cell_count_y) # get remaining pixel
        y2 = y1*y_res # get remainder in crs unit (e.g. metre)
        y3 = y2/int(cell_count_y) # remainder per pixel cell
        y_res = y_res + y3 # new cell size = original cell size + remainder per pixel cell
        resamp_method = 'rms'

    # images will be compressed lossless with ZSTD compression 
    # overviews of the 8-bit images can be created with the more space-saving JPEG compression
        # JPEG compression can cause the problem of empty cells in dark areas if that happens use deflate
        # the overview compression method of 16-bit-images is DEFLATE
    if dtype == 'Byte':
        comp = 'ZSTD'
    else:
        comp = 'ZSTD'
    
    if not os.path.isfile(output): #calculate file just if it exists
        gdaltranString = f'gdal_translate -q -of COG -co COMPRESS={comp} -co PREDICTOR=2 -r {resamp_method} -a_srs EPSG:{str(out_srs)} {bands} -tr {str(x_res)} {str(y_res)} -co BIGTIFF=YES --config GDAL_TIFF_INTERNAL_MASK YES -co OVERVIEWS=IGNORE_EXISTING -co OVERVIEW_COMPRESS={comp} -co OVERVIEW_PREDICTOR=2 -co OVERVIEW_RESAMPLING=average -co OVERVIEW_QUALITY=50 -projwin {str(extent[0])}, {str(extent[1])}, {str(extent[2])}, {str(extent[3])} {input} {output}'
        subprocess.run(gdaltranString, shell=True)
        print(gdaltranString)

    # create polygon from data extent
    outline = os.path.join(dir_footprint, f"{output_name}.gpkg")
    if not os.path.isfile(outline): #calculate file just if it exists
        gdalvectorString = f'gdal_contour -q -fl 0 -b 1 -f "GPKG" -p {output} {outline}'
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
    
    if nodata_clip_option == 1:
        if not df.empty:
        #     os.remove(outline)
        #     # os.remove(output)
        # else:          
            footprint = os.path.join(dir_footprint, f"{output_name}_footprint.gpkg")
            gdalindex_string = f'gdaltindex -tileindex location -lyr_name footprint {footprint} {output}'
            subprocess.run(gdalindex_string, shell=True)
            # clip nodata values from raster tiles
            clip_nodata(output, nodata_value, cutline_dir=dir_footprint)
            df = geopandas.read_file(outline, layer='contour')
    if 'location' not in df.columns:
        df.insert(1, 'location', output)
        df.to_file(outline, layer='contour', driver='GPKG')  


# ###############
# create 2x2 km cog tiles from temporary vrt that was created from input data  
if __name__ == '__main__':
    count = mp.cpu_count()
    pool = mp.Pool(count-count+4)
    args = [(vrt_temp, dir_cog, x, band_count, tilesize, xres, yres, nodata_clip_option, nodata_value) for x in tiles]
    pool.starmap(tiling, args)
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


    # build vrt from cog tiles
    dir_cog = pathlib.Path(dir_cog)
    input_windows_path = dir_cog.rglob("*.tif")
    tif = []
    for x in input_windows_path:
        tif.append(str(x))
    tile_sample = tif[0]
    tif= '\n'.join(tif)

    with open(input_list_txt, 'w') as file:
        file.write(tif)
        file.close()
    vrt = os.path.join(path_out, f"{vrt_name}.vrt")
    
    if nodata_clip_option == 1:
        dataset = gdal.Open(tile_sample)
        nodata_value = dataset.GetRasterBand(1).GetNoDataValue()
        
        nodata_list = []
        i = 1
        while i < band_count+1:
            nodata_list.append(str(int(nodata_value)))
            i += 1
        nodata_list = ' '.join(nodata_list)
        print(f'nodata_list exists: {nodata_list}')
    
    try:
        nodata_list #check if nodata list exists
        
    except NameError:
        buildvrtString = f'gdalbuildvrt -overwrite -input_file_list {input_list_txt} {vrt}'
    else:
        # if nodata value is defined it will be used as source nodata
        buildvrtString = f'gdalbuildvrt -srcnodata "{ " ".join(nodata_list) }" -overwrite -input_file_list {input_list_txt} {vrt}'
    subprocess.run(buildvrtString, shell=True)


    # # create vrt overviews
    level = [16, 2, 2, 2, 2, 2]
    ovr_list = []

    for x in level:
        if x == level[0]:
            gdaladdoString = f'gdaladdo -r average -ro --config GDAL_NUM_THREADS ALL_CPUS --config COPY_SRC_OVERVIEWS YES {vrt} {str(x)}'
            print(gdaladdoString)
            subprocess.run(gdaladdoString, shell=True)
            OVERVIEW_FILE = f'{vrt}.ovr'
            ovr_list.append(OVERVIEW_FILE)
            time_level = time.time()
        else:
            gdaladdoString = f'gdaladdo -r average -ro --config GDAL_NUM_THREADS ALL_CPUS --config COPY_SRC_OVERVIEWS YES {OVERVIEW_FILE} {str(x)}'
            print(gdaladdoString)
            subprocess.run(gdaladdoString, shell=True)
            OVERVIEW_FILE = f'{OVERVIEW_FILE}.ovr'
            ovr_list.append(OVERVIEW_FILE)
            time_level = time.time()
            ovr_tif =[]

    for x in ovr_list:
        x_split = x.split('.vrt.ovr')
        new_name =  f'{x_split[0]}2.tif{x_split[1]}'
        os.rename(x, new_name)
        ovr_tif.append(new_name)

    ovr = ovr_tif[0]

    ds = gdal.Open(ovr)
    ds.SetProjection(f'EPSG:{str(out_srs)}')
    ds.SetGeoTransform([ulx, level[0]*xres, 0, uly, 0, level[0]*yres])
    ds = None
    gdaltransString = f'gdal_translate {ovr} {vrt[:-4]}.tif -co COMPRESS=ZSTD -co BIGTIFF=YES -co COPY_SRC_OVERVIEWS=YES --config OVERVIEW_COMPRESS ZSTD --config GDAL_NUM_THREADS ALL_CPUS'
    subprocess.run(gdaltransString, shell=True)
    ovr_final = f'{vrt[:-4]}.vrt.ovr'
    os.rename(f'{vrt[:-4]}.tif', ovr_final)
    for x in ovr_tif:
        os.remove(x)
    os.remove(f'{ovr}.aux.xml')

    #remove temporary layers
    vector_list = glob(os.path.join(dir_footprint, '*'))
    for x in vector_list:
        if x != extent:
            os.remove(x)

    delete_list = glob(os.path.join(dir_vrt, '*'))
    for x in delete_list:
        if not x in (vrt, ovr_final):
            openfile = open(x)
            openfile.close()
            print(x)
            os.remove(x)
    os.removedirs(dir_vrt)

    hours, rem = divmod(time.time() - start_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print("{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))
    if warning != '':
        print(warning)