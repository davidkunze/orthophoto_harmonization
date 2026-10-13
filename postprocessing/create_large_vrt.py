import os
import pathlib
from osgeo import gdal
import subprocess

# build vrt from cog tiles

dir_cog = r"\\lb-srv\fern_2\luftbild\he\flugzeug\2023\he_lverm\tdop\daten\kacheln"
dir_cog = pathlib.Path(dir_cog)
input_windows_path = dir_cog.rglob("*.tif")
tif = []
for x in input_windows_path:
    tif.append(str(x))
tile_sample = tif[0]
tif= '\n'.join(tif)

path_out = r"\\lb-srv\fern_2\luftbild\he\flugzeug\2023\he_lverm\tdop\daten"
vrt_name = "he_flugzeug_2023_he_lverm_tdop"
nodata_list = ["0", "0", "0", "0"]

input_list_txt = os.path.join(path_out, "input_list.txt")

with open(input_list_txt, 'w') as file:
    file.write(tif)
    file.close()
vrt = os.path.join(path_out, f"{vrt_name}.vrt")

buildvrtString = f'gdalbuildvrt -srcnodata "{ " ".join(nodata_list) }" -overwrite -input_file_list {input_list_txt} {vrt}'
subprocess.run(buildvrtString, shell=True)
