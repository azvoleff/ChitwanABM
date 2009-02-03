"""
Part of Chitwan Valley agent-based model.

Class for person agents.

Alex Zvoleff, azvoleff@mail.sdsu.edu
"""

import numpy as np

from chitwanABM import rcParams
from chitwanABM.agents import IDGenerator, boolean_choice

PIDGen = IDGenerator()

class Population(object):
    "Represents a set of persons sharing certain demographic characteristics."
    def __init__(self):
        # This will store a dictionary of all persons in the population, keyed 
        # by PID
        self._persons = {}

        # Now setup the demographic variables for this population, based on the 
        # values given in the model rc file
        self._hazard_birth = rcParams['hazard_birth']
        self._hazard_death = rcParams['hazard_death']
        self._hazard_marriage = rcParams['hazard_marriage']

    def getCouple(self):
        # Couples will start out as a list of one spouse from each couple, then 
        # be extended to become a list of couples.
        couples = []
        for person in self._persons():
            if person.is_married() and person.getSpousePID:
                # store the first spouse
                couples.append(person)

        # Now store the second spouse
        #for couple in self.couples():
        #    couple.extend(self._persons[couple.

    def kill_agent(self):
        "Kills an agent, and fixes the relationships of spouses, households, etc."
        # TODO: this function will "kill" an agent, most likely as a result of 
        # the outcome of the deaths function. Will need to deal with children 
        # and spouse PIDs

    def deaths(self, time):
        """"Runs through the population and kills agents probabilistically based 
        on their age and the hazard_death for this population"""

    def births(self, time):
        """"Runs through the population and agents give birth probabilistically based 
        on their sex, age and the hazard_birth for this population"""
        # TODO: This should take account of the last time the agent gave birth 
        # to ajust the hazard accordingly
        for person in self._persons:
            if person.get_sex() == 'female' and \
                    np.random.random() < self._hazard_death[person.get_age()]:
                        # Agent gives birth:
                        

    def increment_age(self):
        """Adds one to the age of each agent. The units of age are dependent on 
        the units of the input rc parameters."""

class Person(object):
    "Represents a single person agent"
    def __init__(self, birthdate, age=None, initial_agent=False):
        # TODO: use keywordargs to pass things like age, initial_agent, parents, 
        # etc

        # birthdate is the timestep of the birth of the agent. It is used to 
        # calculate the age of the agent. Agents have a birthdate of 0 if they 
        # were BORN in the first timestep of the model.  If they were used to 
        # initialize the model their birthdates will be negative.
        self._birthdate = birthdate

        # self._initial_agent is set to "True" for agents that were used to 
        # initialize the model.
        self._initial_agent = initial_agent

        # self._age is used as a convenience to avoid the need to calculate the 
        # agent's age from self._birthdate each time it is needed. It is 
        # important to remember though that all agent's ages must be incremented 
        # with each model timestep. The age starts at 0 (it is zero for the 
        # entire first timestep of the model).
        self._age = 0

        # self._PID is unique ID number used to track each person agent.
        self._PID = PIDGen.next()

        # Also need to store information on the agent's parents. For agents used 
        # to initialize the model both parent fields are set to "None"
        self._father_PID = father_PID
        self._mother_PID = mother_PID

        # Person agents are randomly assigned a sex
        if boolean_choice(.5):
            self._sex = 'female'
        else:
            self._sex = 'male'

    def get_PID(self):
        return self._PID

    def get_sex(self):
        return self._sex

    def get_spouse_PID(self):
        try:
            return self._spousePID
        except AttributeError:
            raise AttributeError("spouse of agent %i is not defined"%self.get_PID())

    def marry(self, spouse):
        "Marries this agent to another Person instance."
        self._spousePID = spouse.get_PID()
        other._spousePID = self.get_PID()

    def is_married(self):
        "Returns a boolean indicating if person is married or not."
        if self._spousePID == None:
            return False
        else:
            return True

#class Ancestors(list):
    #"Stores a list of person agents for later recall and analysis"
    # TODO: This class will contain a list of deceased person agents, mostly for 
    # debugging the model, although the results could also be used for plotting 
    # purposes.
    #def AddPerson(self, person):
