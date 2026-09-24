import os
import sys
from glob import glob
import pathlib
import multiprocessing as mp
import time
import fiona
# from shapely.geometry import Point, LineString, Polygon
# import geopandas
import pandas
# import numpy
import subprocess
# import rasterio
# import rioxarray as rxr
from osgeo import gdal, osr, ogr
gdal.UseExceptions()

start_time = time.time()

path_data = r'\\lb-srv\LB-Z-Temp\David\vrt_cog\testdaten\bobenwald_sgb3\dop\daten\kacheln'
path_out = path_data
# naming scheme for tiles: bundesland_tragersystem_jahr_gebiet_datentyp_auftrageber_x-wert_y-wert
    # For abbreviations open "\\lb-server\LB-Projekte\SGB4_InterneVerwaltung\EDV\KON-GEO\2024\vrt_benennung\vrt_benennung.txt"
    # x-wert und y-wert will be added later
tile_name = 'ni_flugzeug_2020_bobenwald_sgb3_dop'
# naming scheme for vrt: bundesland_tragersystem_jahr_gebiet_datentyp_auftrageber
    # similar to folder structure see "Z:\SGB4_InterneVerwaltung\EDV\KON-GEO\2024\neustrukturierung_laufwerk_fernerkundung\Übersicht_Neustrukturierung_Laufwerke_nach_BL_Trägersystem_Jahr_Gebiet_20240130.docx"

vrt_name = tile_name
out_srs = 25832


# path_meta = os.path.join(os.path.dirname(path_data),"doku")
cog_folder = path_data
footprint_folder = 'kacheluebersicht'

dir_cog = os.path.join(path_out, cog_folder)
dir_vrt = os.path.dirname(path_data)
dir_footprint = os.path.join(path_out,footprint_folder)

def create_folder(output_f, folder_name):
    if not os.path.isdir(os.path.join(output_f, folder_name)):
        os.mkdir(os.path.join(output_f, folder_name))
# create_folder(path_data, vrt_folder)

#get all cog-tiles
dir_cog = pathlib.Path(dir_cog)
input_windows_path = dir_cog.rglob("*.tif")
tif = []
for x in input_windows_path:
    tif.append(str(x))
tile_sample = tif[0]
tif= '\n'.join(tif)

input_list_txt = os.path.join(dir_vrt, 'input_list.txt')
with open(input_list_txt, 'w') as file:
    file.write(tif)
    file.close()

vrt = os.path.join(dir_vrt, vrt_name + '.vrt')
buildvrtString = 'gdalbuildvrt -overwrite -input_file_list '+ input_list_txt + ' ' + vrt
subprocess.run(buildvrtString)

level = [16, 32, 64, 128, 256, 512]
ovr_list = []

gdaladdoString = f'gdal raster overview add --levels {','.join([str(x) for x in level])} --resampling average --config GDAL_NUM_THREADS ALL_CPUS --config COPY_SRC_OVERVIEWS YES --config OVERVIEW_COMPRESS ZSTD  {vrt}'
print(gdaladdoString)
subprocess.run(gdaladdoString)

ovr = vrt + '.ovr'
ovr_tif = ovr.split('.vrt.ovr')[0]+'_2.tif'
os.rename(ovr, ovr_tif)

vrt_ds = gdal.Open(vrt)
ulx, xres, xskew, uly, yskew, yres  = vrt_ds.GetGeoTransform()

ds = gdal.Open(ovr_tif)
ds.SetProjection('EPSG:'+str(out_srs))
ds.SetGeoTransform([ulx, level[0]*xres, 0, uly, 0, level[0]*yres])
ds = None
gdaltransString = 'gdal_translate ' + ovr_tif + ' ' + vrt[:-4]+ '.tif' + ' -co COMPRESS=ZSTD -co BIGTIFF=YES -co COPY_SRC_OVERVIEWS=YES --config OVERVIEW_COMPRESS ZSTD --config GDAL_NUM_THREADS ALL_CPUS' 
subprocess.run(gdaltransString)
ovr_final = vrt[:-4]+'.vrt.ovr'
os.rename(vrt[:-4]+ '.tif',ovr_final)

os.remove(input_list_txt)
os.remove(ovr_tif)


hours, rem = divmod(time.time() - start_time, 3600)
minutes, seconds = divmod(rem, 60)
print("{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))
