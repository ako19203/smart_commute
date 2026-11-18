from runtime.state_store import StateStore
from runtime.session_manager import SessionManager
from runtime.event_bus import EventBus
from runtime.runtime_manager import RuntimeManager


# =====================================================
# Setup Runtime Components
# =====================================================

state_store = StateStore()

session_manager = SessionManager(state_store)

event_bus = EventBus()

runtime_manager = RuntimeManager(
    session_manager=session_manager,
    event_bus=event_bus,
)


# =====================================================
# Event Handlers
# =====================================================

def handle_gps_update(payload):
    print("\nGPS UPDATE EVENT:")
    print(payload)


def handle_state_update(payload):
    print("\nSESSION STATE UPDATED EVENT:")
    print(payload)


def handle_progress_update(payload):
    print("\nROUTE PROGRESS UPDATED EVENT:")
    print(payload)


def handle_deviation_check(payload):
    print("\nDEVIATION CHECK EVENT:")
    print(payload)


def handle_off_route(payload):
    print("\nOFF ROUTE DETECTED EVENT:")
    print(payload)


def handle_reroute(payload):
    print("\nROUTE REROUTED EVENT:")
    print(payload)


def handle_trigger_evaluation(payload):
    print("\nTRIGGER EVALUATED EVENT:")
    print(payload)


def handle_commute_alert(payload):
    print("\nCOMMUTE ALERT TRIGGERED EVENT:")
    print(payload)


# =====================================================
# Subscribe To Events
# =====================================================

event_bus.subscribe(
    "GPS_UPDATE_RECEIVED",
    handle_gps_update
)

event_bus.subscribe(
    "SESSION_STATE_UPDATED",
    handle_state_update
)

event_bus.subscribe(
    "ROUTE_PROGRESS_UPDATED",
    handle_progress_update
)

event_bus.subscribe(
    "DEVIATION_CHECK_COMPLETED",
    handle_deviation_check
)

event_bus.subscribe(
    "OFF_ROUTE_DETECTED",
    handle_off_route
)

event_bus.subscribe(
    "ROUTE_REROUTED",
    handle_reroute
)

event_bus.subscribe(
    "TRIGGER_EVALUATED",
    handle_trigger_evaluation
)

event_bus.subscribe(
    "COMMUTE_ALERT_TRIGGERED",
    handle_commute_alert
)


# =====================================================
# Create Active Session
# =====================================================

session = runtime_manager.start_session(
    session_id="session_001",

    origin_coordinates=(12.9716, 77.5946),

    destination_name="Office",

    destination_coordinates=(12.9352, 77.6245),
)

print("SESSION CREATED:")
print(session)


# =====================================================
# Simulated GPS Update
# =====================================================
# Intentionally away from route
# to trigger:
# - deviation
# - rerouting
# - trigger evaluation
# =====================================================

updated_session = runtime_manager.process_gps_update(
    session_id="session_001",
    latitude=12.9500,
    longitude=77.5700,
    speed_mps=18.0,
)

print("\nUPDATED SESSION:")
print(updated_session)