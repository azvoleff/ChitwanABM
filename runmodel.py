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

import numpy as np

from chitwanABM import rcParams, initialize, modelloop
from chitwanABM.agents import Region
from chitwanABM.rcsetup import write_RC_file

# Try to load a random state from the rcfile
if rcParams['model.RandomState'] != None:
    np.random.RandomState = rcParams['model.RandomState']
else:
    # Otherwise seed the RandomState with a known random integer, and save the 
    # seed for later reuse (for testing, etc.).
    RandomState = int(10**8 * np.random.random())
    rcParams['model.RandomState'] = RandomState

if rcParams['model.use_psyco'] == True:
    import psyco
    psyco.full()

def main():
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
    print time.strftime("%I:%M:%S %p") + ": started model run number %s."%(run_ID_number)
    print "******************************************************************************\n"
    results = modelloop.main_loop(region)
    print "\n******************************************************************************"
    print time.strftime("%I:%M:%S %p") + ":  finished model run." 
    print "******************************************************************************\n"

    
    # Save the results
    print "\nSaving results to text...",
    results_file = os.path.join(results_path, "results.P")
    output = open(results_file, 'w')
    pickle.dump(results, output)
    output.close()

    # After running model, save rcParams to a file, along with the SHA-1 of the 
    # code version used to run it, and the start and finish times of the model 
    # run. Save this file in the same folder as the model output.
    run_RC_file = os.path.join(results_path, "modelRunRC")
    write_RC_file(run_RC_file)
    # TODO: write a function that will save the output of "git show" so that 
    # the SHA-1 of the commit is saved, along with any diffs from the commit.  
    # This file can also contain the start/stop times of the model run.

    print "done."


if __name__ == "__main__":
    sys.exit(main())
