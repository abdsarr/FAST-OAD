"""
Airfoil reshape function
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

from importlib.resources import open_text

import numpy as np
import pandas as pd

from .profile import Profile
from .. import resources


def get_profile(file_name: str = "BACJ.txt", thickness_ratio=None, chord_length=None) -> Profile:
    """
    Reads profile from indicated resource file and returns it after resize

    :param file_name: name of resource (only "BACJ.txt" for now)
    :param thickness_ratio:
    :param chord_length:
    :return: the Profile instance
    """

    with open_text(resources, file_name) as source:
        x_z = np.genfromtxt(source, skip_header=1, delimiter="\t", names="x, z")
    profile = Profile()
    profile.set_points(x_z["x"], x_z["z"])

    if thickness_ratio:
        profile.thickness_ratio = thickness_ratio

    if chord_length:
        profile.chord_length = chord_length

    return profile
