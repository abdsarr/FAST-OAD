"""Sellar discipline 1"""
#  This file is part of FAST-OAD : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2024 ONERA & ISAE-SUPAERO
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
import openmdao.api as om

from ...validity_checker import ValidityDomainChecker


@ValidityDomainChecker({"x": (-1, 1)})  # This validity domain should not apply
class Disc1(om.ExplicitComponent):
    """An OpenMDAO component to encapsulate Disc1 discipline"""

    def setup(self):
        self.add_input(
            "x", val=np.nan, desc="input x"
        )  # NaN as default for testing connexion check
        self.add_input("z", val=[5, 2], desc="", units="m**2")  # for testing non-None units
        self.add_input("y2", val=1.0, desc="variable y2")  # for testing input description capture

        self.add_output("y1", val=1.0, desc="variable y1")  # for testing output description capture

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        """
        Evaluates the equation
        y1 = z1**2 + z2 + x1 - 0.2*y2
        """
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        x1 = inputs["x"]
        y2 = inputs["y2"]

        outputs["y1"] = z1 ** 2 + z2 + x1 - 0.2 * y2


@ValidityDomainChecker({"x": (0, 4)})  # This validity domain should apply in case 1
class Disc1Bis(om.ExplicitComponent):
    """An OpenMDAO component to encapsulate Disc1 discipline"""

    def setup(self):
        self.add_input("x", val=2.0, desc="input x")  # NaN as default for testing connexion check
        self.add_input("z", val=[5, 2], desc="", units="m**2")  # for testing non-None units
        self.add_input("y2", val=1.0, desc="variable y2")  # for testing input description capture

        self.add_output("y1", val=1.0, desc="variable y1")  # for testing output description capture

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        """
        Evaluates the equation
        y1 = z1**2 + z2 + x1 - 0.2*y2
        """
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        x1 = inputs["x"]
        y2 = inputs["y2"]

        outputs["y1"] = z1 ** 2 + z2 + x1 - 0.2 * y2


@ValidityDomainChecker({"x": (0, 1)})  # This validity domain should apply in case 2
class Disc1Ter(Disc1Bis):
    """Same component with different validity domain."""
