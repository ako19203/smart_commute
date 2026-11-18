from runtime.models import SessionState
from runtime.state_store import StateStore


# =====================================================
# Create Store
# =====================================================

store = StateStore()


# =====================================================
# Create Session
# =====================================================

session = SessionState(
    session_id="session_001",

    destination_name="Office",

    destination_coordinates=(12.9352, 77.6245),

    current_location=(12.9716, 77.5946),

    eta_minutes=18.5
)


# =====================================================
# Add Session
# =====================================================

store.add_session(session)

print("SESSION ADDED")
print(store.get_session("session_001"))


# =====================================================
# Check Count
# =====================================================

print("\nTOTAL ACTIVE SESSIONS:")
print(store.total_active_sessions())


# =====================================================
# Remove Session
# =====================================================

store.remove_session("session_001")

print("\nSESSION REMOVED")


# =====================================================
# Final Count
# =====================================================

print("\nTOTAL ACTIVE SESSIONS:")
print(store.total_active_sessions())