from runtime.state_store import StateStore
from runtime.session_manager import SessionManager


# =====================================================
# Setup
# =====================================================

store = StateStore()

manager = SessionManager(store)


# =====================================================
# Create Session
# =====================================================

session = manager.create_session(
    session_id="session_001",

    origin_coordinates=(12.9716, 77.5946),

    destination_name="Office",

    destination_coordinates=(12.9352, 77.6245),
)

print("SESSION CREATED:")
print(session)


# =====================================================
# Check Existence
# =====================================================

print("\nSESSION EXISTS:")
print(manager.session_exists("session_001"))


# =====================================================
# Retrieve Session
# =====================================================

retrieved = manager.get_session("session_001")

print("\nRETRIEVED SESSION:")
print(retrieved)


# =====================================================
# Active Count
# =====================================================

print("\nTOTAL ACTIVE SESSIONS:")
print(manager.total_active_sessions())


# =====================================================
# Terminate Session
# =====================================================

terminated = manager.terminate_session("session_001")

print("\nSESSION TERMINATED:")
print(terminated)


# =====================================================
# Final Count
# =====================================================

print("\nTOTAL ACTIVE SESSIONS:")
print(manager.total_active_sessions())