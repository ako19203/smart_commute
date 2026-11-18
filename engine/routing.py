from pathlib import Path
from typing import List, Tuple

import json
import pickle
import threading
import time

import requests

from urllib.parse import urlencode
from urllib.request import urlopen


# =========================================================
# TYPES
# =========================================================

Coordinate = Tuple[float, float]
Matrix = List[List[float]]


# =========================================================
# CONFIG
# =========================================================

OSRM_BASE_URL = "http://localhost:5000"

OSRM_ROUTE_URL = f"{OSRM_BASE_URL}/route/v1/driving/"
OSRM_TABLE_URL = f"{OSRM_BASE_URL}/table/v1/driving/"

CACHE_FILE = Path(__file__).resolve().parent / "distance_cache.pkl"


# =========================================================
# CACHE
# =========================================================

_distance_cache_lock = threading.Lock()


def load_distance_cache(cache_path: Path = CACHE_FILE) -> dict:
    """
    Load cached distance matrices from disk.
    """

    if not cache_path.exists():
        return {}

    try:
        with cache_path.open("rb") as fh:
            data = pickle.load(fh)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def save_distance_cache(
    cache: dict,
    cache_path: Path = CACHE_FILE
) -> None:
    """
    Save distance cache to disk.
    """

    try:
        with cache_path.open("wb") as fh:
            pickle.dump(
                cache,
                fh,
                protocol=pickle.HIGHEST_PROTOCOL
            )

    except Exception:
        pass


_global_cache = load_distance_cache()


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _remap_matrix(
    matrix: Matrix,
    from_points: List[Coordinate],
    to_points: List[Coordinate]
) -> Matrix:
    """
    Reorder cached matrix into requested point ordering.
    """

    index_by_point = {
        point: idx
        for idx, point in enumerate(from_points)
    }

    return [
        [
            matrix[index_by_point[src]][index_by_point[dst]]
            for dst in to_points
        ]
        for src in to_points
    ]


# =========================================================
# ROUTE GEOMETRY
# =========================================================

def get_osrm_route(
    points: List[Coordinate]
) -> List[Coordinate]:
    """
    Fetch full road route geometry from OSRM.
    """

    if len(points) < 2:
        return points

    coordinates = ";".join(
        f"{lon},{lat}"
        for lat, lon in points
    )

    url = f"{OSRM_ROUTE_URL}{coordinates}"

    params = {
        "overview": "full",
        "geometries": "geojson",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        geometry = (
            response.json()["routes"][0]
            ["geometry"]["coordinates"]
        )

        return [
            (lat, lon)
            for lon, lat in geometry
        ]

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ):
        return points


# =========================================================
# DISTANCE MATRIX
# =========================================================

def build_distance_matrix_osrm(
    points: List[Coordinate],
    cache: dict
) -> Matrix:
    """
    Build NxN distance matrix using OSRM Table API.
    """

    canonical_points = sorted(points)

    matrix_key = (
        "matrix",
        tuple(canonical_points)
    )

    with _distance_cache_lock:
        cached_matrix = cache.get(matrix_key)

    if cached_matrix is not None:

        return _remap_matrix(
            cached_matrix,
            canonical_points,
            points
        )

    coordinates = ";".join(
        f"{lon},{lat}"
        for lat, lon in canonical_points
    )

    url = (
        f"{OSRM_TABLE_URL}{coordinates}?"
        f"{urlencode({'annotations': 'distance'})}"
    )

    started_at = time.perf_counter()

    last_error = None

    for attempt in range(3):

        try:
            print(
                f"OSRM TABLE → "
                f"{len(points)} points "
                f"(attempt {attempt + 1})"
            )

            with urlopen(url, timeout=20) as response:
                payload = json.load(response)

            if payload.get("code") != "Ok":
                raise RuntimeError(
                    f"OSRM error: "
                    f"{payload.get('code')}"
                )

            distances = payload.get("distances")

            if not isinstance(distances, list):
                raise RuntimeError(
                    "Invalid OSRM matrix response"
                )

            matrix = []

            for row in distances:

                if any(value is None for value in row):
                    raise RuntimeError(
                        "Null matrix values returned"
                    )

                matrix.append([
                    float(value)
                    for value in row
                ])

            with _distance_cache_lock:

                cache[matrix_key] = matrix

                for i, point_a in enumerate(canonical_points):
                    for j, point_b in enumerate(canonical_points):

                        cache[(point_a, point_b)] = (
                            matrix[i][j]
                        )

            save_distance_cache(cache)

            print(
                f"Matrix built in "
                f"{time.perf_counter() - started_at:.2f} sec"
            )

            return _remap_matrix(
                matrix,
                canonical_points,
                points
            )

        except Exception as e:

            last_error = e

            print(f"Retry failed: {e}")

            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    raise RuntimeError(
        f"OSRM Table API failed: {last_error}"
    )


# =========================================================
# PUBLIC API
# =========================================================

def get_distance_matrix(
    points: List[Coordinate]
) -> Matrix:
    """
    Public wrapper for distance matrix generation.
    """

    return build_distance_matrix_osrm(
        points,
        _global_cache
    )


def route_distance_km(
    matrix: Matrix
) -> float:
    """
    Compute total route distance in km
    from sequential matrix traversal.
    """

    total = 0

    for i in range(len(matrix) - 1):
        total += matrix[i][i + 1]

    return round(total / 1000, 2)