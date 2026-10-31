from __future__ import annotations

import pytest

from sattrack.catalog.domain import OrbitClass, classify_orbit, group_display_name, period_minutes


@pytest.mark.parametrize(
    ("mean_motion", "eccentricity", "expected"),
    [
        (15.50103472, 0.0006703, OrbitClass.LEO),  # ISS
        (2.00562, 0.0091, OrbitClass.MEO),  # GPS-like
        (1.00271, 0.0002, OrbitClass.GEO),  # geostationary
        (2.006, 0.74, OrbitClass.HEO),  # Molniya
        (1.0, 0.05, OrbitClass.OTHER),  # geosynchronous period but too eccentric for GEO
        (0.5, 0.01, OrbitClass.OTHER),  # beyond GEO
    ],
)
def test_classify_orbit_returns_expected_regime(
    mean_motion: float, eccentricity: float, expected: OrbitClass
) -> None:
    assert classify_orbit(mean_motion, eccentricity) is expected


def test_classify_orbit_treats_leo_threshold_as_exclusive() -> None:
    assert classify_orbit(11.25, 0.0) is OrbitClass.MEO
    assert classify_orbit(11.2501, 0.0) is OrbitClass.LEO


def test_classify_orbit_treats_heo_eccentricity_threshold_as_inclusive() -> None:
    assert classify_orbit(15.0, 0.25) is OrbitClass.HEO
    assert classify_orbit(15.0, 0.2499) is OrbitClass.LEO


def test_period_minutes_converts_mean_motion() -> None:
    assert period_minutes(15.5) == pytest.approx(92.903, abs=1e-3)
    assert period_minutes(1.0) == pytest.approx(1440.0)


@pytest.mark.parametrize("mean_motion", [0.0, -1.0])
def test_period_minutes_rejects_non_positive_mean_motion(mean_motion: float) -> None:
    with pytest.raises(ValueError, match="mean motion must be positive"):
        period_minutes(mean_motion)


def test_group_display_name_falls_back_to_slug() -> None:
    assert group_display_name("stations") == "Space stations"
    assert group_display_name("amateur") == "amateur"
