import os
import numpy
import rasterio
from osgeo import gdal, gdal_array
from scipy import ndimage
import geopandas
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.validation import make_valid


# Creates an alpha band from a raster's NoData mask, supporting equality and threshold-based filtering across multiple bands. 
# Fills small enclosed NoData regions and optionally regions touching the raster boundary.
# Generates polygons of valid data areas and converts the resulting raster into a Cloud Optimized GeoTIFF (COG).


def create_alpha_mask(
    input,
    nodata_value,
    contour_dir=None,
    max_hole_size=20,
    connectivity=4,
    nodata_mode="equal",
    fill_boundary_holes=False
):
    # 0. Validate parameters
    if nodata_value in (None, ''):
        raise ValueError("NoData value must be defined.")
    if max_hole_size < 0:
        raise ValueError("max_hole_size must be >= 0.")
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8.")
    if nodata_mode not in ("equal", "less", "greater"):
        raise ValueError("nodata_mode must be 'equal', 'less' or 'greater'.")

    input_path = os.path.dirname(input)
    input_name = os.path.basename(input)
    if contour_dir is None:
        contour_dir = input_path
    os.makedirs(contour_dir, exist_ok=True)

    name, ext = os.path.splitext(input_name)
    mask_tif = os.path.join(input_path, f"{name}_mask.tif")
    temp_tif = os.path.join(input_path, f"{name}_alpha_temp.tif")
    temp_cog = os.path.join(input_path, f"{name}_alpha_temp_cog.tif")
    cutline = os.path.join(contour_dir, f"{name}.gpkg")

    # Open input raster
    dataset = gdal.Open(input, gdal.GA_ReadOnly)
    if dataset is None:
        raise ValueError(f"Could not open raster: {input}")

    band_count = dataset.RasterCount
    width = dataset.RasterXSize
    height = dataset.RasterYSize

    if any(
        dataset.GetRasterBand(i).GetColorInterpretation() == gdal.GCI_AlphaBand
        for i in range(1, band_count + 1)
    ):
        dataset = None
        raise ValueError("Input raster already contains an alpha band.")

    driver = gdal.GetDriverByName("GTiff")
    nodata = float(nodata_value)
    block_size = 1024

    # 1. Create NoData mask (0 = valid data, 1 = NoData)
    mask_ds = driver.Create(
        mask_tif, width, height, 1, gdal.GDT_Byte,
        options=["TILED=YES", "COMPRESS=DEFLATE"]
    )
    mask_ds.SetGeoTransform(dataset.GetGeoTransform())
    mask_ds.SetProjection(dataset.GetProjection())

    for y in range(0, height, block_size):
        rows = min(block_size, height - y)
        for x in range(0, width, block_size):
            cols = min(block_size, width - x)
            band_list = []

            for band_nr in range(1, band_count + 1):
                arr = dataset.GetRasterBand(band_nr).ReadAsArray(x, y, cols, rows)

                if nodata_mode == "equal":
                    band_mask = (
                        numpy.isnan(arr)
                        if numpy.isnan(nodata)
                        else arr == nodata
                    )
                elif nodata_mode == "less":
                    band_mask = arr < nodata
                elif nodata_mode == "greater":
                    band_mask = arr > nodata

                band_list.append(band_mask)

            # NoData only if all bands match the condition
            mask = numpy.logical_and.reduce(band_list).astype(numpy.uint8)
            mask_ds.GetRasterBand(1).WriteArray(mask, x, y)

    mask_ds.FlushCache()
    mask_ds = None

    # 2. Fill small NoData regions
    with rasterio.open(mask_tif, "r+") as src:
        mask = src.read(1)
        structure = (
            numpy.ones((3, 3), dtype=numpy.uint8)
            if connectivity == 8
            else numpy.array(
                [[0, 1, 0], [1, 1, 1], [0, 1, 0]],
                dtype=numpy.uint8
            )
        )

        labels, num_features = ndimage.label(mask == 1, structure=structure)

        boundary_labels = numpy.unique(
            numpy.concatenate([
                labels[0, :], labels[-1, :],
                labels[:, 0], labels[:, -1]
            ])
        )

        counts = numpy.bincount(labels.ravel())
        small_holes = counts <= max_hole_size

        # Exclude background
        small_holes[0] = False

        # Optionally exclude regions touching the raster boundary
        if not fill_boundary_holes:
            small_holes[boundary_labels] = False

        fill_pixels = small_holes[labels]
        mask[fill_pixels] = 0
        src.write(mask, 1)

        filled_regions = numpy.count_nonzero(small_holes)
        filled_pixels = numpy.count_nonzero(fill_pixels)

        print(
            f"Found {num_features} regions; "
            f"filled {filled_regions} regions "
            f"({filled_pixels} pixels)."
        )

    # 3. Generate polygons of valid data areas (only value 0)
    if os.path.exists(cutline):
        os.remove(cutline)

    with rasterio.open(mask_tif) as src:
        mask = src.read(1)
        transform = src.transform
        crs = src.crs
        polygons = []

        for geom, value in shapes(
            mask,
            mask=(mask == 0),
            transform=transform,
            connectivity=connectivity
        ):
            if value == 0:
                polygon = make_valid(shape(geom))
                if not polygon.is_empty:
                    polygons.append(polygon)

    gdf = geopandas.GeoDataFrame(geometry=polygons, crs=crs)
    gdf.to_file(cutline, layer="contour", driver="GPKG")
    print(f"Created {len(polygons)} valid data polygons.")

    # 4. Append alpha band to original raster
    dtype = dataset.GetRasterBand(1).DataType
    numpy_dtype = numpy.dtype(gdal_array.GDALTypeCodeToNumericTypeCode(dtype))
    alpha_max = (
        numpy.iinfo(numpy_dtype).max
        if numpy.issubdtype(numpy_dtype, numpy.integer)
        else 1.0
    )

    out_ds = driver.Create(
        temp_tif, width, height, band_count + 1, dtype,
        options=["TILED=YES", "COMPRESS=DEFLATE"]
    )
    out_ds.SetGeoTransform(dataset.GetGeoTransform())
    out_ds.SetProjection(dataset.GetProjection())
    out_ds.SetMetadata(dataset.GetMetadata())

    alpha_band = out_ds.GetRasterBand(band_count + 1)
    alpha_band.SetColorInterpretation(gdal.GCI_AlphaBand)
    alpha_band.SetDescription("Alpha")

    with rasterio.open(mask_tif) as mask_src:
        for band_nr in range(1, band_count + 1):
            src_band = dataset.GetRasterBand(band_nr)
            dst_band = out_ds.GetRasterBand(band_nr)
            dst_band.SetMetadata(src_band.GetMetadata())
            dst_band.SetDescription(src_band.GetDescription())
            dst_band.SetColorInterpretation(src_band.GetColorInterpretation())

            if src_band.GetNoDataValue() is not None:
                dst_band.SetNoDataValue(src_band.GetNoDataValue())

            for y in range(0, height, block_size):
                rows = min(block_size, height - y)
                for x in range(0, width, block_size):
                    cols = min(block_size, width - x)
                    arr = src_band.ReadAsArray(x, y, cols, rows)
                    dst_band.WriteArray(arr, x, y)

        # Convert NoData mask to alpha values (0 = transparent, maximum = opaque)
        for y in range(0, height, block_size):
            rows = min(block_size, height - y)
            for x in range(0, width, block_size):
                cols = min(block_size, width - x)
                mask = mask_src.read(
                    1,
                    window=((y, y + rows), (x, x + cols))
                )
                alpha = numpy.where(mask == 1, 0, alpha_max).astype(numpy_dtype)
                alpha_band.WriteArray(alpha, x, y)

    out_ds.FlushCache()
    out_ds = None
    dataset = None

    # 5. Convert output to Cloud Optimized GeoTIFF
    result = gdal.Translate(
        temp_cog, temp_tif, format="COG",
        creationOptions=[
            "COMPRESS=ZSTD",
            "BIGTIFF=IF_SAFER",
            "OVERVIEWS=AUTO"
        ]
    )
    if result is None:
        raise RuntimeError("COG creation failed.")
    result = None

    os.replace(temp_cog, input)

    # 6. Remove temporary files
    for path in [mask_tif, temp_tif]:
        if os.path.exists(path):
            os.remove(path)

    print(f"Alpha band successfully created: {input}")
    print(f"Contour layer created: {cutline}")

    return cutline


# input_file = r"\\lb-srv\LB-Z-Temp\David\vrt_cog\testdaten\testdaten_addalphamask\test_1\cir_376_5814_rgbi.tif"
contour_directory = r"\\lb-srv\LB-Z-Temp\David\vrt_cog\testdaten\testdaten_addalphamask\test_1\contours"
# create_alpha(input_file, nodata_value=0, contour_dir=contour_directory, max_hole_size=20, connectivity=4)

input_file = r"\\lb-srv\LB-Z-Temp\David\vrt_cog\testdaten\ni_2012_abnkum_nlf_fe\dop\daten\a_rohdaten\cir_354_5824_rgbi.tif"
create_alpha_mask(input_file, nodata_value=0, max_hole_size=100, connectivity=4, nodata_mode="equal", fill_boundary_holes=False)