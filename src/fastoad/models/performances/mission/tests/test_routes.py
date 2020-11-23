"""
Tests module for standard_flight.py

These tests use the segment classes and the RubberEngine model, so they are
more integration tests than unit tests.
Therefore, obtained numerical results depend mainly on other classes, so this is
why almost no numerical check is done here (such checks will be done in the
non-regression tests).
"""
#  This file is part of FAST-OAD : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2020  ONERA & ISAE-SUPAERO
#  FAST is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os.path as pth
from abc import ABC
from os import mkdir
from shutil import rmtree
from typing import Dict, List, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.ticker import MultipleLocator
from numpy.testing import assert_allclose
from scipy.constants import knot, foot

from fastoad.base.flight_point import FlightPoint
from fastoad.constants import FlightPhase, EngineSetting
from fastoad.models.performances.mission.base import (
    IFlightPart,
    FlightSequence,
)
from fastoad.models.performances.mission.polar import Polar
from fastoad.models.performances.mission.routes import SimpleRoute, RangedRoute
from fastoad.models.performances.mission.segments.altitude_change import AltitudeChangeSegment
from fastoad.models.performances.mission.segments.cruise import CruiseSegment
from fastoad.models.performances.mission.segments.speed_change import SpeedChangeSegment
from fastoad.models.propulsion import IPropulsion
from fastoad.models.propulsion.fuel_propulsion.base import FuelEngineSet
from fastoad.models.propulsion.fuel_propulsion.rubber_engine import RubberEngine

DATA_FOLDER_PATH = pth.join(pth.dirname(__file__), "data")
RESULTS_FOLDER_PATH = pth.join(pth.dirname(__file__), "results")


@pytest.fixture(scope="module")
def cleanup():
    rmtree(RESULTS_FOLDER_PATH, ignore_errors=True)


@pytest.fixture(scope="module")
def cleanup():
    rmtree(RESULTS_FOLDER_PATH, ignore_errors=True)
    mkdir(RESULTS_FOLDER_PATH)


def print_dataframe(df, max_rows=20):
    """Utility for correctly printing results"""
    # Not used if all goes all well. Please keep it for future test setting/debugging.
    with pd.option_context(
        "display.max_rows", max_rows, "display.max_columns", None, "display.width", None
    ):
        print()
        print(df)


@pytest.fixture
def high_speed_polar() -> Polar:
    """Returns a dummy polar where max L/D ratio is about 16., around CL=0.5"""
    cl = np.arange(0.0, 1.5, 0.01)
    cd = 0.6e-1 * cl ** 2 + 0.016
    return Polar(cl, cd)


@pytest.fixture
def low_speed_polar() -> Polar:
    """Returns a dummy polar where max L/D ratio is around CL=0.5"""
    cl = np.arange(0.0, 2.0, 0.01)
    cd = 0.6e-1 * cl ** 2 + 0.03
    return Polar(cl, cd)


def plot_flight(flight_points, fig_filename):
    plt.figure(figsize=(12, 12))
    ax1 = plt.subplot(2, 1, 1)
    plt.plot(flight_points.ground_distance / 1000.0, flight_points.altitude / foot, "o-")
    plt.xlabel("distance [km]")
    plt.ylabel("altitude [ft]")
    ax1.xaxis.set_minor_locator(MultipleLocator(50))
    ax1.yaxis.set_minor_locator(MultipleLocator(500))
    plt.grid(which="major", color="k")
    plt.grid(which="minor")

    ax2 = plt.subplot(2, 1, 2)
    lines = []
    lines += plt.plot(
        flight_points.ground_distance / 1000.0, flight_points.true_airspeed, "b-", label="TAS [m/s]"
    )
    lines += plt.plot(
        flight_points.ground_distance / 1000.0,
        flight_points.equivalent_airspeed / knot,
        "g--",
        label="EAS [kt]",
    )
    plt.xlabel("distance [km]")
    plt.ylabel("speed")
    ax2.xaxis.set_minor_locator(MultipleLocator(50))
    ax2.yaxis.set_minor_locator(MultipleLocator(5))
    plt.grid(which="major", color="k")
    plt.grid(which="minor")

    plt.twinx(ax2)
    lines += plt.plot(
        flight_points.ground_distance / 1000.0, flight_points.mach, "r.-", label="Mach"
    )
    plt.ylabel("Mach")

    labels = [l.get_label() for l in lines]
    plt.legend(lines, labels, loc=0)

    plt.savefig(pth.join(RESULTS_FOLDER_PATH, fig_filename))
    plt.close()


def test_ranged_flight(low_speed_polar, high_speed_polar, cleanup):

    engine = RubberEngine(5.0, 30.0, 1500.0, 1.0e5, 0.95, 10000.0)
    propulsion = FuelEngineSet(engine, 2)

    total_distance = 2.0e6
    flight_calculator = RangedRoute(
        StandardFlight(
            propulsion=propulsion,
            reference_area=120.0,
            low_speed_climb_polar=low_speed_polar,
            high_speed_polar=high_speed_polar,
            cruise_mach=0.78,
            thrust_rates={FlightPhase.CLIMB: 0.93, FlightPhase.DESCENT: 0.2},
        ),
        flight_distance=total_distance,
    )

    assert flight_calculator.cruise_speed == ("mach", 0.78)

    start = FlightPoint(
        true_airspeed=150.0 * knot, altitude=100.0 * foot, mass=70000.0, ground_distance=100000.0,
    )
    flight_points = flight_calculator.compute_from(start)

    plot_flight(flight_points, "test_ranged_flight.png")

    assert_allclose(
        flight_points.iloc[-1].ground_distance,
        total_distance + start.ground_distance,
        atol=flight_calculator.distance_accuracy,
    )


# We define here in Python the StandardFlight class that feeds the test of RangedRoute ============


class StandardFlight(SimpleRoute):
    """
    Defines and computes a standard flight mission.

    The flight sequence is:
    - initial climb
    - climb
    - cruise at constant altitude
    - descent
    """

    def __init__(
        self,
        propulsion: IPropulsion,
        reference_area: float,
        low_speed_climb_polar: Polar,
        high_speed_polar: Polar,
        cruise_mach: float,
        thrust_rates: Dict[FlightPhase, float],
        cruise_distance: float = 0.0,
        climb_target_altitude: float = AltitudeChangeSegment.OPTIMAL_FLIGHT_LEVEL,
        descent_target_altitude: float = 1500.0 * foot,
        time_step=None,
    ):
        """

        :param propulsion:
        :param reference_area:
        :param low_speed_climb_polar:
        :param high_speed_polar:
        :param cruise_mach:
        :param thrust_rates:
        :param cruise_distance:
        :param climb_target_altitude: (in m) altitude where cruise will begin. If value is
                                      AltitudeChangeSegment.OPTIMAL_ALTITUDE (default), climb will
                                      stop when maximum lift/drag ratio is achieved. Cruise will go
                                      on at the same altitude.
        :param descent_target_altitude: (in m) altitude where descent will end in meters
                                        Default is 457.2m (1500ft)
        :param time_step: if provided, this time step will be applied for all segments.
        """

        self.flight_phase_kwargs = {
            "propulsion": propulsion,
            "reference_area": reference_area,
            "time_step": time_step,
        }

        self.low_speed_climb_polar = low_speed_climb_polar
        self.high_speed_polar = high_speed_polar
        self.cruise_mach = cruise_mach
        self.thrust_rates = thrust_rates
        self.climb_target_altitude = climb_target_altitude
        self.descent_target_altitude = descent_target_altitude
        self.time_step = time_step

        kwargs = {
            "propulsion": propulsion,
            "reference_area": reference_area,
        }

        initial_climb = InitialClimbPhase(
            **kwargs,
            polar=low_speed_climb_polar,
            thrust_rate=1.0,
            name=FlightPhase.INITIAL_CLIMB.value,
            time_step=0.2,
        )
        climb = ClimbPhase(
            **kwargs,
            polar=high_speed_polar,
            thrust_rate=thrust_rates[FlightPhase.CLIMB],
            target_altitude=self.climb_target_altitude,
            maximum_mach=self.cruise_mach,
            name=FlightPhase.CLIMB.value,
            time_step=5.0,
        )
        cruise = CruiseSegment(
            **kwargs,
            target=FlightPoint(ground_distance=cruise_distance),
            polar=high_speed_polar,
            engine_setting=EngineSetting.CRUISE,
            name=FlightPhase.CRUISE.value,
        )
        descent = DescentPhase(
            **kwargs,
            polar=high_speed_polar,
            thrust_rate=thrust_rates[FlightPhase.DESCENT],
            target_altitude=self.descent_target_altitude,
            name=FlightPhase.DESCENT.value,
            time_step=5.0,
        )
        super().__init__(
            [initial_climb, climb], cruise, [descent],
        )


class AbstractManualThrustFlightPhase(FlightSequence, ABC):
    """
    Base class for climb and descent phases.
    """

    def __init__(
        self,
        *,
        propulsion: IPropulsion,
        reference_area: float,
        polar: Polar,
        thrust_rate: float = 1.0,
        name="",
        time_step=None
    ):
        """
        Initialization is done only with keyword arguments.

        :param propulsion:
        :param reference_area:
        :param polar:
        :param thrust_rate:
        :param time_step: if provided, this time step will be applied for all segments.
        """

        super().__init__()
        self.segment_kwargs = {
            "propulsion": propulsion,
            "reference_area": reference_area,
            "polar": polar,
            "thrust_rate": thrust_rate,
            "name": name,
            "time_step": time_step,
        }


class InitialClimbPhase(AbstractManualThrustFlightPhase):
    """
    Preset for initial climb phase.

    - Climbs up to 400ft at constant EAS
    - Accelerates to EAS = 250kt at constant altitude
    - Climbs up to 1500ft at constant EAS
    """

    @property
    def flight_sequence(self) -> List[Union[IFlightPart, str]]:
        return [
            AltitudeChangeSegment(
                target=FlightPoint(equivalent_airspeed="constant", altitude=400.0 * foot),
                engine_setting=EngineSetting.TAKEOFF,
                **self.segment_kwargs,
            ),
            SpeedChangeSegment(
                target=FlightPoint(equivalent_airspeed=250.0 * knot),
                engine_setting=EngineSetting.TAKEOFF,
                **self.segment_kwargs,
            ),
            AltitudeChangeSegment(
                target=FlightPoint(equivalent_airspeed="constant", altitude=1500.0 * foot),
                engine_setting=EngineSetting.TAKEOFF,
                **self.segment_kwargs,
            ),
        ]


class ClimbPhase(AbstractManualThrustFlightPhase):
    """
    Preset for climb phase.

    - Climbs up to 10000ft at constant EAS
    - Accelerates to EAS = 300kt at constant altitude
    - Climbs up to target altitude at constant EAS
    """

    def __init__(self, **kwargs):
        """
        Uses keyword arguments as for :meth:`AbstractManualThrustFlightPhase` with
        these additional keywords:

        :param maximum_mach: Mach number that won't be exceeded during climb
        :param target_altitude: target altitude in meters, can be a float or
                                AltitudeChangeSegment.OPTIMAL_ALTITUDE to target
                                altitude with maximum lift/drag ratio
        """

        if "maximum_mach" in kwargs:
            self.maximum_mach = kwargs.pop("maximum_mach")
        self.target_altitude = kwargs.pop("target_altitude")
        super().__init__(**kwargs)

    @property
    def flight_sequence(self) -> List[Union[IFlightPart, str]]:
        self.segment_kwargs["engine_setting"] = EngineSetting.CLIMB

        return [
            AltitudeChangeSegment(
                target=FlightPoint(equivalent_airspeed="constant", altitude=10000.0 * foot),
                **self.segment_kwargs,
            ),
            SpeedChangeSegment(
                target=FlightPoint(equivalent_airspeed=300.0 * knot), **self.segment_kwargs,
            ),
            AltitudeChangeSegment(
                target=FlightPoint(equivalent_airspeed="constant", mach=self.maximum_mach),
                **self.segment_kwargs,
            ),
            AltitudeChangeSegment(
                target=FlightPoint(mach="constant", altitude=self.target_altitude),
                **self.segment_kwargs,
            ),
        ]


class DescentPhase(AbstractManualThrustFlightPhase):
    """
    Preset for descent phase.

    - Descends down to EAS = 300kt at constant Mach
    - Descends down to 10000ft at constant EAS
    - Decelerates to EAS = 250kt
    - Descends down to target altitude at constant EAS
    """

    def __init__(self, **kwargs):
        """
        Uses keyword arguments as for :meth:`AbstractManualThrustFlightPhase` with
        this additional keyword:

        :param target_altitude: target altitude in meters
        """

        self.target_altitude = kwargs.pop("target_altitude")
        super().__init__(**kwargs)

    @property
    def flight_sequence(self) -> List[Union[IFlightPart, str]]:
        self.segment_kwargs["engine_setting"] = EngineSetting.IDLE
        return [
            AltitudeChangeSegment(
                target=FlightPoint(equivalent_airspeed=300.0 * knot, mach="constant"),
                **self.segment_kwargs,
            ),
            AltitudeChangeSegment(
                target=FlightPoint(altitude=10000.0 * foot, equivalent_airspeed="constant"),
                **self.segment_kwargs,
            ),
            SpeedChangeSegment(
                target=FlightPoint(equivalent_airspeed=250.0 * knot), **self.segment_kwargs,
            ),
            AltitudeChangeSegment(
                target=FlightPoint(altitude=self.target_altitude, equivalent_airspeed="constant"),
                **self.segment_kwargs,
            ),
        ]
