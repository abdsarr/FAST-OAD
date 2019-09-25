"""
Test module for rubber_engine.py
"""

#  This file is part of FAST : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2019  ONERA/ISAE
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

import numpy as np
from pytest import approx

from fastoad.modules.propulsion.fuel_engine.rubber_engine import RubberEngine
from fastoad.modules.propulsion.fuel_engine.rubber_engine.rubber_engine import FlightPhase
from fastoad.utils.physics import Atmosphere


def test_compute_manual():
    engine = RubberEngine(5, 30, 1500, -50, -100, 1, 0.95,
                          10000)  # f0=1 so that output is simply fc/f0
    fc, sfc = engine.compute_manual(0, 0, 0.8, FlightPhase.MTO)
    np.testing.assert_allclose(fc, 0.955 * 0.8, rtol=1e-2)
    np.testing.assert_allclose(sfc, 0.993e-5, rtol=1e-2)

    fc, sfc = engine.compute_manual(0.3, 0, 0.5, FlightPhase.MTO)
    np.testing.assert_allclose(fc, 0.389, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.35e-5, rtol=1e-2)

    fc, sfc = engine.compute_manual(0.3, 0, 0.5, FlightPhase.CLIMB)
    np.testing.assert_allclose(fc, 0.357, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.35e-5, rtol=1e-2)

    fc, sfc = engine.compute_manual(0.8, 10000, 0.4, FlightPhase.FI)
    np.testing.assert_allclose(fc, 0.0967, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.84e-5, rtol=1e-2)

    fc, sfc = engine.compute_manual(0.8, 13000, 0.7, FlightPhase.CRUISE)
    np.testing.assert_allclose(fc, 0.113, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.57e-5, rtol=1e-2)


def test_compute_regulated():
    engine = RubberEngine(5, 30, 1500, -50, -100, 1, 0.95,
                          10000)  # f0=1 so that input drag in drag/f0
    sfc, thrust_rate = engine.compute_regulated(0, 0, 0.955 * 0.8, FlightPhase.MTO)
    np.testing.assert_allclose(thrust_rate, 0.8, rtol=1e-2)
    np.testing.assert_allclose(sfc, 0.993e-5, rtol=1e-2)

    sfc, thrust_rate = engine.compute_regulated(0.3, 0, 0.389, FlightPhase.MTO)
    np.testing.assert_allclose(thrust_rate, 0.5, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.35e-5, rtol=1e-2)

    sfc, thrust_rate = engine.compute_regulated(0.3, 0, 0.357, FlightPhase.CLIMB)
    np.testing.assert_allclose(thrust_rate, 0.5, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.35e-5, rtol=1e-2)

    sfc, thrust_rate = engine.compute_regulated(0.8, 10000, 0.0967, FlightPhase.FI)
    np.testing.assert_allclose(thrust_rate, 0.4, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.84e-5, rtol=1e-2)

    sfc, thrust_rate = engine.compute_regulated(0.8, 13000, 0.113, FlightPhase.CRUISE)
    np.testing.assert_allclose(thrust_rate, 0.7, rtol=1e-2)
    np.testing.assert_allclose(sfc, 1.57e-5, rtol=1e-2)


def test_installed_weight():
    fj44 = RubberEngine(0, 0, 0, 0, 0, 8452, 0, 0)
    np.testing.assert_allclose(fj44.installed_weight(), 225, rtol=1e-2)
    br710 = RubberEngine(0, 0, 0, 0, 0, 66034, 0, 0)
    np.testing.assert_allclose(br710.installed_weight(), 1756, rtol=1e-2)
    cfm56_3c1 = RubberEngine(0, 0, 0, 0, 0, 104533, 0, 0)
    np.testing.assert_allclose(cfm56_3c1.installed_weight(), 2542, rtol=1e-2)
    trent900 = RubberEngine(0, 0, 0, 0, 0, 340289, 0, 0)
    np.testing.assert_allclose(trent900.installed_weight(), 6519, rtol=1e-2)


def test_length():
    engine = RubberEngine(0, 0, 0, 0, 0, 75000, 0.95, 0)
    np.testing.assert_allclose(engine.length(), 2.73, rtol=1e-2)

    engine = RubberEngine(0, 0, 0, 0, 0, 250000, 0.92, 0)
    np.testing.assert_allclose(engine.length(), 4.39, rtol=1e-2)


def test_nacelle_diameter():
    engine = RubberEngine(3, 0, 0, 0, 0, 75000, 0, 0)
    np.testing.assert_allclose(engine.nacelle_diameter(), 1.61, rtol=1e-2)

    engine = RubberEngine(5.5, 0, 0, 0, 0, 250000, 0, 0)
    np.testing.assert_allclose(engine.nacelle_diameter(), 3.25, rtol=1e-2)


def test_max_thrust():
    """
    Checks model against simplified (but analytically equivalent) formulas
    as in p. 59 of :cite:`roux:2005`, but with correct coefficients (yes, those in report
    are not consistent with the complete formula nor the figure 2.19 just below)

    .. bibliography:: ../refs.bib
    """
    engine = RubberEngine(5, 30, 1500, 0, 0, 1, 0, 0)  # f0=1 so that output is simply fmax/f0
    machs = np.arange(0, 1.01, 0.1)

    # Check cruise
    atm = Atmosphere(11000, altitude_in_feet=False)
    max_thrust_ratio = engine.max_thrust(atm, machs, -100)
    ref_max_thrust_ratio = 0.949 * atm.density / 1.225 * (
            1 - 0.681 * machs + 0.511 * machs ** 2)
    np.testing.assert_allclose(max_thrust_ratio, ref_max_thrust_ratio, rtol=1e-2)

    # Check Take-off
    atm = Atmosphere(0, altitude_in_feet=False)
    max_thrust_ratio = engine.max_thrust(atm, machs, 0)
    ref_max_thrust_ratio = 0.955 * atm.density / 1.225 * (
            1 - 0.730 * machs + 0.359 * machs ** 2)
    np.testing.assert_allclose(max_thrust_ratio, ref_max_thrust_ratio, rtol=1e-2)

    # Check Cruise with compression rate != 30 and bypass ratio != 5
    engine = RubberEngine(4, 35, 1500, 0, 0, 1, 0, 0)  # f0=1 so that output is simply fmax/f0
    atm = Atmosphere(13000, altitude_in_feet=False)
    max_thrust_ratio = engine.max_thrust(atm, machs, -50)
    ref_max_thrust_ratio = 0.969 * atm.density / 1.225 * (
            1 - 0.636 * machs + 0.521 * machs ** 2)
    np.testing.assert_allclose(max_thrust_ratio, ref_max_thrust_ratio, rtol=1e-2)


def test_sfc_at_max_thrust():
    """
    Checks model against values from :cite:`roux:2005` p.40
    (only for ground/Mach=0 values, as cruise values of the report look flawed)

    .. bibliography:: ../refs.bib
    """

    # Check with arrays
    cfm56_3c1 = RubberEngine(6, 25.7, 0, 0, 0, 0, 0, 0)
    atm = Atmosphere([0, 10668, 13000], altitude_in_feet=False)
    sfc = cfm56_3c1.sfc_at_max_thrust(atm, [0, 0.8, 0.8])
    # Note: value for alt==10668 is different from PhD report
    #       alt=13000 is here just for testing in stratosphere
    np.testing.assert_allclose(sfc, [0.970e-5, 1.78e-5, 1.77e-5], rtol=1e-2)

    # Check with scalars
    trent900 = RubberEngine(7.14, 41, 0, 0, 0, 0, 0, 0)
    atm = Atmosphere(0, altitude_in_feet=False)
    sfc = trent900.sfc_at_max_thrust(atm, 0)
    np.testing.assert_allclose(sfc, 0.735e-5, rtol=1e-2)

    atm = Atmosphere(9144, altitude_in_feet=False)
    sfc = trent900.sfc_at_max_thrust(atm, 0.8)
    np.testing.assert_allclose(sfc, 1.68e-5, rtol=1e-2)  # value is different from PhD report

    # Check with arrays
    pw2037 = RubberEngine(6, 31.8, 0, 0, 0, 0, 0, 0)
    atm = Atmosphere(0, altitude_in_feet=False)
    sfc = pw2037.sfc_at_max_thrust(atm, 0)
    np.testing.assert_allclose(sfc, 0.906e-5, rtol=1e-2)

    atm = Atmosphere(10668, altitude_in_feet=False)
    sfc = pw2037.sfc_at_max_thrust(atm, 0.85)
    np.testing.assert_allclose(sfc, 1.74e-5, rtol=1e-2)  # value is different from PhD report


def test_sfc_ratio():
    """    Checks SFC ratio model    """
    design_alt = 10000
    engine = RubberEngine(0, 0, 0, 0, 0, 0, 0, design_alt)

    # Test values taken from method report (plots p. 80, see roux:2002 in refs.bib)
    # + values where model fails (around dh=-1562.5)
    altitudes = design_alt + np.array([-2370, -1564, -1562.5, -1560, -846, 678, 2202, 3726])

    ratio = engine.sfc_ratio(altitudes, 0.8)

    assert ratio == approx([1.024, 3864.6, np.inf, 1386.6, 1.005, 0.972, 0.936, 0.917],
                           rel=1e-3)
