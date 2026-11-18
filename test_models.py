from runtime.models import GPSUpdate


gps = GPSUpdate(
    session_id="session_001",
    latitude=12.9716,
    longitude=77.5946,
    speed_mps=8.2
)


print("GPS OBJECT:")
print(gps)

print("\nCOORDINATES:")
print(gps.coordinates)