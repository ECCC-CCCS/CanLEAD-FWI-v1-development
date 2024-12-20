"""
Count of the length of the fire season, annually, under RCP8.5.
"""

#%% Set up code
import xarray as xr
import glob
import sys
import os
from config_stats import stats_chunks, add_realization_dim
from filepaths import fwipaths
import gc
import subprocess
tracking_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()

version = f'CanLEAD-FWI-{sys.argv[1]}-v1' # S14FD or EWEMBI
outpath = f'{fwipaths.output_data}{version}/summary_stats/RCP85/fire_season_length/'
if not os.path.exists(outpath): # create outpath if it doesn't already exist
    os.makedirs(outpath)
    
# get filenames of daily data of all 50 realizations 
fls = glob.glob(f'{fwipaths.output_data}/{version}/*.nc') 

# Canada mask, excluding northern Arctic
final_mask = xr.open_dataset(f'{fwipaths.input_data}/CanLEAD_FWI_final_mask.nc')['CanLEAD_FWI_mask'] 

for fl in fls: # loop over realizations by filename
                          
    data = xr.open_dataset(fl, chunks=stats_chunks) # open data
    data = data.drop_vars(['FFMC', 'DMC', 'DC', 'ISI', 'BUI', 'FWI', 'DSR','time_bnds']) # drop all vars but fire_season_mask, but retain ds structure and attrs
    out = data.resample(time='AS').sum(keep_attrs=True) # take annual count of fire season days (since values are 1 in summer, 0 in winter, this equals count)
    
    out = out.rename({'fire_season_mask': 'fire_season'}) # rename variable to 'fire season'
    # define fire season attrs
    fs_attrs = dict(short_name = 'fire_season',
                    long_name = 'Fire Season Length',
                    cell_methods = 'time: count within years', # in format: time: method1 within years time: method2 over years
                    description = 'Number of days in the annual fire season (when there is measurable fire danger and '\
                                   +'fire weather calculations are turned on) based on temperature thresholds.'#,
                    # wait to assign units until a later step. units are 'days'
                    )
    out['fire_season'].attrs = fs_attrs # replace attrs with new attrs   
    out.attrs['frequency'] = 'year' # change attrs in outfile to reflect new frequency
    out.attrs['history'] = f'Generated by {sys.argv[0]}'
    out.attrs['git_id'] = tracking_id
    out.attrs['git_repo'] = 'https://github.com/ECCC-CCCS/CanLEAD-FWI-v1/' 
    
    # add realization as a dimension and realization attrs, via config func
    out, realization_label = add_realization_dim(out) 
    
    # set encoding
    encoding = {'fire_season': {'dtype': 'int16', '_FillValue': 32767} } # for fire season
    for var in ['lat','lon']: 
        encoding[var] = {'dtype': 'float64', '_FillValue': None}  # for lat and lon
        
    out = out.where(final_mask==100) # mask with Canadian boundaries and ecozone mask
        
    # save
    out.to_netcdf(f'{outpath}/{realization_label}_rcp85_{version}_fire_season_length.nc', encoding=encoding) 

    del([out,data,realization_label])
    gc.collect()