#!/usr/bin/env python
"""
Part of Chitwan Valley agent-based model.

Wrapper to run a set of Chitwan ABM model runs: Reads in input parameters, then 
calls routines to initialize and run the model, and output model statistics.

NOTE: Borrows code from matplotlib, particularly for rcsetup functions.

Alex Zvoleff, azvoleff@mail.sdsu.edu
"""

import os
import sys
import getopt
import time
import pickle
import tempfile
import cStringIO
import subprocess

import numpy as np

from chitwanABM import rcParams, read_rc_params, initialize, modelloop
from chitwanABM.agents import Region
from chitwanABM.rcsetup import write_RC_file
from chitwanABM.plotting import plot_pop_stats

if rcParams['model.use_psyco'] == True:
    import psyco
    psyco.full()

def main(argv=None):
    if argv==None:
        argv = sys.argv

    try:
        rc_file = sys.argv[1]
        print "\nWARNING: using default rc params. Custom rc_file use is not yet implemented.\n"
    except IndexError:
        pass

    # The run_ID_number provides an ID number (built from the start time) to 
    # uniquely identify this model run.
    run_ID_number = time.strftime("%Y%m%d-%H%M%S")
    results_path = os.path.join(str(rcParams['model.resultspath']), run_ID_number)
    try:
        os.mkdir(results_path)
    except OSError:
        raise OSError("error creating results directory")
    
    # Initialize
    region = Region()
    initialize.assemble_region(region)

    # Run the model loop
    print "\n******************************************************************************"
    start_time = time.strftime("%m/%d/%Y %I:%M:%S %p")
    print  "%s: started model run number %s."%(start_time, run_ID_number)
    print "******************************************************************************\n"
    results = modelloop.main_loop(region)
    print "\n******************************************************************************"
    end_time = time.strftime("%m/%d/%Y %I:%M:%S %p") 
    print "%s: finished model run number %s."%(end_time, run_ID_number)

    print "******************************************************************************\n"
    
    # Store the run ID in the results for later tracking purposes
    results.set_model_run_ID(run_ID_number)
    
    # Save the results
    print "Saving results...",
    results_file = os.path.join(results_path, "results.P")
    output = open(results_file, 'w')
    pickle.dump(results, output)
    output.close()

    # Save a plot of the results.
    plot_file = os.path.join(results_path, "plot.pdf")
    plot_pop_stats(results, plot_file)

    # Save the output of "git show" so that the SHA-1 of the commit is saved, 
    # along with any diffs from the commit.  This file can also contain the 
    # start/stop times of the model run.
    git_show_file = os.path.join(results_path, "git_show.txt")
    commit_hash = git_info("/home/azvoleff/Code/Python/chitwanABM", git_show_file)

    # After running model, save rcParams to a file, along with the SHA-1 of the 
    # code version used to run it, and the start and finish times of the model 
    # run. Save this file in the same folder as the model output.
    run_RC_file = os.path.join(results_path, "chitwanABMrc")
    RC_file_header = """# This file contains the parameters used for a chitwanABM model run.
# Model run ID:\t%s
# Start time:\t%s
# End time:\t\t%s
# Code version:\t%s"""%(run_ID_number, start_time, end_time, commit_hash)
    write_RC_file(run_RC_file, RC_file_header, rcParams)

    print "done."

def git_info(code_path, git_show_file):
    try:
        out_file = open(git_show_file, "w")
    except IOError:
        raise IOError("error writing to git-show output file: %s"%(git_show_file))
    subprocess.check_call(['git-show','--pretty=format:%H'], stdout=out_file, cwd=code_path)
    out_file.close()

    in_file = open(git_show_file, "r")
    commit_hash = in_file.readline().strip('\n')
    in_file.close()

    return commit_hash
if __name__ == "__main__":
    sys.exit(main())
