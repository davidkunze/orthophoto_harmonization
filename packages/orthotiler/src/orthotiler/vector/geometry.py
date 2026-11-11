
import numpy as np

from shapely.geometry import (
    Polygon,
    MultiPolygon,
)


def get_angles(vec_1, vec_2):
    """
    Calculates the angle between two 2D vectors in degrees.
    """

    vec_1_3d = np.array([
        vec_1[0],
        vec_1[1],
        0,
    ])

    vec_2_3d = np.array([
        vec_2[0],
        vec_2[1],
        0,
    ])

    dot = np.dot(
        vec_1_3d,
        vec_2_3d,
    )

    det = np.cross(
        vec_1_3d,
        vec_2_3d,
    )[2]

    angle_in_rad = np.arctan2(
        det,
        dot,
    )

    return np.degrees(angle_in_rad)


def simplify_by_angle(
    poly_in,
    deg_tol=1,
):
    """
    Removes unnecessary vertices along straight polygon edges.

    Vertices are retained when the angle between consecutive
    vectors exceeds the specified tolerance.

    Parameters
    ----------
    poly_in : Polygon
        Input polygon.

    deg_tol : float
        Angular tolerance in degrees.

    Returns
    -------
    Polygon
        Simplified polygon.
    """

    ext_poly_coords = poly_in.exterior.coords[:]

    vector_rep = np.diff(
        ext_poly_coords,
        axis=0,
    )

    num_vectors = len(vector_rep)

    angles_list = []

    for i in range(num_vectors):

        angles_list.append(
            np.abs(
                get_angles(
                    vector_rep[i],
                    vector_rep[(i + 1) % num_vectors],
                )
            )
        )

    # Identify vertices exceeding the angular tolerance
    thresh_vals_by_deg = np.where(
        np.array(angles_list) > deg_tol
    )

    new_idx = list(
        thresh_vals_by_deg[0] + 1
    )

    new_vertices = [
        ext_poly_coords[idx]
        for idx in new_idx
    ]

    return Polygon(new_vertices)


def remove_inner_rings(geom):
    """
    Removes interior rings from Polygon and MultiPolygon geometries.

    Polygon boundaries are simplified using the angle-based
    simplification method.

    Other geometry types are returned unchanged.
    """

    if isinstance(geom, Polygon):

        geom = simplify_by_angle(geom)

        return Polygon(
            geom.exterior
        )

    elif isinstance(geom, MultiPolygon):

        geom = MultiPolygon([
            simplify_by_angle(p)
            for p in geom.geoms
        ])

        return MultiPolygon([
            Polygon(p.exterior)
            for p in geom.geoms
        ])

    else:

        return geom
