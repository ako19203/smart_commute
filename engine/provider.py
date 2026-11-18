from engine.routing import (
    get_osrm_route,
    get_distance_matrix,
)


class RoutingProvider:
    """
    Base routing provider interface.
    """

    def get_route(self, points):
        raise NotImplementedError

    def get_distance_matrix(self, points):
        raise NotImplementedError


class OSRMProvider(RoutingProvider):
    """
    OSRM implementation.
    """

    def get_route(self, points):
        return get_osrm_route(points)

    def get_distance_matrix(self, points):
        return get_distance_matrix(points)