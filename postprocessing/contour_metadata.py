from pathlib import Path
import os
import geopandas as gpd
import pandas as pd
import subprocess
import shutil
from glob import glob
from osgeo import gdal
# Problem with Fiona and GDAL on Windows if other software (e.g., PCI Geomatics) is installed that also uses packages like gdal or fiona.
os.environ["PATH"] = os.pathsep.join(
    p for p in os.environ["PATH"].split(os.pathsep)
    if not p.lower().startswith("c:\\pci geomatics\\")
)
import fiona

# retiles = gpd.read_file(r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\daten\temp\retile.gpkg")

# for index, row in retiles.iterrows():
#     name = os.path.basename(row["location"])
#     input_path = r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\daten\temp\translate\kacheln"
#     tif = os.path.join(input_path, name)
    
#     # comp = "ZSTD"
#     # resamp_method = "rms"
#     # gdaltranString = f'gdal_translate -q -a_nodata 0 -of COG -co COMPRESS={comp} -co PREDICTOR=2 -r {resamp_method} -co BIGTIFF=YES --config GDAL_TIFF_INTERNAL_MASK YES -co OVERVIEWS=IGNORE_EXISTING -co OVERVIEW_COMPRESS={comp} -co OVERVIEW_PREDICTOR=2 -co OVERVIEW_RESAMPLING=average -co OVERVIEW_QUALITY=50 {row["location"]} {output}'
#     # subprocess.run(gdaltranString, shell=True)
    
#     out_path = r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\daten\temp\translate\kacheluebersicht"
#     gpkg = os.path.join(out_path, name[:-4] + '.gpkg')
    
#     gdalvectorString = f'gdal_contour -q -fl 0 -b 1 -f "GPKG" -p {tif} {gpkg}'
#     print(gdalvectorString)
#     subprocess.run(gdalvectorString, shell=True)

path_data = r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\daten"
dir_footprint = os.path.join(path_data, "kacheluebersicht")
dir_cog = os.path.join(path_data, "kacheln")
path_meta = r"\\lb-srv\fern_2\luftbild\ni\flugzeug\2025\ni_lverm\tdop\doku"
tile_name = "ni_flugzeug_2025_ni_lverm_tdop"
vrt_name = f"{tile_name}.vrt"
nodata_clip_option = 0
out_srs = 25832

vector_data = glob(os.path.join(dir_footprint, '*000.gpkg'))
tiles_valid = []
for x in vector_data:
    df = gpd.read_file(x, layer='contour')
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
df_merged = pd.concat(tiles_valid)
df_merged['geometry'] = df_merged['geometry'].make_valid()
df_merged.to_file(extent, layer='footprint_outline', driver="GPKG")
# dissolve tile outlines to dataset outline
df_outline = df_merged.dissolve(by='ID')
df_outline['location'] = os.path.join(path_data, f"{vrt_name}.vrt")
df_outline['geometry'] =df_outline['geometry'].make_valid()
df_outline.to_file(extent, layer='outline', driver="GPKG")
# get all 2x2 km tiles which contain data
# if nodata_clip_option == 1:
#     footprints = glob(os.path.join(dir_footprint, '*footprint.gpkg'))
#     tiles_footprint = []
#     for x in footprints:
#         df = gpd.read_file(x, layer='footprint')
#         tiles_footprint.append(df)
#     extent = os.path.join(dir_footprint, f'{tile_name}_extent.gpkg')
#     df_footprint = pd.concat(tiles_footprint)
#     df_footprint.to_file(extent, layer='footprints', driver="GPKG") 
# else:
gdalindex_string = f'gdaltindex -tileindex location -lyr_name footprints {extent} {os.path.join(dir_cog)}/*.tif'
subprocess.run(gdalindex_string, shell=True)


# read metadaten files
metadata = glob(os.path.join(path_meta, '*.csv'))
metadata = pd.read_csv(metadata[0], sep='\r\n', skip_blank_lines=True, header=None, encoding='utf-8', engine='python')
metadata = metadata.values.flatten().tolist()

# add metadata to vector tiles
def insert_medata(file):
    layers = fiona.listlayers(file)
    for table in layers:
        dataframe = gpd.read_file(file, layer=table)
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
