import rasterio
import numpy as np
from scipy import ndimage

input_file = r"\\lb-srv\fern_1\luftbild\ni\flugzeug\2012\ankum_nlf_fe\dop\daten\kacheln\ni_flugzeug_2012_ankum_nlf_fe_dop_354000_5824000_mask.tif"
output_file = r"\\lb-srv\fern_1\luftbild\ni\flugzeug\2012\ankum_nlf_fe\dop\daten\kacheln\ni_flugzeug_2012_ankum_nlf_fe_dop_354000_5824000_mask_cleaned.tif"

with rasterio.open(input_file) as src:
    mask = src.read(1)
    profile = src.profile.copy()

# Identify NoData pixels (value 1)
nodata = mask == 1

# Label connected NoData regions
labels, num = ndimage.label(nodata)

# Identify regions touching raster boundaries
boundary_labels = np.unique(np.concatenate([
    labels[0, :],
    labels[-1, :],
    labels[:, 0],
    labels[:, -1]
]))

# Count pixels in each region
counts = np.bincount(labels.ravel())

# Select enclosed NoData regions smaller than 20 pixels
small_holes = (
    (counts < 20) &
    (~np.isin(np.arange(len(counts)), boundary_labels)) &
    (np.arange(len(counts)) != 0)
)

# Replace small holes with background value 0
cleaned = mask.copy()
cleaned[small_holes[labels]] = 0

# Save raster
with rasterio.open(output_file, "w", **profile) as dst:
    dst.write(cleaned, 1)