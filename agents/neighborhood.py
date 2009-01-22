#!/usr/bin/env python
"""
Part of Chitwan Valley agent-based model.

Class for neighborhood agents.

Alex Zvoleff, azvoleff@mail.sdsu.edu
"""
import shared

NIDGen = shared.IDGenerator()

class Neighborhood(object):
    "Represents a single neighborhood agent"
    def __init__(self):
        self._NID = NIDGen.next()
        self._NumYearsNonFamilyServices = 15 #TODO
        self._ElecAvailable = shared.Boolean()
        self._members = set()

    def GetNID(self):
        "Returns the ID of this neighborhood."
        return self._NID

    def GetNumYearsFamilyServices(self):
        "Boolean for whether household uses any non-wood fuel."
        return self._NumYearsNonFamilyServices

    def ElecAvailable(self):
        "Boolean for whether neighborhood has electricity."
        return self._ElecAvailable
