#!/usr/bin/env python3
"""
Quick validation script for OptiRoute two-layer system.
Run from backend/: python validate_system.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from flood_risk import (
    _load_pivots,
    _preference_map_at_point,
    _rainfall_factor,
    flood_risk_at_point,
    SPREAD_FACTOR_KM,
)


def test_pivots_loaded():
    """Check that flood pivots are loaded correctly."""
    pivots = _load_pivots()
    assert len(pivots) > 0, "❌ No pivots loaded!"
    assert len(pivots[0]) == 3, "❌ Pivot tuple should have 3 elements!"
    print(f"✅ Loaded {len(pivots)} flood pivots from CSV")
    print(f"   Examples: Hindmata {pivots[0]}, Kurla {pivots[3]}")
    return True


def test_preference_map():
    """Check that preference map works correctly."""
    # At the Hindmata pivot (high risk)
    hindmata = (19.0056, 72.8417)
    pref_at_pivot = _preference_map_at_point(hindmata[0], hindmata[1])
    assert 0.9 < pref_at_pivot <= 1.0, f"❌ Preference at pivot should be ~0.95, got {pref_at_pivot}"
    print(f"✅ Preference map at Hindmata: {pref_at_pivot:.3f} (expect ~0.95)")

    # At a safe location (far from all pivots)
    safe_loc = (18.50, 72.50)  # Far southwest
    pref_safe = _preference_map_at_point(safe_loc[0], safe_loc[1])
    assert pref_safe < 0.1, f"❌ Preference at safe location should be ~0, got {pref_safe}"
    print(f"✅ Preference map at safe location (18.50°N, 72.50°E): {pref_safe:.4f} (expect ~0)")

    # Test decay with distance
    close_to_hindmata = (19.0156, 72.8417)  # ~1.1 km away
    pref_close = _preference_map_at_point(close_to_hindmata[0], close_to_hindmata[1])
    assert pref_close < pref_at_pivot, "❌ Preference should decay with distance!"
    print(f"✅ Distance decay working: {pref_at_pivot:.3f} (at pivot) → {pref_close:.3f} (1.1 km away)")

    return True


def test_rainfall_factor():
    """Check rainfall modulation curve."""
    # No rain
    factor_dry = _rainfall_factor(0.0)
    assert 0.09 < factor_dry <= 0.11, f"❌ Dry factor should be ~0.1, got {factor_dry}"
    print(f"✅ Rain factor (0mm): {factor_dry:.3f} (expect 0.1, baseline)")

    # Light rain
    factor_light = _rainfall_factor(20.0)
    assert 0.3 < factor_light < 0.6, f"❌ Light rain factor should be ~0.4–0.5, got {factor_light}"
    print(f"✅ Rain factor (20mm): {factor_light:.3f} (expect ~0.4–0.5)")

    # Heavy rain
    factor_heavy = _rainfall_factor(100.0)
    assert 0.95 < factor_heavy <= 1.0, f"❌ Heavy rain factor should be ~1.0, got {factor_heavy}"
    print(f"✅ Rain factor (100mm): {factor_heavy:.3f} (expect ~1.0, full activation)")

    # Verify non-linear (not just linear scaling)
    factor_50 = _rainfall_factor(50.0)
    linear_50 = 0.1 + 0.9 * (50 / 100)  # Linear would be here
    assert factor_50 < linear_50, "❌ Rain factor should be non-linear (sublinear)"
    print(f"✅ Rain factor (50mm) is non-linear: {factor_50:.3f} < {linear_50:.3f} (linear)")

    return True


def test_combined_risk():
    """Check final combined risk computation."""
    hindmata = (19.0056, 72.8417)

    # Dry weather at hotspot
    risk_dry = flood_risk_at_point(hindmata[0], hindmata[1], 0.0)
    assert 0.08 < risk_dry < 0.15, f"❌ Dry risk at Hindmata should be ~0.095, got {risk_dry}"
    print(f"✅ Risk at Hindmata (dry): {risk_dry:.3f}")

    # Heavy rain at hotspot
    risk_wet = flood_risk_at_point(hindmata[0], hindmata[1], 100.0)
    assert risk_wet > 0.9, f"❌ Wet risk at Hindmata should be ~0.95, got {risk_wet}"
    print(f"✅ Risk at Hindmata (100mm rain): {risk_wet:.3f}")

    # Verify rain increases risk
    assert risk_wet > risk_dry, "❌ Rain should increase risk!"
    print(f"✅ Risk amplification: {risk_dry:.3f} (dry) → {risk_wet:.3f} (rain)")

    # Safe location (low risk even with rain)
    safe_loc = (18.50, 72.50)
    risk_safe_wet = flood_risk_at_point(safe_loc[0], safe_loc[1], 100.0)
    assert risk_safe_wet < 0.1, f"❌ Risk at safe location even with rain should be low, got {risk_safe_wet}"
    print(f"✅ Risk at safe location (100mm rain): {risk_safe_wet:.4f} (stays low)")

    return True


def test_constants():
    """Verify tunable constants are reasonable."""
    print(f"\n🔧 System Constants:")
    print(f"   SPREAD_FACTOR_KM = {SPREAD_FACTOR_KM} km")
    print(f"   (Lower → faster decay, Higher → slower decay)")
    assert 0.5 < SPREAD_FACTOR_KM < 5.0, "❌ Spread factor should be between 0.5 and 5 km"
    print(f"✅ Spread factor in reasonable range")
    return True


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("🧪 OptiRoute Two-Layer System Validation")
    print("=" * 60)

    tests = [
        ("Pivots Loading", test_pivots_loaded),
        ("Preference Map", test_preference_map),
        ("Rainfall Factor", test_rainfall_factor),
        ("Combined Risk", test_combined_risk),
        ("Constants", test_constants),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n📝 Testing: {name}")
        print("-" * 60)
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED! System is ready to use.")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
