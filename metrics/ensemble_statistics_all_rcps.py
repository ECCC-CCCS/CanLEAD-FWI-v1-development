'''
Calculate the ensemble statistics for climatological values of metrics.
Update variable attributes and names to reflect absolute values, deltas,
or percentage deltas.
'''

import xarray as xr
import glob
import pandas as pd
import numpy as np
import datetime
import subprocess
import sys
from filepaths import fwipaths
import gc
tracking_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()

version = f'CanLEAD-FWI-{sys.argv[1]}-v1' # get CanLEAD version from job file
rcp = sys.argv[2] # get RCP from job file

test_statistics = ['fire_season_length',
                   'MJJAS_quantile_fillna',
                   'exceedances_high',
                   'exceedances_extreme',
                   'exceedances_moderate',
                   'MJJAS_mean_fillna',
                   'annual_exceedances_1971_2000_MJJAS_95th_quantile_fillna'
                   ]

outpath = f'{fwipaths.output_data}{version}/summary_stats/{rcp}/ensemble_percentiles/'

# Canada mask, excluding northern Arctic
final_mask = xr.open_dataset(f'{fwipaths.input_data}/CanLEAD_FWI_final_mask.nc')['CanLEAD_FWI_mask'] 

# create function to add file attrs
def add_attrs(ds):
    ds.attrs['creation_data'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ds.attrs['institution'] = 'Canadian Centre for Climate Services, Environment and Climate Change Canada'
    ds.attrs['institute_id'] = 'CCCS/ECCC'
    ds.attrs['domain'] = 'Canada land areas, excluding the Northern Arctic'
    ds.attrs['history'] = f'Generated by {sys.argv[0]}'
    ds.attrs['git_id'] = tracking_id
    ds.attrs['git_repo'] = 'https://github.com/ECCC-CCCS/CanLEAD-FWI/'
    ds.attrs['title'] = 'Canadian Forest Fire Weather Index (FWI) System projections based on CanLEAD-CanRCM4-EWEMBI'
    ds.attrs['references'] =  'Van Vliet, L. et al. In review. Developing user-informed fire weather projections for Canada. Climate Services. \n'\
                              +'Natural Resources Canada (NRCan). [no date]. Background Information: Canadian Forest Fire Weather '\
                              +'Index (FWI) System. Accessed on: 2023-04-27. '\
                              +'Available at: https://cwfis.cfs.nrcan.gc.ca/background/summary/fwi.'
    ds.attrs['index_package_information'] = 'FWI System outputs calculated using xclim 0.39.0 indices.fwi.fire_weather_ufunc '\
                                            +'and indices.fwi.fire_season. Reference: Logan, Travis, et al. Ouranosinc/xclim: '\
                                            +'V0.39.0. v0.39.0, Zenodo, 2 Nov. 2022, p., doi:10.5281/zenodo.7274811.'  
    # delete some repetitive attrs from daily files    
    del(ds.attrs['CanLEAD_CanRCM4_bc_method_id'], ds.attrs['CanLEAD_CanRCM4_bc_info'], ds.attrs['CanLEAD_CanRCM4_bc_observation_id'])
    # add RCP as an attr
    if rcp == 'RCP85':
        ds.attrs['rcp'] = 'RCP8.5' 
    elif rcp == 'constructed_RCP26':
        ds.attrs['rcp'] = 'Constructed RCP2.6' 
    elif rcp == 'constructed_RCP45':
        ds.attrs['rcp'] = 'Constructed RCP4.5' 
    return ds 

# function to add variable attrs
def add_var_attrs(ds, data_type, test_stat):
    '''
    Parameters
    ----------
    ds : DATASET
        Dataset to which to add attrs, ensemble statistics should already be applied.
    data_type : One of "absolute", "delta", or "percent_delta."
        Defines the units which will get added based on the type of data.
    test_stat : the metric, to determine which attrs are updated

    Returns
    -------
    Dataset with updated variable attrs.
    '''
    # set cell methods, long and short variable names for each data type
    method_cell = {"absolute": "",
                   'delta': ' time: difference from 1971-2000',
                   'percent_delta': ' time: percent difference from 1971-2000'}    
    method_short = {"absolute": "",
                    'delta': '_delta_1971_2000',
                    'percent_delta': '_percent_delta_1971_2000'}                  
    method_long = {"absolute": "",
                   'delta': ', difference from 1971-2000',
                   'percent_delta': ', percent difference from 1971-2000'}    

    # add variable attrs
    for var in ds.data_vars:
        # set all var attrs to those from input data, lost during processing for delta and percent delta    
        ds[var].attrs = alldat[var].attrs
        # then, update as needed
        if test_stat == 'MJJAS_mean_fillna': # update long and short name and cell methods
            del ds[var].attrs['ancillary_variables'] # delete this ancillary variable attrs, it's only relevant for daily data
            ds[var].attrs['long_name'] = f'{ds[var].attrs["long_name"]}: May to September mean value (NaNs filled with zeroes)' 
            ds[var].attrs['short_name'] = f'{ds[var].attrs["short_name"]}_MJJAS_fillna_mean'
            ds[var].attrs['cell_methods'] = 'time: mean over MJJAS (interval: 1 day) time: mean over years' 
        elif test_stat == 'MJJAS_quantile_fillna': # update long and short name and cell methods
            ds[var].attrs['long_name'] = f'{ds[var].attrs["long_name"]}: May to September (annual) quantile value (NaNs filled with zeroes)'
            ds[var].attrs['short_name'] = f'{ds[var].attrs["short_name"]}_MJJAS_fillna_quantile'
        elif test_stat == 'annual_exceedances_1971_2000_MJJAS_95th_quantile_fillna':
            ds[var].attrs['long_name'] = ds[var].attrs['long_name'].split(':')[0] + ': Count of days that exceed the 95th percentile May to September value (NaNs filled with zeroes) in 1971-2000'
            ds[var].attrs['short_name'] = ds[var].attrs['short_name'] + '_fillna'
        
        # update cell methods with climological stats interval (1 year) and data_type methods for all vars and metrics
        ds[var].attrs['cell_methods'] = ds[var].attrs['cell_methods'] + f' (interval: 1 year){method_cell[data_type]}'
        # update short and long name with delta methods
        ds[var].attrs['short_name'] = f'{ds[var].attrs["short_name"]}{method_short[data_type]}'
        ds[var].attrs['long_name'] = f'{ds[var].attrs["long_name"]}{method_long[data_type]}'
        if test_stat == 'fire_season_length': # update metric description for fire season length
            ds['fire_season'].attrs['description'] = 'Number of days in the annual fire season based on temperature thresholds '\
                                                     +'(when there is measurable fire danger and fire weather calculations are turned on).'
        else: # add reference to other description
            ds[var].attrs['description'] = f'{var}: "{ds[var].attrs["description"].split(" (")[0]}." (NRCan n.d.)'
        
        # set units based on data type
        if data_type == 'percent_delta':
            ds[var].attrs['units'] = 'percent'
        elif data_type in ["absolute", 'delta']:
            # set units to days for selected vars. For MJJAS_mean and MJJAS_quantile, units are already set to "" (dimensionless)
            if test_stat in ['exceedances_extreme', 'exceedances_high', 'exceedances_moderate', 'fire_season_length', 'annual_exceedances_1971_2000_MJJAS_95th_quantile_fillna']:
                ds[var].attrs['units'] = 'days'
    return ds
     
def return_wl(fl):
    '''
    From each dataset, obtain the warming level for each time period.
    Return these as a dataframe, with the column heading the realization name.

    '''
    ds = xr.open_dataset(fl) # open dataset
    real = ds.realization.values # get realization
    wls = ds.warming_level.values # get warming levels for each period as type string
    wls = [i.split(':')[1][:4] for i in wls] # extract only numeric warming level 
    df = pd.DataFrame(wls, columns=[real]).astype('float') # return as a dataframe, with the column heading the realization name
    return df
        
def reassign_wl(ds):
    ''' 
    Preprocess to remove base_rcp_period for constructed RCPs 2.6 and 4.5, which conflict between different 
    realizations and therefore won't allow auto-merge of datasets on import with open_mfdataset.
    Then, assign new WL coordinate that will be equivalent for all ensemble members.
    '''
    try:
        ds = ds.drop_vars(['source_rcp_period', 'source_rcp_period_first_year', 'warming_level'])
    except ValueError: # for RCP8.5
      pass
    ds = ds.assign_coords({'warming_level': ("period", wl_string)}) # assign WL as coordinate based on period. WL from wl_string defined below
    return ds

for test_stat in test_statistics: 
                                              
    cfls = glob.glob(f'{fwipaths.output_data}{version}/summary_stats/{rcp}/{test_stat}/*_{test_stat}*_30yr_mean.nc') # get all files
    assert len(cfls) == 50, f'Number of files does not equal 50: {len(cfls)}' # check that there is the correct number of files (50)
    
    if rcp in ['constructed_RCP26', 'constructed_RCP45']:
        # get constructed RCP warming levels data for RCPs 2.6 and 4.5
        all_wl = pd.concat([return_wl(fl) for fl in cfls], axis=1).mean(axis=1) # generate df with warming levels for all realizations, then take mean by period
        wl_string = [f'GWL:{wl:.2f}Cvs1850-1900' for wl in all_wl.values] # from all-realization mean WL, generate strings to use as dataset coordinate
        # open all data from all realizations into one dataset      
    elif rcp == 'RCP85': 
        # get RCP8.5 info from csv, not associated with nc input files
        all_wl = pd.read_csv(f'{fwipaths.working_data}GWL/warming_levels_by_period_all_RCPs.csv', index_col=0)['RCP8.5']
        wl_string = [f'GWL:{wl:.2f}Cvs1850-1900' for wl in all_wl.values] # generate strings to use as dataset coordinate
    alldat = xr.open_mfdataset(cfls, preprocess=reassign_wl, chunks={'realization':-1, 'lat':10, 'lon':10}).chunk({'realization':-1}) # chunk along realization dim of -1 will create one large chunk along dim to allow for ens percentiles (dask cannot do quantiles over multiple chunks)
    
    if 'quantile' in alldat.coords: # for MJJAS quantile metric, rename quantile dims if they exist
        alldat = alldat.rename({'quantile': 'annual_quantiles'})
    
    # get ref period data, to calculate deltas
    ref_period = alldat.sel(period='1971-2000').squeeze().drop('period')  
                
    ### Take RCP stats ###
    
    # Calculate ensemble mean and ensemble percentiles, create a new ensemble_statistic dim, then merge
    ens_percentiles = xr.merge([alldat.quantile([0.10,0.50,0.90], dim='realization', keep_attrs=True).rename({'quantile':'ensemble_statistic'}),
                                alldat.mean(dim='realization', keep_attrs=True).assign_coords({'ensemble_statistic': 'mean'}).expand_dims('ensemble_statistic')])
    ens_percentiles['ensemble_statistic'] = [f'quantile:{q}' for q in ens_percentiles.ensemble_statistic.values[:3]] + ['mean'] # relabel quantiles in ensemble_statistic dim to be more transparent
            
    # Calculate deltas from the 1971-2000 period. Then repeat the above
    alldat_deltas = alldat - ref_period
    # Calculate ensemble mean and ensemble percentiles, create a new ensemble_statistic dim, then merge
    delta_ens_percentiles = xr.merge([alldat_deltas.quantile([0.10,0.50,0.90], dim='realization', keep_attrs=True).rename({'quantile':'ensemble_statistic'}),
                                      alldat_deltas.mean(dim='realization', keep_attrs=True).assign_coords({'ensemble_statistic': 'mean'}).expand_dims('ensemble_statistic')])
    delta_ens_percentiles = delta_ens_percentiles.assign_coords({'warming_level': ("period", ens_percentiles.warming_level.values)}) # re-add WL info lost in calcs
    delta_ens_percentiles['ensemble_statistic'] = [f'quantile:{q}' for q in delta_ens_percentiles.ensemble_statistic.values[:3]] + ['mean'] # relabel quantiles in ensemble_statistic dim to be more transparent
    
    # Calculate percentage deltas from the 1971-2000 period. Then repeat the above
    percent_alldat_deltas = 100 * (alldat - ref_period) / ref_period
    # check for infinites (number/0 in the above eqn). Where infinite=True, replace with NaNs. 
    # Zero divide by zero above will return NaN. Zeros exist in the historical period when there is no fire season, or no exceedances of the set threshold
    percent_alldat_deltas = xr.where(np.isinf(percent_alldat_deltas), np.nan, percent_alldat_deltas) 
    # Calculate ensemble mean and ensemble percentiles, create a new ensemble_statistic dim, then merge
    # Since NaNs exist for these data, set skipna=False to not take ens. stats for any locations where NaNs exist in ANY ensemble member
    percent_delta_ens_percentiles = xr.merge([percent_alldat_deltas.quantile([0.10,0.50,0.90], dim='realization', skipna=False, keep_attrs=True).rename({'quantile':'ensemble_statistic'}), 
                                              percent_alldat_deltas.mean(dim='realization', skipna=False, keep_attrs=True).assign_coords({'ensemble_statistic': 'mean'}).expand_dims('ensemble_statistic')])
    percent_delta_ens_percentiles = percent_delta_ens_percentiles.assign_coords({'warming_level': ("period", ens_percentiles.warming_level.values)})  # re-add WL info lost in calcs
    percent_delta_ens_percentiles['ensemble_statistic'] = [f'quantile:{q}' for q in percent_delta_ens_percentiles.ensemble_statistic.values[:3]] + ['mean'] # relabel quantiles in ensemble_statistic dim to be more transparent
     
    ### add attrs, encoding and save ###
     
    encoding = {var: {'zlib': True, 'complevel': 4} for var in alldat.data_vars} 
    for var in ['lat','lon']:
        encoding[var] = {'dtype': 'float64', '_FillValue': None}  
        
    # update/add dataset attrs and variable attrs
    ens_percentiles = add_attrs(ens_percentiles)
    ens_percentiles = add_var_attrs(ens_percentiles, data_type='absolute', test_stat=test_stat) 
    
    delta_ens_percentiles.attrs = ens_percentiles.attrs # add universal attrs back that are lost during subtract
    delta_ens_percentiles = add_var_attrs(delta_ens_percentiles, data_type='delta', test_stat=test_stat) 
    
    percent_delta_ens_percentiles.attrs = ens_percentiles.attrs # add universal attrs back that are lost during subtract
    percent_delta_ens_percentiles = add_var_attrs(percent_delta_ens_percentiles, data_type='percent_delta', test_stat=test_stat) 
    
    # trim to Canada domain and save          
    ens_percentiles.where(final_mask==100).to_netcdf(f'{outpath}{test_stat}_{rcp}_30yr_mean_ensemble_percentiles.nc', encoding=encoding) 
    delta_ens_percentiles.where(final_mask==100).to_netcdf(f'{outpath}{test_stat}_{rcp}_30yr_mean_delta_1971_2000_ensemble_percentiles.nc', encoding=encoding)
    percent_delta_ens_percentiles.where(final_mask==100).to_netcdf(f'{outpath}{test_stat}_{rcp}_30yr_mean_percent_delta_1971_2000_ensemble_percentiles.nc', encoding=encoding)
        
    del([cfls,alldat,alldat_deltas,percent_alldat_deltas,delta_ens_percentiles,percent_delta_ens_percentiles,ens_percentiles])
    gc.collect()