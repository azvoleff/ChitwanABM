# Copyright 2008-2012 Alex Zvoleff
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
Contains the classes for Person, Household, Neighborhood, and Region agents. 
Person agents are subclasses of the Agent class, while Household, Neighborhood, 
and Region agents are all subclasses of the Agent_set object.

Alex Zvoleff, azvoleff@mail.sdsu.edu
"""

import os
import csv
import logging

import numpy as np

from PyABM import IDGenerator, boolean_choice
from PyABM.agents import Agent, Agent_set, Agent_Store

from ChitwanABM import rcParams, random_state
from ChitwanABM.statistics import calc_probability_death, \
        calc_probability_migration_simple, calc_first_birth_time, \
        calc_birth_interval, calc_hh_area, calc_des_num_children, \
        calc_first_birth_prob_ghimireaxinn2010, calc_first_birth_prob_zvoleff, \
        calc_probability_migration_masseyetal_2010, calc_migration_length, \
        calc_education_level, calc_spouse_age_diff, choose_spouse, \
        calc_num_inmigrant_households, calc_probability_divorce

logger = logging.getLogger(__name__)

if rcParams['model.parameterization.marriage'] == 'simple':
    from ChitwanABM.statistics import calc_probability_marriage_simple as calc_probability_marriage
elif rcParams['model.parameterization.marriage'] == 'yabiku2006':
    from ChitwanABM.statistics import calc_probability_marriage_yabiku2006 as calc_probability_marriage
elif rcParams['model.parameterization.marriage'] == 'zvoleff':
    from ChitwanABM.statistics import calc_probability_marriage_zvoleff as calc_probability_marriage
else:
    raise Exception("Unknown option for marriage parameterization: '%s'"%rcParams['model.parameterization.marriage'])

if rcParams['model.parameterization.migration'] == 'simple':
    from ChitwanABM.statistics import calc_probability_migration_simple as calc_probability_migration
elif rcParams['model.parameterization.migration'] == 'massey2010':
    from ChitwanABM.statistics import calc_probability_migration_masseyetal_2010 as calc_probability_migration
else:
    raise Exception("Unknown option for migration parameterization: '%s'"%rcParams['model.parameterization.migration'])

if rcParams['model.parameterization.fuelwood_usage'] == 'simple':
    from ChitwanABM.statistics import calc_fuelwood_usage_simple as calc_fuelwood_usage
elif rcParams['model.parameterization.fuelwood_usage'] == 'migrationfeedback':
    from ChitwanABM.statistics import calc_fuelwood_usage_migration_feedback as calc_fuelwood_usage
else:
    raise Exception("Unknown option for fuelwood usage: '%s'"%rcParams['model.parameterization.fuelwood_usage'])

class Person(Agent):
    "Represents a single person agent"
    def __init__(self, world, birthdate, ID=None, mother=None, father=None,
            age=None, sex=None, initial_agent=False, ethnicity=None, 
            in_migrant=False):
        Agent.__init__(self, world, ID, initial_agent)

        # birthdate is the timestep of the birth of the agent. It is used to 
        # calculate the age of the agent. Agents have a birthdate of 0 if they 
        # were BORN in the first timestep of the model.  If they were used to 
        # initialize the model their birthdates will be negative.
        self._birthdate = birthdate

        # deathdate is used for tracking agent deaths in the results, mainly 
        # for debugging.
        self._deathdate = None
        self._alive = True

        # self._initial_agent is set to "True" for agents that were used to 
        # initialize the model.
        self._initial_agent = initial_agent

        self._in_migrant = in_migrant

        # self._age is used as a convenience to avoid the need to calculate the 
        # agent's age from self._birthdate each time it is needed. It is         
        # important to remember though that all agent's ages must be 
        # incremented with each model timestep, and are expressed in months.
        # The age starts at 0 (it is zero for the entire first timestep of the 
        # model).
        self._age = age

        # Also need to store information on the agent's parents. For agents 
        # used to initialize the model both parent fields are set to "None"
        if father == None:
            self._father = None
        else:
            self._father = father

        if mother == None:
            self._mother = None
        else:
            self._mother = mother

        if sex==None:
            # Person agents are randomly assigned a sex
            if boolean_choice():
                self._sex = 'female'
            else:
                self._sex = 'male'
        elif sex in ['male', 'female']:
            self._sex = sex
        else:
            raise ValueError("%s is not a valid gender"%(sex))

        # The agent's ethnicity in the CVFS data as 1: High Caste Hindu, 2: 
        # Hill Tibetoburmese, 3: Low Caste Hindu, 4: Newar, 5: Terai 
        # Tibetoburmese, 6: Other. Other is dropped from the model for 
        # consistency of published works. Here ethnicity is converted to a 
        # textual representation for clarity (see the preprocessing code).
        self._ethnicity = ethnicity

        # If not defined at birth, self._des_num_children will be defined (for 
        # women) at marriage in the "marry" function.
        self._des_num_children = None

        if self._sex=="female":
            # TODO: For initial agents, set birth interval to start as of the 
            # date of their last birth, and initialize first birth interval for 
            # these agents in initialization code.
            self._birth_interval = calc_birth_interval()

        self._spouse = None

        self._children = []
        self._number_of_children = 0

        if self._sex == "female":
            self._first_birth_timing = calc_first_birth_time(self)
        else:
            self._first_birth_timing = None

        self._marriage_time = None

        self._schooling = 0
        self._final_schooling_level = None
        self._school_status = "undetermined"

        #TODO: fix this value elsewhere according to empirical probability
        self._work = boolean_choice(.1)
        #TODO: fix this value elsewhere according to empirical probability
        self._parents_contracep_ever = boolean_choice()

        if in_migrant:
            # These values are set in the give_birth method of mother agents 
            # for agents born within the model run, and in initialize.py for 
            # agents that initialize the model.
            if (self._age / 12.) > rcParams['education.start_school_age_years']:
                self._schooling = np.random.randint(1, 15)
                #TODO: Fix this to also allow inschool status
                self._school_status == "outofschool"
            self._mother_work = boolean_choice()
            self._father_work = boolean_choice()
            #TODO: fix this value elsewhere according to empirical probability
            self._mother_years_schooling = np.random.randint(1, 15)
            self._father_years_schooling = np.random.randint(1, 15)
            #self._mother_years_schooling = calc_education_level(initial=True)
            #self._father_years_schooling = calc_education_level(initial=True)
            self._mother_num_children = boolean_choice()
            self._child_school_lt_1hr_ft = boolean_choice()
            self._child_health_lt_1hr_ft = boolean_choice()
            self._child_bus_lt_1hr_ft = boolean_choice()
            self._child_market_lt_1hr_ft = boolean_choice()
            self._child_employer_lt_1hr_ft = boolean_choice()

        # These values are set in the give_birth method of mother agents
        self._birth_household_ID = None
        self._birth_neighborhood_ID = None

        # _store_list tracks any agent_store instances this person is a member 
        # of (for LL or LD migration for example).
        self._store_list = []

    def get_mother(self):
        return self._mother

    def get_num_children(self):
        return self._number_of_children

    def get_father(self):
        return self._father

    def get_sex(self):
        return self._sex

    def get_age_months(self):
        return self._age

    def get_age_years(self):
        return self._age / 12.

    def get_ethnicity(self):
        return self._ethnicity

    def get_spouse(self):
        return self._spouse

    def get_years_schooling(self):
        return self._schooling

    def get_work(self):
        return self._work

    def get_mother_years_schooling(self):
        if self.is_initial_agent() or self.is_in_migrant():
            # Only initial agents and in-migrant agents have this attribute.  
            # For endogenous agents, check the actual years of schooling their 
            # mother had, since it may have changed since birth. Same comment 
            # applies to all the 'get_mother_' and 'get_father_' methods.
            return self._mother_years_schooling
        else:
            return self.get_mother().get_years_schooling()

    def get_father_years_schooling(self):
        if self.is_initial_agent() or self.is_in_migrant():
            return self._father_years_schooling
        else:
            return self.get_father().get_years_schooling()

    def get_mother_work(self):
        if self.is_initial_agent() or self.is_in_migrant():
            return self._mother_work
        else:
            return self.get_mother().get_work()

    def get_father_work(self):
        if self.is_initial_agent() or self.is_in_migrant():
            return self._father_work
        else:
            return self.get_father().get_work()

    def get_mother_num_children(self):
        if self.is_initial_agent() or self.is_in_migrant():
            return self._mother_num_children
        else:
            return self.get_mother().get_num_children()

    def is_sibling(self, person):
        if person.get_mother() == None or person.is_in_migrant():
            # Handle initial agents and in_migrants for whom we have no data on 
            # their mother's children's relationships. This is the case for 
            # only a subset of the initial agents.
            return False
        elif self in person.get_mother()._children: return True
        else: return False

    def is_initial_agent(self):
        return self._initial_agent

    def is_in_migrant(self):
        return self._in_migrant

    def kill(self, time):
        self._alive = False
        self._deathdate = time
        if self.is_married():
            self.divorce()
        household = self.get_parent_agent()
        household.remove_agent(self)

    def marry(self, spouse, time):
        "Marries this agent to another Person instance."
        assert self._spouse == None, "Person %s already has spouse %s"%(person.get_ID(), person.get_spouse().get_ID())
        assert spouse._spouse == None, "Person %s already has spouse %s"%(spouse.get_ID(), spouse.get_spouse().get_ID())
        assert spouse.get_sex() != self.get_sex(), "Two people of the same sex cannot marry"
        assert spouse.get_ethnicity() == self.get_ethnicity(), "Two people of different ethnicities cannot marry"
        self._spouse = spouse
        spouse._spouse = self
        # Also assign first birth timing and desired number of children to the 
        # female (if not already defined, which it will be for initial agents).
        if self.get_sex()=="female":
            female=self
        else:
            female=spouse
            female._des_num_children = calc_des_num_children(self)
        self._marriage_time = time
        spouse._marriage_time = time

    def divorce(self):
        assert self.get_spouse() != None, "Person %s cannot divorce as they are not married"%(person.get_ID())
        spouse = self._spouse
        spouse._spouse = None
        self._spouse = None

    def is_eligible_for_birth(self, time):
        """
        Check birth timing using Ghimire and Axinn, 2010 first birth timing 
        results or simple probability distribution for first birth timing, 
        depending on the choice of rcparams.
        """
        # Check that the woman has been married long_enough (first birth time), 
        # didn't already give birth more recently than the minimum birth 
        # interval and does not already have greater than their desired family 
        # size.  Note that des_num_children=-1 means no preference ("god's 
        # will").
        if (not (self.get_sex() == 'female')) or (not self.is_married()):
            return False

        if (self._age > (rcParams['birth.max_age.years'] * 12)) | \
                (self._age < (rcParams['birth.min_age.years'] * 12)):
            return False

        # Handle first births using the appropriate first birth timing 
        # parameterization:
        num_children = self.get_num_children()
        if (num_children) == 0:
            first_birth_flag = False
            #TODO: Remove this line after debugging.
            if ((time - self._marriage_time) >= 6.):
                return False
            if rcParams['model.parameterization.firstbirthtiming'] == 'simple':
                if (time - self._marriage_time) >= self._first_birth_timing/12.:
                    first_birth_flag = True
            elif rcParams['model.parameterization.firstbirthtiming'] == 'ghimireaxinn2010':
                if (random_state.rand() < calc_first_birth_prob_ghimireaxinn2010(self, time)) & ((time - self._marriage_time) >= 9/12.):
                    first_birth_flag = True
            elif rcParams['model.parameterization.firstbirthtiming'] == 'zvoleff':
                if (random_state.rand() < calc_first_birth_prob_zvoleff(self, time)) & ((time - self._marriage_time) >= 9/12.):
                    first_birth_flag = True
            else:
                raise Exception("Unknown option for first birth timing parameterization: '%s'"%rcParams['model.parameterization.firstbirthtiming'])
            if first_birth_flag == True:
                logger.debug("First birth to agent %s (age %.2f, marriage time %.2f)"%(self.get_ID(), self.get_age_years(), self._marriage_time))
                return True
            else: return False
        else:
            # Handle births to mothers who have already given birth in the 
            # past:
            if self._last_birth_time >= (time - self._birth_interval/12.):
                return False
            elif (num_children < self._des_num_children) or (self._des_num_children==-1):
                # self._des_num_children = -1 means no preference
                return True
            else: return False

    def give_birth(self, time, father):
        "Agent gives birth. New agent inherits characterists of parents."
        assert self.get_sex() == 'female', "Men can't give birth"
        assert self.get_spouse().get_ID() == father.get_ID(), "All births must be in marriages"
        assert self.get_ID() != father.get_ID(), "No immaculate conception (agent: %s)"%(self.get_ID())
        baby = self._world.new_person(birthdate=time, age=0, mother=self, father=father, ethnicity=self.get_ethnicity())

        neighborhood = self.get_parent_agent().get_parent_agent()
    
        # Set childhood community context for baby
        baby._child_school_lt_1hr_ft = neighborhood._school_min_ft < 60
        baby._child_health_lt_1hr_ft = neighborhood._health_min_ft < 60
        baby._child_bus_lt_1hr_ft = neighborhood._bus_min_ft < 60
        baby._child_market_lt_1hr_ft = neighborhood._market_min_ft < 60
        baby._child_employer_lt_1hr_ft = neighborhood._employer_min_ft < 60

        baby._birth_household_ID = self.get_parent_agent().get_ID()
        baby._birth_neighborhood_ID = neighborhood.get_ID()

        self._last_birth_time = time

        # Assign a new birth interval for the next child
        self._birth_interval = calc_birth_interval()
        for parent in [self, father]:
            parent._children.append(baby)
            parent._number_of_children += 1
        logger.debug('New birth to %s, (age %.2f, %s total children, %s desired, next birth %.2f)'%(self.get_ID(), self.get_age_years(), self._number_of_children, self._des_num_children, self._birth_interval))
        return baby

    def is_married(self):
        "Returns a boolean indicating if person is married or not."
        if self._spouse == None:
            return False
        else:
            return True

    def __str__(self):
        return "Person(PID: %s. Household: %s. Neighborhood: %s)" %(self.get_ID(), self.get_parent_agent().get_ID(), self.get_parent_agent().get_parent_agent().get_ID())

class Household(Agent_set):
    "Represents a single household agent"
    def __init__(self, world, ID=None, initial_agent=False):
        Agent_set.__init__(self, world, ID, initial_agent)
        self._any_non_wood_fuel = boolean_choice(.93) # From DS0002$BAE15
        self._own_house_plot = boolean_choice(.829)  # From DS0002$BAA43
        self._own_land = boolean_choice(.61) # From Axinn, Ghimire (2007)
        self._rented_out_land = boolean_choice(.11) # From Axinn, Ghimire (2007)
        self._lastmigrant_time = None
        self._hh_area = 0 # Area of house plot in square meters

    def any_non_wood_fuel(self):
        "Boolean for whether household uses any non-wood fuel"
        return self._any_non_wood_fuel
    
    def get_hh_head(self):
        max_age = None
        if self.num_members() == 0:
            raise AgentError("No household head for household %s. Household has no members"%self.get_ID())
        for person in self.get_agents():
            if person.get_age_months() > max_age:
                max_age = person.get_age_months()
                hh_head = person
        return hh_head

    def own_house_plot(self):
        "Boolean for whether household owns the plot of land on which it resides"
        return self._own_house_plot

    def own_any_land(self):
        "Boolean for whether household owns any land"
        return self._own_land

    def rented_out_land(self):
        "Boolean for whether household rented out any of its land"
        return self._rented_out_land

    def is_initial_agent(self):
        return self._initial_agent

    def fw_usage(self, time):
        fw_usage = calc_fuelwood_usage(self, time)
        # Convert daily fw_usage to monthly
        fw_usage = fw_usage * 30
        return fw_usage

    def remove_agent(self, person):
        """
        Remove a person from this household. Override the default method for an 
        Agent_set so that we can check if the removal of this agent would leave 
        this household empty. It it would leave it empty, they destroy this 
        household after removing the agent. Otherwise, run the normal method 
        for agent removal from a household Agent_set.
        """
        Agent_set.remove_agent(self, person)
        if self.num_members() == 0:
            logger.debug("Household %s left empty - household removed from model"%self.get_ID())
        #    neighborhood = self.get_parent_agent()
        #    neighborhood._land_agveg += self._hh_area
        #    neighborhood._land_privbldg -= self._hh_area
        #    neighborhood.remove_agent(neighborhood)

    def __str__(self):
        return "Household(HID: %s. %s person(s))"%(self.get_ID(), self.num_members())

class Neighborhood(Agent_set):
    "Represents a single neighborhood agent"
    def __init__(self, world, ID=None, initial_agent=False):
        Agent_set.__init__(self, world, ID, initial_agent)
        self._avg_years_nonfamily_services = None
        self._elec_available = None
        self._land_agveg = None
        self._land_nonagveg = None
        self._land_privbldg = None
        self._land_pubbldg = None
        self._land_other = None
        self._distnara = None
        self._x = None # x coordinate in UTM45N
        self._y = None # y coordinate in UTM45N
        self._elev = None # Elevation of neighborhood from SRTM DEM

        # These values are set in the initialize.py script.
        self._school_min_ft = None
        self._health_min_ft = None
        self._bus_min_ft = None
        self._market_min_ft = None
        self._employer_min_ft = None

    def add_agent(self, agent, initializing=False):
        """
        Subclass the Agent_set.add_agent function in order to account for LULC 
        change with new household addition.
        """
        # The "initializing" variable allows ignoring the land cover 
        # addition/subtraction while initializing the model with the CVFS data.
        if initializing==True:
            Agent_set.add_agent(self, agent)
        else:
            hh_area = calc_hh_area()
            if self._land_agveg - hh_area < 0:
                if self._land_nonagveg - hh_area < 0:
                    return False
                else:
                    self._land_nonagveg -= hh_area
                    self._land_privbldg += hh_area
                    Agent_set.add_agent(self, agent)
                    return True
            else:
                self._land_agveg -= hh_area
                self._land_privbldg += hh_area
                Agent_set.add_agent(self, agent)
                return True
            # Should never get to this line:
            return False

    def is_initial_agent(self):
        return self._initial_agent

    def avg_years_nonfamily_services(self):
        "Average number of years non-family services have been available."
        return self._avg_years_nonfamily_services

    def elec_available(self):
        "Boolean for whether neighborhood has electricity."
        return self._elec_available

    def get_num_psn(self):
        "Returns the number of people in the neighborhood."
        num_psn = 0
        for household in self.iter_agents():
            num_psn += household.num_members()
        return num_psn

    def get_num_marriages(self):
        "Returns the total number of marriages in this neighborhood."
        num_marr = 0
        spouses = []
        for household in self.iter_agents():
            for person in household.iter_agents():
                if person.is_married() and (person.get_spouse() not in spouses):
                    num_marr += 1
                    spouses.append(person)
        return num_marr

    def get_hh_sizes(self):
        hh_sizes = {}
        for household in self.iter_agents():
            hh_sizes[household.get_ID()] = household.num_members()
        return hh_sizes

    def get_coords(self):
        return self._x, self._y

    def __str__(self):
        return "Neighborhood(NID: %s. %s household(s))" %(self.get_ID(), self.num_members())

class Region(Agent_set):
    """Represents a set of neighborhoods sharing a spatial area (and therefore 
    land use data), and demographic characteristics."""
    def __init__(self, world, ID=None, initial_agent=False):
        Agent_set.__init__(self, world, ID, initial_agent)

        # Maintain a list of agent_stores in a dictionary keyed by agent type 
        # and then by store name. This allows iterating over all agent stores 
        # for a particular agent type, which is important for things like 
        # iterating the ages of all persons in the model, even those who may be 
        # away from their neighborhood.
        self._agent_stores = {}
        # The agent_store instances are used to store migrants while they are 
        # away from their household (prior to their return).  LL_agent_store 
        # stores local-local migrants while LD_migr_agent_store stores 
        # local-distant migrants.
        self._agent_stores['person'] = {}
        self._agent_stores['person']['LL_migr'] = Agent_Store()
        self._agent_stores['person']['LD_migr'] = Agent_Store()

        # TODO: Demographic variables could be setup here to be specific for 
        # each region - these could be used to represent different strata.

    def __repr__(self):
        #TODO: Finish this
        return "__repr__ UNDEFINED"

    def __str__(self):
        return "Region(RID: %s, %s neighborhood(s), %s household(s), %s person(s))"%(self.get_ID(), \
                len(self._members), self.num_households(), self.num_persons())

    def is_initial_agent(self):
        return self._initial_agent

    def iter_households(self):
        "Returns an iterator over all the households in the region"
        for neighborhood in self.iter_agents():
            for household in neighborhood.iter_agents():
                yield household

    def iter_persons(self):
        """
        Returns an iterator over all the persons in the region that are NOT 
        within an agent_store class instance (so only those resident in 
        Chitwan).
        """
        for household in self.iter_households():
            for person in household.iter_agents():
                yield person

    def iter_all_persons(self):
        """"
        Returns an iterator over all the persons in the region, including those 
        within agent store class instances. Necessary for doing things that 
        apply to all agents regardless of their status, like incrementing ages.
        """
        for household in self.iter_households():
            for person in household.iter_agents():
                yield person
        for agent_store in self.iter_person_agent_stores():
            for person in agent_store._stored_agents:
                yield person

    def iter_person_agent_stores(self):
        for agent_store_name in self._agent_stores['person'].keys():
            yield self._agent_stores['person'][agent_store_name]

    def births(self, time):
        """Runs through the population and agents give birth probabilistically 
        based on their birth interval and desired family size."""
        logger.debug("Processing births")
        births = {}
        for household in self.iter_households():
            for person in household.iter_agents():
                if person.is_eligible_for_birth(time):
                    # Agent gives birth. First find the father (assumed to be 
                    # the spouse of the person giving birth).
                    father = person.get_spouse()
                    # Now have the mother give birth, and add the 
                    # new person to the mother's household.
                    household.add_agent(person.give_birth(time,
                        father=father))
                    if rcParams['feedback.birth.nonagveg']:
                        neighborhood = household.get_parent_agent()
                        if (neighborhood._land_nonagveg - rcParams['feedback.birth.nonagveg.area']) >= 0:
                            neighborhood._land_nonagveg -= rcParams['feedback.birth.nonagveg.area']
                            neighborhood._land_other += rcParams['feedback.birth.nonagveg.area']
                    # Track the total number of births for each 
                    # timestep by neighborhood.
                    if not births.has_key(neighborhood.get_ID()):
                        births[neighborhood.get_ID()] = 0
                    births[neighborhood.get_ID()] += 1
        return births
                        
    def deaths(self, time):
        """Runs through the population and kills agents probabilistically based 
        on their age and sex and the probability.death for this population"""
        logger.debug("Processing deaths")
        deaths = {}
        for household in self.iter_households():
            for person in household.iter_agents():
                if random_state.rand() < calc_probability_death(person):
                    # Agent dies.
                    person.kill(time)
                    neighborhood = household.get_parent_agent()
                    if not deaths.has_key(neighborhood.get_ID()):
                        deaths[neighborhood.get_ID()] = 0
                    deaths[neighborhood.get_ID()] += 1
        return deaths
                        
    def marriages(self, time):
        """
        Runs through the population and marries agents probabilistically based 
        on their age and the probability_marriage for this population
        """
        logger.debug("Processing marriages")
        # First find the eligible agents
        minimum_age = rcParams['marriage.minimum_age_years']
        maximum_age = rcParams['marriage.maximum_age_years']
        eligible_males = []
        eligible_females = []
        for household in self.iter_households():
            for person in household.iter_agents():
                if (not person.is_married()) and \
                        (person.get_age_years() >= minimum_age) and \
                        (person.get_age_years() <= maximum_age) and \
                        (random_state.rand() < calc_probability_marriage(person)):
                    # Agent is eligible to marry.
                    if person.get_sex() == "female": eligible_females.append(person)
                    if person.get_sex() == "male": eligible_males.append(person)
        logger.debug('%s resident males and %s resident females eligible for marriage'%(len(eligible_males), len(eligible_females)))
        eligible_persons = eligible_males + eligible_females

        couples = []
        for person in eligible_persons:
            # The 'choose_spouse' function in statistics.py chooses a spouse
            # based on the probability of a person man marrying each other 
            # person of opposite sex in the eligible_persons list, with the 
            # probability dependent on the age difference between the person 
            # and each potential spouse in the list.
            if len(eligible_persons) == 0: break
            spouse = choose_spouse(person, eligible_persons)
            if spouse == None:
                # In this case there are no eligible spouses for this person 
                # (because all the other persons are of a different ethnicity).
                continue
            eligible_persons.remove(spouse)
            eligible_persons.remove(person)
            if person.get_sex() == "male": couples.append((person, spouse))
            else: couples.append((spouse, person))
        logger.debug("%s resident couples formed, %s couples with in-migrants"%(len(couples), len(eligible_persons)))

        # The remaining individuals marry in-migrants
        for person in eligible_persons:
            frac_year, years = np.modf(calc_spouse_age_diff(person))
            months = np.round(frac_year * 12)
            age_diff_months = years * 12 + months
            if person.get_sex() == "female":
                spouse_sex = "male"
                spouse_age_months = person.get_age_months() + age_diff_months
            else:
                spouse_sex = "female"
                spouse_age_months = person.get_age_months() - age_diff_months
            if spouse_age_months < rcParams['marriage.minimum_age_years']:
                spouse_age_months = rcParams['marriage.minimum_age_years']
            # Create the spouse:
            spouse_birthdate = time - spouse_age_months/12.
            spouse = self._world.new_person(birthdate=spouse_birthdate, 
                    age=spouse_age_months, sex=spouse_sex,
                    ethnicity=person.get_ethnicity(), in_migrant=True)
            # Ensure that the man is first in the couples tuple
            if person.get_sex() == "female": couples.append((spouse, person))
            else: couples.append((person, spouse))

        marriages = {}
        # Now marry the agents
        for male, female in couples:
            # First marry the agents.
            male.marry(female, time)
            female._first_birth_timing = calc_first_birth_time(self)
            moveout_prob = rcParams['prob.marriage.moveout']
            # Create a new household according to the moveout probability
            if boolean_choice(moveout_prob) or male.get_parent_agent() == None:
                # Create a new household. male.get_parent_agent() is equal to 
                # None for in-migrants, as they are not a member of a 
                # household.
                new_home = self._world.new_household()
                poss_neighborhoods = [] # Possible neighborhoods for the new_home
                for person in [male, female]:
                    old_household = person.get_parent_agent() # this person's old household
                    if old_household != None:
                        # old_household will equal none for in-migrants, as 
                        # they are not tracked in the model until after this 
                        # timestep. This means they also will not have a 
                        # neighborhood yet, so the next two lines would not 
                        # work.
                        poss_neighborhoods.append(old_household.get_parent_agent()) # this persons old neighborhood
                        old_household.remove_agent(person)
                    new_home.add_agent(person)
                # Assign the new household to the male or females neighborhood.  
                # Or randomly pick new neighborhood if both members of the 
                # couple are in-migrants.
                if len(poss_neighborhoods)>0:
                    # len(poss_neighborhoods) is greater than zero if at least one 
                    # is NOT an in-migrant. Choose male's neighborhood by 
                    # default.
                    neighborhood = poss_neighborhoods[0]
                else:
                    poss_neighborhoods = self.get_agents()
                    neighborhood = poss_neighborhoods[np.random.randint( \
                        len(poss_neighborhoods))]
                # Try to add the household to the chosen neighborhood. If
                # the add_agent function returns false it means there is no 
                # available land in the chosen neighborhood, so pick another 
                # neighborhood, iterating through the closest neighborhoods 
                # until one is found with adequate land:
                n = 0
                while neighborhood.add_agent(new_home) == False:
                    neighborhood = neighborhood._neighborhoods_by_distance[n]
                    n += 1
            else:
                # Otherwise they stay in the male's household. So have the 
                # female move in.
                old_household = female.get_parent_agent() # this person's old household
                # old_household will equal none for in-migrants, as they are 
                # not tracked in the model until after this timestep.
                if old_household != None: old_household.remove_agent(female)
                male_household = male.get_parent_agent()
                male_household.add_agent(female)
                neighborhood = male.get_parent_agent().get_parent_agent()
            if not marriages.has_key(neighborhood.get_ID()):
                marriages[neighborhood.get_ID()] = 0
            marriages[neighborhood.get_ID()] += 1
        return marriages

    def divorces(self, time):
        """
        Runs through the population and marries agents probabilistically 
        based on their age and the probability_marriage for this population
        """
        logger.debug("Processing divorces")
        # First find the divorcing agents
        checked_spouses = []
        divorces = {}
        for household in self.iter_households():
            for person in household.iter_agents():
                if (not person.is_married()) or \
                        (person in checked_spouses) or \
                        (random_state.rand() >= calc_probability_divorce(person)):
                    # Person does NOT get divorced
                    checked_spouses.append(person)
                    continue
                # Person DOES get divorced:
                checked_spouses.append(person)
                neighborhood = household.get_parent_agent()
                # Make the woman move out and either:
                # 	- return to her parental home if it still exists
                # 	- establish a new household in a randomly selected              
                # 	neighborhood
                if person.get_sex() == "female":
                    woman = person
                else: woman = person.get_spouse()
                person.divorce()
                woman.get_parent_agent().remove_agent(woman)
                if woman.get_mother() == None or \
                        woman.get_mother().get_parent_agent() == None:
                    # First make a new home for the woman
                    new_home = self._world.new_household()
                    new_home.add_agent(woman)
                    # Now find a neighborhood for the new home
                    poss_neighborhoods = self.get_agents()
                    new_neighborhood = poss_neighborhoods[np.random.randint( \
                        len(poss_neighborhoods))]
                    new_neighborhood.add_agent(new_home)
                else:
                    # If the woman's mother's home still exists, move the woman 
                    # to that home.
                    new_home = woman.get_mother().get_parent_agent()
                    new_home.add_agent(woman)
                if not divorces.has_key(neighborhood.get_ID()):
                    divorces[neighborhood.get_ID()] = 0
                divorces[neighborhood.get_ID()] += 1
                logger.debug("Divorce to agent %s (age %.2f, marriage time %.2f)"%(person.get_ID(), person.get_age_years(), person._marriage_time))
        return divorces

    def get_num_marriages(self):
        "Returns the total number of marriages in this region."
        num_marr = 0
        spouses = []
        for person in self.iter_persons():
            if person.is_married() and (person.get_spouse() not in spouses):
                    num_marr += 1
                    spouses.append(person)
        return num_marr

    def education(self, time):
        """
        Runs through the population and makes agents probabilistically attend 
        schooling based on their age and the education function for this 
        population.
        """
        logger.debug("Processing education")
        timestep = rcParams['model.timestep']
        start_school_age = rcParams['education.start_school_age_years']
        schooling = {}
        for person in self.iter_persons():
            if person._school_status == "outofschool":
                pass
            elif (person._school_status == "undetermined") & (person.get_age_years() >= start_school_age):
                person._school_status = "inschool"
                person._final_schooling_level = calc_education_level(person)
                person._schooling = timestep / 12
            elif person._school_status == "inschool":
                if person._schooling >= person._final_schooling_level:
                    person._school_status = "outofschool"
                else:
                    person._schooling += timestep / 12
            neighborhood = person.get_parent_agent().get_parent_agent()
            #if not schooling.has_key(neighborhood.get_ID()):
            #    schooling[neighborhood.get_ID()] = person._schooling
            #schooling[neighborhood.get_ID()] += 1
        return schooling

    def migrations(self, time):
        """
        Runs through the population and makes agents probabilistically migrate
        based on their age and the probability_marriage for this population.
        """
        # First handle out-migrations
        logger.debug("Processing migrations")
        out_migr = {}
        for household in self.iter_households():
            for person in household.iter_agents():
                if random_state.rand() < calc_probability_migration(person):
                    household._lastmigrant_time = time
                    # Agent migrates. Choose how long the agent is migrating 
                    # for from a probability distribution.
                    months_away = calc_migration_length(person)
                    # The add_agent function of the agent_store class also 
                    # handles removing the agent from its parent (the 
                    # household).
                    self._agent_stores['person']['LD_migr'].add_agent(person, time+(months_away/12))
                    neighborhood = household.get_parent_agent()
                    if not out_migr.has_key(neighborhood.get_ID()):
                        out_migr[neighborhood.get_ID()] = 0
                    out_migr[neighborhood.get_ID()] += 1

        # Now handle the returning migrants (based on the return times assigned 
        # to them when they initially outmigrated)
        return_migr = self._agent_stores['person']['LD_migr'].release_agents(time)

        # Now handle inmigrations:
        new_in_migr = {}
        num_in_migr_households = calc_num_inmigrant_households()
        logger.debug("%s in-migrant households"%num_in_migr_households)

        timestep = rcParams['inmigrant.prob.ethnicity']
        timestep = rcParams['inmigrant.prob.hh_size']
        timestep = rcParams['inmigrant.prob.hh_head_age']
        
        return out_migr, return_migr, new_in_migr

    def increment_age(self):
        """
        Adds one to the age of each agent. The units of age are dependent on 
        the units of the input rc parameters.
        """
        logger.debug("Incrementing ages")
        n_LL_migrants_away = 0
        n_LD_migrants_away = 0
        unmarr_females = 0
        unmarr_males = 0
        max_age_male = 0.
        max_age_female = 0.
        age_sum_female = 0.
        age_sum_male = 0.
        n_female = 0.
        n_male = 0.
        person_IDs = []
        for person in self.iter_all_persons():
            assert (person.get_ID() not in person_IDs), ("Age of person %s incremented twice"%person.get_ID())
            person_IDs.append(person.get_ID())
            timestep = rcParams['model.timestep']
            person._age += timestep
            # Track some extra information for logging
            if person.get_sex() == 'female':
                n_female += 1
                age_sum_female += person.get_age_years()
                if person.get_age_years() > max_age_female: max_age_female = person.get_age_years()
            else:
                n_male += 1
                age_sum_male += person.get_age_years()
                if person.get_age_years() > max_age_male: max_age_male = person.get_age_years()
            if (person._spouse != None):
                if person.get_sex() == 'female': unmarr_females += 1
                else: unmarr_males += 1
            if self._agent_stores['person']['LD_migr'] in person._store_list: n_LD_migrants_away += 1
            elif self._agent_stores['person']['LL_migr'] in person._store_list: n_LL_migrants_away += 1
        logger.debug('%s unmarried females, %s unmarried males'%(unmarr_males, unmarr_females))
        logger.debug('Oldest female is %.2f, oldest male is %.2f'%(max_age_female, max_age_male))
        logger.debug('Mean age of women is %.2f, mean age of men is %.2f'%((age_sum_male/n_male), (age_sum_female/n_female)))
        logger.debug('%s LL migrants away, %s LD migrants away'%(n_LL_migrants_away, n_LD_migrants_away))

    def get_neighborhood_fw_usage(self, time):
        fw_usage = {}
        for neighborhood in self.iter_agents():
            fw_usage[neighborhood.get_ID()] = 0
            for household in neighborhood.iter_agents():
                fw_usage[neighborhood.get_ID()] += household.fw_usage(time)
        return {'fw_usage': fw_usage}

    def get_neighborhood_landuse(self):
        landuse = {'agveg':{}, 'nonagveg':{}, 'privbldg':{}, 'pubbldg':{}, 'other':{}}
        for neighborhood in self.iter_agents():
            landuse['agveg'][neighborhood.get_ID()] = neighborhood._land_agveg
            landuse['nonagveg'][neighborhood.get_ID()] = neighborhood._land_nonagveg
            landuse['privbldg'][neighborhood.get_ID()] = neighborhood._land_privbldg
            landuse['pubbldg'][neighborhood.get_ID()] = neighborhood._land_pubbldg
            landuse['other'][neighborhood.get_ID()] = neighborhood._land_other
        return landuse

    def get_neighborhood_pop_stats(self):
        """
        Used each timestep to return a dictionary of neighborhood-level 
        population statistics.
        """
        pop_stats = {'num_psn':{}, 'num_hs':{}, 'num_marr':{}}
        for neighborhood in self.iter_agents():
            if not pop_stats.has_key(neighborhood.get_ID()):
                pop_stats[neighborhood.get_ID()] = {}
            pop_stats['num_psn'][neighborhood.get_ID()] = neighborhood.get_num_psn()
            pop_stats['num_hs'][neighborhood.get_ID()] = neighborhood.num_members()
            pop_stats['num_marr'][neighborhood.get_ID()] = neighborhood.get_num_marriages()
        return pop_stats

    def num_persons(self):
        "Returns the number of persons in the population."
        total = 0
        for household in self.iter_households():
            total += household.num_members()
        return total

    def num_households(self):
        total = 0
        for neighborhood in self.iter_agents():
            total += len(neighborhood.get_agents())
        return total

    def num_neighborhoods(self):
        return len(self._members.values())

class World():
    """
    The world class generates new agents, while tracking ID numbers to ensure 
    that they are always unique across each agent type. It also contains a 
    dictionary with all the regions in the model.
    """
    def __init__(self):
        # _members stores member regions in a dictionary keyed by RID
        self._members = {}

        # These IDGenerator instances generate unique ID numbers that are never 
        # reused, and always unique (once used an ID number cannot be 
        # reassigned to another agent). All instances of the Person class, for  
        # example, will have a unique ID number generated by the PIDGen 
        # IDGenerator instance.
        self._PIDGen = IDGenerator()
        self._HIDGen = IDGenerator()
        self._NIDGen = IDGenerator()
        self._RIDGen = IDGenerator()

    def set_DEM_data(self, DEM, gt, prj):
        self._DEM_array = DEM
        self._DEM_gt = gt
        self._DEM_prj = prj
        return 0

    def get_DEM(self):
        return self._DEM_array

    def get_DEM_data(self):
        return self._DEM_array, self._DEM_gt, self._DEM_prj

    def set_world_mask_data(self, world_mask, gt, prj):
        self._world_mask_array = world_mask
        self._world_mask_gt = gt
        self._world_mask_prj = prj
        return 0

    def get_world_mask(self):
        return self._world_mask_array

    def get_world_mask_data(self):
        return self._world_mask_array, self._world_mask_gt, self._world_mask_prj

    def new_person(self, birthdate, PID=None, **kwargs):
        "Returns a new person agent."
        if PID == None:
            PID = self._PIDGen.next()
        else:
            # Update the generator so the PID will not be reused
            self._PIDGen.use_ID(PID)
        return Person(self, birthdate, ID=PID, **kwargs)

    def new_household(self, HID=None, **kwargs):
        "Returns a new household agent."
        if HID == None:
            HID = self._HIDGen.next()
        else:
            # Update the generator so the HID will not be reused
            self._HIDGen.use_ID(HID)
        return Household(self, ID=HID, **kwargs)

    def new_neighborhood(self, NID=None, **kwargs):
        "Returns a new neighborhood agent."
        if NID == None:
            NID = self._NIDGen.next()
        else:
            # Update the generator so the NID will not be reused
            self._NIDGen.use_ID(NID)
        return Neighborhood(self, ID=NID, **kwargs)

    def new_region(self, RID=None, initial_agent=False):
        "Returns a new region agent, and adds it to the world member list."
        if RID == None:
            RID = self._RIDGen.next()
        else:
            # Update the generator so the RID will not be reused
            self._RIDGen.use_ID(RID)
        region = Region(self, RID, initial_agent)
        self._members[region.get_ID()] = region
        return region

    def get_regions(self):
        return self._members.values()

    def iter_regions(self):
        "Convenience function for iteration over all regions in the world."
        for region in self._members.values():
            yield region

    def iter_persons(self):
        "Convenience function used for things like incrementing agent ages."
        for region in self.iter_regions():
            for person in region.iter_persons():
                yield person

    def write_persons_to_csv(self, timestep, results_path):
        """
        Writes a list of persons, with a header row, to CSV.
        """
        psn_csv_file = os.path.join(results_path, "psns_time_%s.csv"%timestep)
        out_file = open(psn_csv_file, "w")
        csv_writer = csv.writer(out_file)
        csv_writer.writerow(["pid", "hid", "nid", "rid", "gender", "ethnicity", "age", "spouseid", "father_id", "mother_id", "des_num_children", "first_birth_timing"])
        for region in self.iter_regions():
            for person in region.iter_persons():
                new_row = []
                new_row.append(person.get_ID())
                new_row.append(person.get_parent_agent().get_ID())
                new_row.append(person.get_parent_agent().get_parent_agent().get_ID())
                new_row.append(person.get_parent_agent().get_parent_agent().get_parent_agent().get_ID())
                new_row.append(person.get_sex())
                new_row.append(person.get_ethnicity())
                new_row.append(person.get_age_months())
                spouse = person.get_spouse()
                if spouse != None:
                    new_row.append(person.get_spouse().get_ID())
                else:
                    new_row.append(None)
                if person._mother != None:
                    new_row.append(person._mother.get_ID())
                else: 
                    new_row.append(None)
                if person._father != None:
                    new_row.append(person._father.get_ID())
                else: 
                    new_row.append(None)
                new_row.append(person._des_num_children)
                new_row.append(person._first_birth_timing)
                csv_writer.writerow(new_row)
        out_file.close()

    def write_NBHs_to_csv(self, timestep, results_path):
        """
        Writes a list of neighborhoods, with a header row, to CSV.
        """
        NBH_csv_file = os.path.join(results_path, "NBHs_time_%s.csv"%timestep)
        out_file = open(NBH_csv_file, "w")
        csv_writer = csv.writer(out_file)
        csv_writer.writerow(["nid", "rid", "x", "y", "numpsns", "numhs", "agveg",
            "nonagveg", "pubbldg", "privbldg", "other", "total_area",
            "perc_agveg", "perc_veg", "perc_bldg"])
        for region in self.iter_regions():
            for neighborhood in region.iter_agents():
                new_row = []
                new_row.append(neighborhood.get_ID())
                new_row.append(neighborhood.get_parent_agent().get_ID())

                x, y = neighborhood.get_coords()
                new_row.append(x)
                new_row.append(y)

                new_row.append(neighborhood.get_num_psn())
                new_row.append(neighborhood.num_members())

                new_row.append(neighborhood._land_agveg)
                new_row.append(neighborhood._land_nonagveg)
                new_row.append(neighborhood._land_pubbldg)
                new_row.append(neighborhood._land_privbldg)
                new_row.append(neighborhood._land_other)

                total_area = neighborhood._land_agveg + neighborhood._land_nonagveg + \
                        neighborhood._land_pubbldg + neighborhood._land_privbldg + \
                        neighborhood._land_other
                perc_agveg = neighborhood._land_agveg / total_area
                perc_veg = (neighborhood._land_agveg + neighborhood._land_nonagveg) \
                        / total_area
                perc_bldg = (neighborhood._land_privbldg + neighborhood._land_pubbldg) \
                        / total_area

                new_row.append(total_area)
                new_row.append(perc_agveg)
                new_row.append(perc_veg)
                new_row.append(perc_bldg)

                csv_writer.writerow(new_row)
        out_file.close()
