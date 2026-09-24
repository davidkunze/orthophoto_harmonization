import os
from osgeo import gdal
import subprocess

# Define the folder paths for CIR and RGB images
cir_folder = r"\\lb-srv\LB-Ortho\ni\nwfva\ortho_2010\solling_nlf_fe\daten\cir\tiff"
rgb_folder = r"\\lb-srv\LB-Ortho\ni\nwfva\ortho_2010\solling_nlf_fe\daten\rgb\tiff"
output_folder= r"\\lb-srv\LB-Projekte\fernerkundung\luftbild\ni\flugzeug\2010\solling_nlf_fe\dop\daten\rohdaten"

# Get a list of all CIR images in the CIR folder
cir_images = [f for f in os.listdir(cir_folder) if f.lower().endswith(('.tif'))]  # Adjust to ECW extension



def merge_rgb_and_cir(rgb_image, cir_image, output_image):
    temp = output_image[:-4]+'_temp.tif'
    mergeString = 'gdal_merge -separate -o '+ temp+' '+ rgb_image+' '+ cir_image
    print(mergeString)
    subprocess.run(mergeString)
    translateString = 'gdal_translate -of GTiff -b 1 -b 2 -b 3 -b 5 '+ temp+' '+ output_image
    subprocess.run(translateString)
    os.remove(temp)

    # Call the function to merge the images
# Iterate over each CIR image
for cir_image_name in cir_images:
    
    # Construct the corresponding RGB image path using the same base filename
    base_filename = os.path.splitext(cir_image_name)[0]  # Get the base filename without extension
    rgb_image_name = 'ef'+base_filename[3:] + ".tif"  # Assuming RGB image has '_rgb' suffix
    cir_image_path = os.path.join(cir_folder, cir_image_name)
    rgb_image_path = os.path.join(rgb_folder, rgb_image_name)
    # print(cir_image_path)
    # print(rgb_image_path)
    output_image_path = os.path.join(output_folder, base_filename + "_rgbi.tif")  # New file with '_rgb_i' suffix
    # print(output_image_path)
    merge_rgb_and_cir(rgb_image_path, cir_image_path, output_image_path)


    # Check if the corresponding RGB image exists
    # if os.path.exists(rgb_image_path):
    #     # Open the CIR image (ECW format, should have 3 bands: NIR, Red, Green)
    #     ds_cir = gdal.Open(cir_image_path)

        # Open the RGB image (assumed to have 3 bands: Red, Green, Blue)
        # ds_rgb = gdal.Open(rgb_image_path)

        # # Check if image sizes match
        # if ds_cir.RasterXSize != ds_rgb.RasterXSize or ds_cir.RasterYSize != ds_rgb.RasterYSize:
        #     print(f"Image sizes do not match for {base_filename}. Skipping...")
        #     ds_cir = None
        #     ds_rgb = None
        #     continue

        # # Read the individual bands of CIR image (assuming 3 bands: NIR, Red, Green)
        # nir_band = ds_cir.GetRasterBand(1)  # Band 1: NIR (near-infrared)
        # red_band = ds_cir.GetRasterBand(2)  # Band 2: Red
        # green_band = ds_cir.GetRasterBand(3)  # Band 3: Green

        # # Read the individual bands of RGB image (assuming 3 bands: Red, Green, Blue)
        # rgb_red_band = ds_rgb.GetRasterBand(1)  # Band 1: Red
        # rgb_green_band = ds_rgb.GetRasterBand(2)  # Band 2: Green
        # rgb_blue_band = ds_rgb.GetRasterBand(3)  # Band 3: Blue

        # output_image_path = os.path.join(output_folder, base_filename + "_rgbi.tif")  # New file with '_rgb_i' suffix
        # mergString = 'gdal_merge.py -separate -o '+output_image_path+' '+ rgb_image_path+' -b 1 -b 2 -b 3 '+cir_image_path+' -b 1'
        # subprocess.run(mergString)
        # # Create a new output image (RGBI)
        # driver = gdal.GetDriverByName("GTiff")
        # output_image_path = os.path.join(output_folder, base_filename + "_rgbi.tif")  # New file with '_rgb_i' suffix
        # out_ds = driver.Create(output_image_path, ds_rgb.RasterXSize, ds_rgb.RasterYSize, 4, gdal.GDT_Byte)  # 4 bands: R, G, B, I

        # # Write the bands into the new image:
        # out_ds.GetRasterBand(1).WriteArray(rgb_red_band.ReadAsArray())  # Red (from RGB)
        # out_ds.GetRasterBand(2).WriteArray(rgb_green_band.ReadAsArray())  # Green (from RGB)
        # out_ds.GetRasterBand(3).WriteArray(rgb_blue_band.ReadAsArray())  # Blue (from RGB)
        # out_ds.GetRasterBand(4).WriteArray(nir_band.ReadAsArray())  # Infrared (from CIR)

        # # Copy georeference information from CIR image
        # out_ds.SetGeoTransform(ds_cir.GetGeoTransform())  # Set GeoTransform (affine transformation)
        # out_ds.SetProjection(ds_cir.GetProjection())  # Set projection information (e.g., EPSG code)

#         # Close datasets
#         ds_cir = None
#         ds_rgb = None
#         out_ds = None

#         print(f"RGBI image created for: {base_filename}")

#     else:
#         print(f"Corresponding RGB image not found for: {base_filename}")

# print("Processing complete.")

