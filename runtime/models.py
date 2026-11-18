from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, Dict, Any


# =========================================================
# Incoming GPS Packet
# =========================================================

@dataclass
class GPSUpdate:
    """
    Raw GPS update received from client/mobile device.
    """

    session_id: str

    latitude: float
    longitude: float

    speed_mps: float = 0.0
    heading: Optional[float] = None
    accuracy_meters: Optional[float] = None

    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def coordinates(self) -> Tuple[float, float]:
        return (self.latitude, self.longitude)


# =========================================================
# Route Progress State
# =========================================================

@dataclass
class RouteProgress:
    """
    Represents current progress along the active route.
    """

    progress_percent: float

    distance_travelled_meters: float
    distance_remaining_meters: float

    closest_route_index: int

    eta_minutes: float


# =========================================================
# Deviation Evaluation State
# =========================================================

@dataclass
class DeviationState:
    """
    Represents whether the user has deviated from route.
    """

    deviated: bool

    deviation_distance_meters: float

    deviation_confidence: float

    requires_reroute: bool


# =========================================================
# Trigger Evaluation Output
# =========================================================

@dataclass
class TriggerDecision:
    """
    Final trigger decision produced by trigger engine.
    """

    should_alert: bool

    confidence: float

    eta_minutes: float

    reason: str

    trigger_threshold_minutes: Optional[float] = None


# =========================================================
# Central Runtime Session State
# =========================================================

@dataclass
class SessionState:
    """
    Single source of truth for an active commute session.
    """

    session_id: str

    # -----------------------------------------------------
    # Destination
    # -----------------------------------------------------

    destination_name: Optional[str] = None

    destination_coordinates: Optional[Tuple[float, float]] = None

    # -----------------------------------------------------
    # Live Location
    # -----------------------------------------------------

    current_location: Optional[Tuple[float, float]] = None

    current_speed_mps: float = 0.0

    last_updated: datetime = field(default_factory=datetime.utcnow)

    # -----------------------------------------------------
    # Route Information
    # -----------------------------------------------------

    route_geometry: Optional[list] = None

    route_distance_meters: float = 0.0

    eta_minutes: float = 0.0

    # -----------------------------------------------------
    # Progress Tracking
    # -----------------------------------------------------

    progress_percent: float = 0.0

    distance_remaining_meters: float = 0.0

    # -----------------------------------------------------
    # Deviation State
    # -----------------------------------------------------

    deviated: bool = False

    deviation_distance_meters: float = 0.0

    rerouting: bool = False

    # -----------------------------------------------------
    # Trigger Intelligence
    # -----------------------------------------------------

    trigger_confidence: float = 0.0

    should_alert: bool = False

    last_trigger_reason: Optional[str] = None

    # -----------------------------------------------------
    # Session Lifecycle
    # -----------------------------------------------------

    active: bool = True

    created_at: datetime = field(default_factory=datetime.utcnow)


# =========================================================
# Runtime Event Schema
# =========================================================

@dataclass
class RuntimeEvent:
    """
    Generic runtime event emitted by event bus.
    """

    event_type: str

    session_id: str

    payload: Dict[str, Any]

    timestamp: datetime = field(default_factory=datetime.utcnow)