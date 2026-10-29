def overview_plan(
    width,
    height,
    resolution,
    cog_level,
    target_pixels=3000
):

    """
    Bestimmt zusätzliche Overview-Level,
    die oberhalb der COG-Pyramiden notwendig sind.
    """


    levels = []

    current = max(
        width,
        height
    )


    level = 1


    while current > target_pixels:

        level *= 2

        if level > cog_level:

            levels.append(level)

        current = current / 2


    return levels