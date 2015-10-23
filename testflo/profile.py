"""
Methods to provide code profiling using cProfile.
"""
import os
try:
    import cProfile
except:
    import profile as cProfile

from testflo.pstats_viewer import view_pstats

# use to hold a global profile object
_profile = None
_prof_file = 'profile_%d_0.out' % os.getpid()
_prof_pattern = 'profile_%d_*.out' % os.getpid()

def setup_profile(options):
    global _profile
    if _profile is None and options.profile:
        _profile = cProfile.Profile()
    return _profile

def start_profile():
    if _profile:
        _profile.enable()

def stop_profile():
    if _profile:
        _profile.disable()

def save_profile():
    if _profile:
        _profile.dump_stats(_prof_file)

def finalize_profile(options):
    if _profile:
        # if we only have one process, then there are no workers to dump
        # the stats file, so do it here.
        if options.num_procs == 1:
            _profile.dump_stats(_prof_file)
        view_pstats(_prof_pattern, options)
