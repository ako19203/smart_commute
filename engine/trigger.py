from engine.provider import OSRMProvider


# =========================================================
# TRIGGER THRESHOLDS
# =========================================================

TRIGGER_THRESHOLDS = {
    "walking": 2,
    "bus": 5,
    "train": 8,
    "car": 4,
}


# =========================================================
# CONFIDENCE CONFIG
# =========================================================

TRIGGER_CONFIDENCE_THRESHOLD = 70


# =========================================================
# ETA CALCULATION
# =========================================================

def calculate_eta_minutes(
    distance_km: float,
    speed_kmh: float
) -> float:
    """
    Calculate ETA in minutes.

    Formula:
        ETA = distance / speed
    """

    if speed_kmh <= 0:
        return float("inf")

    eta_hours = distance_km / speed_kmh

    return eta_hours * 60


# =========================================================
# TRIGGER THRESHOLD
# =========================================================

def get_trigger_threshold(
    travel_mode: str
) -> float:
    """
    Get trigger threshold (minutes)
    based on travel mode.
    """

    return TRIGGER_THRESHOLDS.get(
        travel_mode,
        5
    )


# =========================================================
# REMAINING ROUTE DISTANCE
# =========================================================

def calculate_remaining_distance_km(
    provider,
    current_location,
    destination
) -> float:
    """
    Calculate remaining road distance
    between current location and destination.
    """

    points = [
        current_location,
        destination
    ]

    matrix = provider.get_distance_matrix(points)

    distance_meters = matrix[0][1]

    return distance_meters / 1000


# =========================================================
# TRIGGER CONFIDENCE ENGINE
# =========================================================

def calculate_trigger_confidence(
    eta_minutes,
    trigger_threshold_minutes,
    route_progress_percent,
    has_deviated,
    current_speed_kmh,
):
    """
    Compute contextual trigger confidence score.
    """

    confidence = 0

    # -----------------------------------------------------
    # ETA FACTOR
    # -----------------------------------------------------

    if eta_minutes <= trigger_threshold_minutes:
        confidence += 50

    elif eta_minutes <= (
        trigger_threshold_minutes * 1.5
    ):
        confidence += 30

    # -----------------------------------------------------
    # ROUTE PROGRESS FACTOR
    # -----------------------------------------------------

    if route_progress_percent >= 80:
        confidence += 30

    elif route_progress_percent >= 60:
        confidence += 20

    elif route_progress_percent >= 40:
        confidence += 10

    # -----------------------------------------------------
    # DEVIATION PENALTY
    # -----------------------------------------------------

    if has_deviated:
        confidence -= 40

    # -----------------------------------------------------
    # SPEED FACTOR
    # -----------------------------------------------------

    if current_speed_kmh >= 50:
        confidence += 10

    elif current_speed_kmh >= 30:
        confidence += 5

    # -----------------------------------------------------
    # CLAMP SCORE
    # -----------------------------------------------------

    confidence = max(0, min(100, confidence))

    return round(confidence, 2)


# =========================================================
# PURE TRIGGER DECISION ENGINE
# =========================================================

def evaluate_trigger_decision(
    eta_minutes,
    trigger_threshold_minutes,
    route_progress_percent,
    has_deviated,
    current_speed_kmh,
):
    """
    Evaluate final trigger decision
    using already-computed runtime context.
    """

    confidence_score = (
        calculate_trigger_confidence(
            eta_minutes=eta_minutes,

            trigger_threshold_minutes=(
                trigger_threshold_minutes
            ),

            route_progress_percent=(
                route_progress_percent
            ),

            has_deviated=has_deviated,

            current_speed_kmh=(
                current_speed_kmh
            ),
        )
    )

    should_trigger_alarm = (
        confidence_score
        >= TRIGGER_CONFIDENCE_THRESHOLD
    )

    return {

        "trigger_confidence_score": (
            confidence_score
        ),

        "should_trigger_alarm": (
            should_trigger_alarm
        ),
    }