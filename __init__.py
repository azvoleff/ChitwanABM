# Copyright 2009 Alex Zvoleff
#
# This file is part of the ChitwanABM agent-based model.
# 
# ChitwanABM is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# 
# ChitwanABM is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# ChitwanABM.  If not, see <http://www.gnu.org/licenses/>.
#
# Contact Alex Zvoleff in the Department of Geography at San Diego State 
# University with any comments or questions. See the README.txt file for 
# contact information.

"""
Part of Chitwan Valley agent-based model.

Sets up rc parameters so that they can be loaded and reused by other parts of 
the model.

Alex Zvoleff, azvoleff@mail.sdsu.edu
"""

import os
import sys
import warnings

import numpy as np

from rcsetup import get_rc_params

class IDError(Exception):
    pass

class IDGenerator(object):
    """A generator class for consecutive unique ID numbers. IDs can be assigned 
    externally by other code, and tracked in this class with the use_ID 
    function. The use_ID function will raise an error if called with an ID that has 
    already been assigned."""
    def __init__(self):
        # Start at -1 so the first ID will be 0
        self._last_ID = -1
        self._used_IDs = []

    def reset(self):
        self.__init__()

    def next(self):
        newID = self._last_ID + 1
        while newID in self._used_IDs:
            newID += 1
        self._last_ID = newID
        self._used_IDs.append(newID)
        return newID

    def use_ID(self, used_ID):
        # TODO: This will get very slow when dealing with large numbers of IDs. 
        # It might be better to just set _last_ID to the maximum value in 
        # _used_IDs whenever the use_ID function is called
        if used_ID in self._used_IDs:
            raise IDError("ID %s has already been used"%(used_ID))
        self._used_IDs.append(used_ID)

# this is the instance used by the model
rcParams = get_rc_params()

# Check if a RandomState was loaded from the rcfile. If not (if 
# RandomState==None), then choose a random RandomState, and store it in 
# rcParams so that it can be written to a file at the end of model runs, and 
# saved for later reuse (for testing, etc.).
if rcParams['model.RandomState'] == None:
    # Seed the RandomState with a known random integer, and save the seed for 
    # later reuse (for testing, etc.).
    random_int = int(10**8 * np.random.random())
    rcParams['model.RandomState'] = random_int
random_state = np.random.RandomState(int(rcParams['model.RandomState']))

def boolean_choice(trueProb=.5):
    """A function that returns true or false depending on whether a randomly
    drawn float is less than trueProb"""
    if random_state.rand() < trueProb:
        return True
    else:
        return False
