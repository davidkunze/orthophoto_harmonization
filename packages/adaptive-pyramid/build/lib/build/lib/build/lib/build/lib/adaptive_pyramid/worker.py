import rasterio


def read_window(
    filename,
    window,
    out_shape
):

    with rasterio.open(filename) as src:

        data = src.read(
            1,
            window=window,
            out_shape=out_shape
        )

    return data