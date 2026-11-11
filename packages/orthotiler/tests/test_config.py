from orthotiler import OrthoConfig

config = OrthoConfig(
    input_dir=r"D:\Orthofotos\Eingang",
    output_dir=r"D:\Orthofotos\Ausgang",

    tile_name="ni_flugzeug_2026_harz_np_dop",

    output_srs=25832,

    tile_width=2000,
    tile_height=2000,

    nodata_value="0",
    nodata_clip=False,

    workers=6,
)

config.create_output_directories()