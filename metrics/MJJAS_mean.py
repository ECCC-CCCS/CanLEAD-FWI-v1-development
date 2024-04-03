"""
Take the central fire season (MJJAS) means, annually.
"""

# Set up code
import xarray as xr
import glob
import sys
import os
from config_stats import stats_chunks, add_realization_dim, get_MJJAS_data
from filepaths import fwipaths
import gc
import subprocess
tracking_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()

version = f'CanLEAD-FWI-{sys.argv[1]}-v1' # EWEMBI or S14FD
outpath = f'{fwipaths.output_data}{version}/summary_stats/RCP85/'
if not os.path.exists(outpath):
    os.makedirs(outpath)

ens_group = sys.argv[2] # ensemble set, 1 to 5
# get filenames of daily data for 10 ensemble members in the specified set
fls = glob.glob(f'{fwipaths.output_data}/{version}/r{ens_group}_*.nc')

# loop over realizations by filename
for fl in fls: 
    
    data = xr.open_dataset(fl, chunks=stats_chunks) # load data
    data = data.drop_vars(['time_bnds', 'fire_season_mask']) # keep FWI System outputs only
    
    # Select and return only MJJAS data with functions. Fill NaNs with zeros to ensure same length of fire season over time
    fs_data = get_MJJAS_data(data)
    
    # Take sesaonal mean
    outMJJAS = fs_data.resample(time='AS', loffset='120D').mean(keep_attrs=True) # add label offset of 120D so that labels are on May 1; only MJJAS data included
    for var in outMJJAS.data_vars: # append method in attrs
        outMJJAS[var].attrs['cell_methods'] = 'time: mean over season (interval: 1 day)' # in format: time: method1 within years time: method2 over years   
        del(outMJJAS[var].attrs['ancillary_variables'])
    # add ds attrs
    outMJJAS.attrs['frequency'] = 'annual fire season'
    outMJJAS.attrs['history'] = f'Generated by {sys.argv[0]}'
    outMJJAS.attrs['git_id'] = tracking_id
    outMJJAS.attrs['git_repo'] = 'https://github.com/ECCC-CCCS/CanLEAD-FWI-v1/' 
    
    # add realization as a dimension and realization attrs, via config func
    outMJJAS, realization_label = add_realization_dim(outMJJAS) # realization is taken from dataset attrs
    
    # set encoding
    encoding = {var: {'dtype': 'float32', 'zlib': True, 'complevel': 3, '_FillValue': 1e+20} for var in outMJJAS.data_vars} 
    for var in ['lat','lon']: 
        encoding[var] = {'dtype': 'float64', '_FillValue': None}  # for lat and lon
    
    # save
    outMJJAS.to_netcdf(f'{outpath}/MJJAS_mean_fillna/{realization_label}_{version}_MJJAS_mean_fillna.nc', encoding=encoding) 
       
    del([outMJJAS,data,realization_label])
    gc.collect()

  