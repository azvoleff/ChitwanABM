#!/usr/bin/env python
"""
Part of Chitwan Valley agent-based model.

Plot basic statistics on a model run: From a set of model output files, 
plots basic statistics summarizing the model run.

Alex Zvoleff, azvoleff@mail.sdsu.edu
"""

import sys
import pickle

sys.path.append("/home/azvoleff/src/matplotlibsvn")

import numpy as np
import matplotlib.pyplot as plt

def main(argv=None):
    if argv is None:
        argv = sys.argv

    results_file = argv[1]
    plot_file = argv[2]

    results = load_results(results_file)
    plot_pop_stats(results, plot_file)

def load_results(results_file):
    try:
        in_file = open(results_file, 'r')
    except IOError:
        raise IOError("error loading results file %s"%(results_file))

    results = pickle.load(in_file)
    in_file.close()
    return results

def plot_pop_stats(results, plot_file):
    time = results.get_timesteps()

    num_persons = results.get_num_persons() # Final populations for each time step.
    births = results.get_num_births()
    deaths = results.get_num_deaths()
    marr = results.get_num_marriages()
    migr = results.get_num_migrations()

    events = [births, deaths, marr, migr]
    labels = ["Births", "Deaths", "Marriages", "Migrations"]

    plt.figure()
    plt.clf()

    # Plot the population vs time
    plt.plot(time, num_persons, color='k', linewidth=2, linestyle='-', label="Population")
    plt.plot(num_persons, time, )
    plt.ylabel("Population")

    # Setup the second axis (sharing the x-axis).
    axR = plt.twinx()
    axR.yaxis.tick_right()
    axR.yaxis.set_label_position("right")
    
    # Now plot births, deaths, and migrations, vs time.
    colors = ['k', '#ff6c01', '#00cd00', 'b']
    linewidths = [.75, .75, .75, .75]
    #linestyles = ['-', '--', '-.', ':']
    linestyles = ['-', '-', '-', '-']
    for event, color, linewidth, linestyle, label in zip(events, colors, linewidths, linestyles, labels):
        plt.plot(time, event, color=color, linewidth=linewidth, linestyle=linestyle, label=label)

    model_run_ID = results.get_model_run_ID()
    plot_title = "Model run statistics for %s"%(model_run_ID)
    #plt.title(plot_title)
    plt.annotate(model_run_ID, (.93,-.165), xycoords='axes fraction')
    plt.legend(loc='upper left')
    plt.xlabel("Year")
    plt.ylabel("Events (per  month)", rotation=270)

    set_tick_labels(time)
    
    plt.savefig(plot_file)
    plt.clf()

def shaded_plot_pop_stats(results_list, plot_file):
    """Make a shaded plot of pop stats that includes 2 standard deviations error 
    bars (as shaded regions around each line)."""
    time = results_list[0].get_timesteps()

    for results in results_list:
        assert results.get_timesteps() == time, "timesteps must be identical for all results"

    num_persons_array = np.array([result.get_num_persons() for result in results_list])
    births_array = np.array([result.get_num_births() for result in results_list])
    deaths_array = np.array([result.get_num_deaths() for result in results_list])
    marr_array = np.array([result.get_num_marriages() for result in results_list])
    migr_array = np.array([result.get_num_migrations() for result in results_list])

    events = [births_array, deaths_array, marr_array, migr_array]
    labels = ["Births", "Deaths", "Marriages", "Migrations"]

    plt.figure()
    plt.clf()

    # Plot the population vs time
    mean_persons = num_persons_array.mean(0)
    std_persons = num_persons_array.std(0)
    plt.plot(time, mean_persons, color='k', linewidth=2, linestyle='-', label="Population")
    plt.fill_between(time, mean_persons-(std_persons*2), mean_persons+(std_persons*2), color='k', linewidth=0, alpha=.5)
    plt.ylabel("Population")

    # Setup the second axis (sharing the x-axis).
    axR = plt.twinx()
    axR.yaxis.tick_right()
    axR.yaxis.set_label_position("right")
    
    # Now plot births, deaths, and migrations, vs time.
    colors = ['k', '#ff6c01', '#00cd00', 'b']
    linewidths = [.75, .75, .75, .75]
    #linestyles = ['-', '--', '-.', ':']
    linestyles = ['-', '-', '-', '-']
    for event, color, linewidth, linestyle, label in zip(events, colors, linewidths, linestyles, labels):
        mean = event.mean(0)
        std = event.std(0)
        plt.plot(time, mean, color=color, linewidth=linewidth, linestyle=linestyle, label=label)
        plt.fill_between(time, mean-(std*2), mean+(std*2), color=color, linewidth=0, alpha=.5)

    model_run_ID = results.get_model_run_ID()
    plot_title = "Model run statistics for %s"%(model_run_ID)
    #plt.title(plot_title)
    plt.annotate(model_run_ID, (.93,-.165), xycoords='axes fraction')
    plt.legend(loc='upper left')
    plt.xlabel("Year")
    plt.ylabel("Events (per  month)", rotation=270)

    set_tick_labels(time)
    
    plt.savefig(plot_file)
    plt.clf()

def set_tick_labels(time):
    # Label first year, last year, and years that end in 0 and 5
    tick_labels = [int(time[0])]
    tick_years = [time[0]]
    for value in time:
        # Remember to handle str -> floating point imprecision
        rounded_value = int(round(value))
        if abs(rounded_value - value) <= .02:
            if (rounded_value%10 == 0) or (rounded_value%5 == 0):
                tick_labels.append(rounded_value)
                tick_years.append(value)
    tick_labels.append(int(time[-1]))
    tick_years.append(time[-1])
    plt.xticks(tick_years, tick_labels)

if __name__ == "__main__":
    sys.exit(main())
