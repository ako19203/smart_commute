from runtime.event_bus import EventBus


# =====================================================
# Create Event Bus
# =====================================================

event_bus = EventBus()


# =====================================================
# Example Subscriber
# =====================================================

def handle_trigger_event(payload):
    print("\nTRIGGER EVENT RECEIVED:")
    print(payload)


# =====================================================
# Subscribe To Event
# =====================================================

event_bus.subscribe(
    "TRIGGER_ALERT",
    handle_trigger_event
)


# =====================================================
# Emit Event
# =====================================================

event_bus.emit(
    "TRIGGER_ALERT",
    {
        "session_id": "session_001",
        "eta_minutes": 3.2,
        "confidence": 0.91,
        "reason": "destination_near"
    }
)


# =====================================================
# Subscriber Count
# =====================================================

print("\nTOTAL SUBSCRIBERS:")
print(
    event_bus.total_subscribers("TRIGGER_ALERT")
)