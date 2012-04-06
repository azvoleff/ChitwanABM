# Copyright 2011 Alex Zvoleff
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
Contains statistical models to calulate probabilities (such as of birth, and of 
marriage) and run OLS regressions (to calculate land use).
"""

import numpy as np

from ChitwanABM import rcParams

if rcParams['model.use_psyco'] == True:
    import psyco
    psyco.full()

probability_time_units = rcParams['probability.time_units']

class UnitsError(Exception):
    pass

def convert_probability_units(probability):
    """
    Converts probability so units match timestep used in the model, assuming probability 
    function is uniform across the interval.

    Conversions are made accordingly using conditional probability.
    """
    # If the probability time units don't match the model timestep units, then the 
    # probabilities need to be converted.
    if probability_time_units == 'months':
        pass
    elif probability_time_units == 'years':
        for key, value in probability.iteritems():
            probability[key] = 1 - (1 - value)**(1/12.)
    elif probability_time_units == 'decades':
        for key, value in probability.iteritems():
            probability[key] = 1 - (1 - value)**(1/120.)
    else:
        raise UnitsError("unhandled probability_time_units")
    return probability

#TODO: these probabilities should be derived from the region, not directly from rcParams
death_probabilities_male = convert_probability_units(rcParams['probability.death.male'])
death_probabilities_female = convert_probability_units(rcParams['probability.death.female'])
marriage_probabilities_male = convert_probability_units(rcParams['probability.marriage.male'])
marriage_probabilities_female = convert_probability_units(rcParams['probability.marriage.female'])
migration_probabilities_male = convert_probability_units(rcParams['probability.migration.male'])
migration_probabilities_female = convert_probability_units(rcParams['probability.migration.female'])

def __probability_index__(t):
    """
    Matches units of time in model to those the probability is expressed in. For 
    instance: if probabilities are specified for decades, whereas the model runs in 
    months, __probability_index__, when provided with an age in months, will convert 
    it to decades, rounding down. NOTE: all probabilities must be expressed with the 
    same time units.
    """
    if probability_time_units == 'months':
        return t
    elif probability_time_units == 'years':
        return int(round(t / 12.))
    elif probability_time_units == 'decades':
        return int(round(t / 120.))
    else:
        raise UnitsError("unhandled probability_time_units")

def calc_firstbirth_prob_ghimireaxinn2010(person, time):
    """
    Calculates the probability of a first birth in a given month for an agent, 
    using the results of Ghimire and Axinn, 2010.
    """
    #########################################################################
    # Intercept
    inner = rcParams['firstbirth.coef.intercept']

    #########################################################################
    # Adult community context
    neighborhood = person.get_parent_agent().get_parent_agent()
    percent_agveg = (neighborhood._land_agveg / neighborhood._land_total) * 100
    inner += rcParams['firstbirth.coef.percagveg'] * percent_agveg
    inner += rcParams['firstbirth.coef.avgyrsnonfam'] * neighborhood._avg_years_nonfamily_services
    inner += rcParams['firstbirth.coef.distnara'] * neighborhood._distnara
    inner += rcParams['firstbirth.coef.elec_avail'] * neighborhood._elec_available
    #inner += rcParams['firstbirth.coef.NBH_wealth_index'] * neighborhood._wealth_index

    #########################################################################
    # Childhood community context
    inner += rcParams['firstbirth.coef.child_school_1hr'] * person._child_school_1hr
    inner += rcParams['firstbirth.coef.child_health_1hr'] * person._child_health_1hr
    inner += rcParams['firstbirth.coef.child_bus_1hr'] * person._child_bus_1hr
    inner += rcParams['firstbirth.coef.child_emp_1hr'] * person._child_emp_1hr

    #inner += rcParams['firstbirth.coef.age_1st_marr']
    #inner += rcParams['firstbirth.coef.marr_dur_pre_1997']

    #########################################################################
    # Ethnicity (high caste hindu as reference case)
    ethnicity = person.get_ethnicity()
    assert ethnicity!=None, "Ethnicity must be defined"
    if ethnicity == "HighHindu":
        # This was the reference level
        pass
    elif ethnicity == "HillTibeto":
        inner += rcParams['firstbirth.coef.ethnicHillTibeto']
    elif ethnicity == "LowHindu":
        inner += rcParams['firstbirth.coef.ethnicLowHindu']
    elif ethnicity == "Newar":
        inner += rcParams['firstbirth.coef.ethnicNewar']
    elif ethnicity == "TeraiTibeto":
        inner += rcParams['firstbirth.coef.ethnicTeraiTibeto']
 
    #########################################################################
    # Education level of individual
    assert person._schooling !=None, "schoolinging must be defined"
    if person._schooling < 4:
        # This was the reference level
        pass
    elif person._schooling < 8:
        inner += rcParams['firstbirth.coef.schooling4']
    elif person._schooling < 11:
        inner += rcParams['firstbirth.coef.schooling8']
    elif person._schooling >= 11:
        inner += rcParams['firstbirth.coef.schooling11']

    #########################################################################
    # Parents characteristics
    inner += rcParams['firstbirth.coef.parents_contracep_ever'] * person._parents_contracep_ever


    #if person.is_initial_agent():
    # For initial agents, use the data from the CVFS.
    father_work = person._father_work
    father_school = person._father_school
    mother_work = person._mother_work
    mother_school = person._mother_school
    mother_num_children = person._mother_num_children
    #else:
        # For others (agents dynamically generated in the model - not from the 
        # CVFS data), use the most current simulated data.
        #if person.get_father()._work > 0: father_work = 1
        #else: father_work = 0
        #if person.get_father()._schooling > 0: father_school = 1
        #else: father_school = 0
        #if person.get_mother()._work > 0: mother_work = 1
        #else: mother_work = 0
        #if person.get_mother()._schooling > 0: mother_school = 1
        #else: mother_school = 0
        #mother_num_children = person.get_mother().get_num_children()
    inner += rcParams['firstbirth.coef.father_work'] * father_work
    inner += rcParams['firstbirth.coef.father_school'] * father_school
    inner += rcParams['firstbirth.coef.mother_work'] * mother_work
    inner += rcParams['firstbirth.coef.mother_school'] * mother_school

    inner += rcParams['firstbirth.coef.mother_num_children'] * mother_num_children

    #########################################################################
    # Hazard duration
    marriage_time = time - person._marriage_time
    if marriage_time <= 6:
        inner += rcParams['firstbirth.coef.hazdur_6']
    elif marriage_time <= 12:
        inner += rcParams['firstbirth.coef.hazdur_12']
    elif marriage_time <= 18:
        inner += rcParams['firstbirth.coef.hazdur_18']
    elif marriage_time <= 24:
        inner += rcParams['firstbirth.coef.hazdur_24']
    elif marriage_time <= 30:
        inner += rcParams['firstbirth.coef.hazdur_30']
    elif marriage_time <= 36:
        inner += rcParams['firstbirth.coef.hazdur_36']
    elif marriage_time > 36:
        inner += rcParams['firstbirth.coef.hazdur_42']

    # Testing code:
    #prob = np.round(1./(1 + np.exp(-inner)), 4)
    #print "First birth probability: prob: %s (marriage_time: %s)"%(prob, mariage_time)
    return 1./(1 + np.exp(inner))

def calc_probability_marriage_yabiku2006(person):
    """
    Calculates the probability of marriage for an agent, using the results of 
    Yabiku, 2006.
    """
    neighborhood = person.get_parent_agent().get_parent_agent()

    inner = rcParams['marrtime.coef.intercept']

    # Neighborhood characteristics
    if neighborhood._land_agveg == 0:
        log_percent_agveg = 0
    else:
        log_percent_agveg = np.log((neighborhood._land_agveg / neighborhood._land_total)*100)
    inner += rcParams['marrtime.coef.logpercagveg'] * log_percent_agveg
    inner += rcParams['marrtime.coef.school_minft_1996'] * neighborhood._nfo_schl_minft_1996
    inner += rcParams['marrtime.coef.health_minft_1996'] * neighborhood._nfo_hlth_minft_1996
    inner += rcParams['marrtime.coef.bus_minft_1996'] * neighborhood._nfo_bus_minft_1996
    inner += rcParams['marrtime.coef.market_minft_1996'] * neighborhood._nfo_mar_minft_1996
    inner += rcParams['marrtime.coef.emp_minft_1996'] * neighborhood._nfo_emp_minft_1996

    if person.get_sex() == "female":
        inner += rcParams['marrtime.coef.female']

    ethnicity = person.get_ethnicity()
    assert ethnicity!=None, "Ethnicity must be defined"
    if ethnicity == "HighHindu":
        # This was the reference level
        pass
    elif ethnicity == "HillTibeto":
        inner += rcParams['marrtime.coef.ethnicHillTibeto']
    elif ethnicity == "LowHindu":
        inner += rcParams['marrtime.coef.ethnicLowHindu']
    elif ethnicity == "Newar":
        inner += rcParams['marrtime.coef.ethnicNewar']
    elif ethnicity == "TeraiTibeto":
        inner += rcParams['marrtime.coef.ethnicTeraiTibeto']

    # Convert person's age from months to years:
    age = person.get_age() / 12.
    inner += rcParams['marrtime.coef.age'] * age
    inner += rcParams['marrtime.coef.age_squared'] * (age**2)
    # Testing code:
    #prob = np.round(1./(1 + np.exp(-inner)), 4)
    #print "age: %s,  prob: %s"%(age, prob)
    return 1./(1 + np.exp(-inner))

def calc_probability_marriage_simple(person):
    """
    Calculate the probability of marriage using a simple sex and age dependent 
    probability distribution.
    """
    age = person.get_age()
    probability_index = __probability_index__(age)
    if person.get_sex() == 'female':
        return marriage_probabilities_female[probability_index]
    elif person.get_sex() == 'male':
        return marriage_probabilities_male[probability_index]

def calc_probability_death(person):
    "Calculates the probability of death for an agent."
    age = person.get_age()
    probability_index = __probability_index__(age)
    try:
        if person.get_sex() == 'female':
            return death_probabilities_female[probability_index]
        elif person.get_sex() == 'male':
            return death_probabilities_male[probability_index]
    except IndexError:
        raise IndexError("error calculating death probability (index %s)"%(probability_index))

def calc_probability_migration(person):
    "Calculates the probability of migration for an agent."
    age = person.get_age()
    probability_index = __probability_index__(age)
    if person.get_sex() == 'female':
        return migration_probabilities_female[probability_index]
    elif person.get_sex() == 'male':
        return migration_probabilities_male[probability_index]

def calc_first_birth_time(person):
    """
    Calculates the time from marriage until first birth for this person (not 
    used if the Ghimire and Axinn 2010 model is selected in rcparams.
    """
    first_birth_prob_dist = rcParams['prob.firstbirth.times']
    return int(draw_from_prob_dist(first_birth_prob_dist))

def calc_des_num_children(person):
    "Calculates the desired number of children for this person."
    des_num_children_prob_dist = rcParams['prob.num.children.desired']
    # Use np.floor as the last number in the des_num_children prob dist (10) is 
    # not actually seen in the Chitwan data. It is included only as the 
    # right-hand bound of the distribution.
    return np.floor(draw_from_prob_dist(des_num_children_prob_dist))

def calc_birth_interval():
    "Calculates the birth interval for this person."
    birth_interval_prob_dist = rcParams['prob.birth.intervals']
    return np.floor(draw_from_prob_dist(birth_interval_prob_dist ))

def calc_hh_area():
    "Calculates the area of this household."
    hh_area_prob_dist = rcParams['lulc.area.hh']
    return draw_from_prob_dist(hh_area_prob_dist)

def draw_from_prob_dist(prob_dist):
    """
    Draws a random number from a manually specified probability distribution,
    where the probability distribution is a tuple specified as:
        ([a, b, c, d], [1, 2, 3])
    where a, b, c, and d are bin limits, and 1, 2, and 3 are the probabilities 
    assigned to each bin. Notice one more bin limit must be specifed than the 
    number of probabilities given (to close the interval).
    """
    # First randomly choose the bin, with the bins chosen according to their 
    # probability.
    binlims, probs = prob_dist
    num = np.random.rand() * np.sum(probs)
    n = 0
    probcumsums = np.cumsum(probs)
    for upprob in probcumsums[1:]:
        if num < upprob:
            break
        n += 1
    upbinlim = binlims[n+1]
    lowbinlim = binlims[n]
    # Now we know the bin lims, so draw a random number evenly distributed 
    # between those two limits.
    return np.random.uniform(lowbinlim, upbinlim)

def calc_fuelwood_usage(household):
    """
    Calculates household-level fuelwood usage, using the results of a 2009 
    survey of fuelwood usage in the valley.
    """
    if household.num_members() == 0:
        return 0
    wood_usage = rcParams['fw_demand.coef.intercept']
    wood_usage += rcParams['fw_demand.coef.hhsize'] * household.num_members()
    wood_usage += rcParams['fw_demand.coef.hhsize_squared'] * household.num_members()
    if household.get_hh_head().get_ethnicity() == 1:
        # Upper caste Hindu is coded as 1
        wood_usage += rcParams['fw_demand.coef.ethnic']
    wood_usage += household.any_non_wood_fuel() * rcParams['fw_demand.coef.own_non_wood_stove']
    wood_usage += np.random.randn() + rcParams['fw_demand.residvariance']
    if wood_usage < 0:
        # Account for less than zero wood usage (could occur due to the random 
        # number added above to account for the low percent variance explained 
        # by the model).
        wood_usage = 0
    return wood_usage
