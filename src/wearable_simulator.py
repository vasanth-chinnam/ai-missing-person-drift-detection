"""
Wearable Device Simulator
==========================
Simulates telemetry from:
  - SmartWatch: heart rate, battery, step count, GPS
  - GPS Tracker: battery, signal strength, GPS

Usage:
    from src.wearable_simulator import SmartWatchSimulator, GPSTrackerSimulator
    watch = SmartWatchSimulator("P001")
    tracker = GPSTrackerSimulator("P001")
    print(watch.tick())   # Advance simulation 1 step
    print(tracker.tick())
"""

import random
import math
import time
from datetime import datetime


HOME = (17.4200, 78.3500)


class SmartWatchSimulator:
    """Simulates a smartwatch worn by a tracked person."""

    def __init__(self, person_id: str, start_lat: float = HOME[0], start_lon: float = HOME[1]):
        self.person_id = person_id
        self.lat = start_lat
        self.lon = start_lon
        self.battery = 100.0
        self.heart_rate = 72
        self.steps = 0
        self.is_active = True
        self._tick_count = 0

    def tick(self) -> dict:
        """Advance simulation by one step (~2 seconds of real time)."""
        self._tick_count += 1

        # Battery drains slowly (100% → 0% over ~8 hours = 14400 ticks at 2s each)
        self.battery = max(0, self.battery - random.uniform(0.005, 0.01))

        # Heart rate varies: resting 60-80, walking 80-110, running/panic 110-140
        base_hr = 72
        hr_noise = random.gauss(0, 3)
        # Simulate occasional spikes (person moving fast or stressed)
        if random.random() < 0.05:
            base_hr = random.randint(100, 135)
        self.heart_rate = int(max(55, min(150, base_hr + hr_noise)))

        # Step count increases if person is moving
        if random.random() < 0.7:  # 70% chance they're walking
            self.steps += random.randint(1, 4)

        # GPS drift (small random walk)
        self.lat += random.gauss(0, 0.00005)
        self.lon += random.gauss(0, 0.00005)

        if self.battery <= 0:
            self.is_active = False

        return {
            "device_type": "smartwatch",
            "person_id": self.person_id,
            "battery_pct": round(self.battery, 1),
            "heart_rate_bpm": self.heart_rate,
            "steps": self.steps,
            "is_active": self.is_active,
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "timestamp": datetime.now().isoformat(),
        }


class GPSTrackerSimulator:
    """Simulates a dedicated GPS tracking device."""

    def __init__(self, person_id: str, start_lat: float = HOME[0], start_lon: float = HOME[1]):
        self.person_id = person_id
        self.lat = start_lat
        self.lon = start_lon
        self.battery = 100.0
        self.signal_strength = 95  # percentage 0-100
        self.is_active = True
        self._tick_count = 0

    def tick(self) -> dict:
        """Advance simulation by one step."""
        self._tick_count += 1

        # Battery drains slower than watch (dedicated device, lasts ~24h)
        self.battery = max(0, self.battery - random.uniform(0.002, 0.005))

        # Signal strength fluctuates
        self.signal_strength = int(max(10, min(100, 
            self.signal_strength + random.gauss(0, 3))))

        # GPS position (follows the person)
        self.lat += random.gauss(0, 0.00005)
        self.lon += random.gauss(0, 0.00005)

        if self.battery <= 0:
            self.is_active = False

        return {
            "device_type": "gps_tracker",
            "person_id": self.person_id,
            "battery_pct": round(self.battery, 1),
            "signal_strength_pct": self.signal_strength,
            "is_active": self.is_active,
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "timestamp": datetime.now().isoformat(),
        }


# Global device instances (populated when first accessed)
_devices: dict = {}


def get_or_create_devices(person_id: str) -> dict:
    """Get or create smartwatch + GPS tracker for a person."""
    if person_id not in _devices:
        _devices[person_id] = {
            "smartwatch": SmartWatchSimulator(person_id),
            "gps_tracker": GPSTrackerSimulator(person_id),
        }
    return _devices[person_id]


def get_all_device_status() -> list:
    """Return telemetry for all active devices."""
    results = []
    for pid, devs in _devices.items():
        results.append(devs["smartwatch"].tick())
        results.append(devs["gps_tracker"].tick())
    return results


if __name__ == "__main__":
    # Quick demo
    watch = SmartWatchSimulator("P001")
    tracker = GPSTrackerSimulator("P001")
    for i in range(5):
        print(f"--- Tick {i+1} ---")
        print(f"  Watch:   HR={watch.tick()['heart_rate_bpm']} bpm, Battery={watch.battery:.1f}%")
        print(f"  Tracker: Signal={tracker.tick()['signal_strength_pct']}%, Battery={tracker.battery:.1f}%")
