from parflow.tools.io import read_pfb,write_pfb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import argparse
import os
import shutil

"""
Add 1.5 deg to the forcing and update SPFH 
"""

def temp_adjustment(og_temp,deg_increase): 
   
    """
    forcing_input:     .pfb already read in as an array, (24,nx,ny) 
    deg_increase: how many degrees to add
    
    returns: 
    new_temp:          24? by nx by ny array of adjusted temperature
    """
    # og_temp = read_pfb(forcing_input)
    new_temp = og_temp.copy()
    
    for layer in range(og_temp.shape[0]): # loop over each hour
        
        new_temp[layer] = og_temp[layer] + deg_increase
    
    
    return new_temp

def relative_humidity(T_og_array, SH_og_array, press_array): 
    """
    
    returns: 
    RH_array:          an nx by ny array of relative humidity values for each cell in domain   
    """
     
    # press_array = read_pfb(press)
    # SH_og_array = read_pfb(SH_og)
    # T_og_array = read_pfb(T_og)
 
    if np.any(press_array== 0):
        raise SystemExit('ZERO value in press_array!')
    if np.isnan(press_array).any():
        raise SystemExit('Nan in press_array')
    
    if np.any(SH_og_array== 0):
        raise SystemExit('ZERO value in SH_og_array!')
    if np.isnan(SH_og_array).any():
        raise SystemExit('Nan in SH_og_array')
        
    if np.any(T_og_array== 0):
        raise SystemExit('ZERO value in T_og_array!')
    if np.isnan(T_og_array).any():
        raise SystemExit('Nan in T_og_array')
    
    shape = T_og_array.shape # shape[0] should be 24 layers 
    
    RH_array = np.zeros((shape)) # should be (24,ny,nx)
    
    for layer in range(shape[0]):
        log_argument = (17.67*(T_og_array[layer]-273.15)) / (T_og_array[layer] - 29.65) 

        RH_array[layer] = (0.263*press_array[layer]*SH_og_array[layer]) * (np.exp(log_argument))**-1 
    
    return RH_array

def specific_humidity(RH_array,press_array,T_new_array): 
    """
    returns: 
    SH_new:   nx by ny array of adjusted specific humidity values, given new temperature values
    
    """
    # T_new_array = read_pfb(T_new)
    # press_array = read_pfb(press) 
    shape = T_new_array.shape # shape[0] should be 24 layers 
    
    
    if (RH_array.shape != press_array.shape):
        raise ValueError(f"RH shape {RH_array.shape} does not equal pressure shape {press_array.shape}")
        
    if (T_new_array.shape != press_array.shape):
        raise ValueError(f"T_new shape {T_new_array.shape} does not equal pressure shape {press_array.shape}")

    SH_new_array = np.zeros((shape)) # should be (24,ny,nx)
    
    for layer in range(shape[0]):
        log_argument = (17.67*(T_new_array[layer] - 273.15)) / (T_new_array[layer] - 29.65)
#         print(layer, "\n",log_argument)
        SH_new_array[layer] = (RH_array[layer]/(0.263*press_array[layer])) * np.exp(log_argument)
        
    if (SH_new_array.shape != press_array.shape):
        raise SystemExit(" SH_new shape ",SH_new_array.shape, " not equal to shape ", press_array.shape)
    
    return SH_new_array



def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '--og_forcing_path',
        type=str,
        required=True
    )

    
    parser.add_argument(
        '--new_forcing_path',
        type=str,
        required=True
    )

    
    parser.add_argument(
        '--deg_increase',
        type=float,
        default=1.5
    )

    
    args = parser.parse_args()

    os.makedirs(args.new_forcing_path, exist_ok=True)

    timestep = 1
    
    for day in range(365):
    
        tstep1 = str(timestep).zfill(6)
        tstep2 = str(timestep+23).zfill(6)  
            
        og_temp_file = read_pfb(os.path.join(args.og_forcing_path, f'CW3E.Temp.{tstep1}_to_{tstep2}.pfb'))
        og_press_file = read_pfb(os.path.join(args.og_forcing_path, f'CW3E.Press.{tstep1}_to_{tstep2}.pfb'))
        og_spfh_file = read_pfb(os.path.join(args.og_forcing_path, f'CW3E.SPFH.{tstep1}_to_{tstep2}.pfb'))
        
        new_temp = temp_adjustment(og_temp_file ,args.deg_increase)
    
        new_temp_file_path = os.path.join(args.new_forcing_path, f'CW3E.Temp.{tstep1}_to_{tstep2}.pfb')
        write_pfb(new_temp_file_path, new_temp, dist=False) 
        new_temp_file = read_pfb(new_temp_file_path)
        
        # calculate relative humidity
        rh_array = relative_humidity(og_temp_file, og_spfh_file, og_press_file)
    
        # adjust specific humidity 
        spfh_adjusted = specific_humidity(rh_array,og_press_file,new_temp_file)
    
        new_spfh_file_path = os.path.join(args.new_forcing_path, f'CW3E.SPFH.{tstep1}_to_{tstep2}.pfb')
        write_pfb(new_spfh_file_path, spfh_adjusted, dist=False)
    
        # copy existing forcing that isn't adjusted here over to the new forcing dir for simplicity in runsript
        other_vars = ['APCP', 'DLWR', 'DSWR', 'Press', 'UGRD', 'VGRD']
        
        for var in other_vars:
            shutil.copy2(os.path.join(args.og_forcing_path, f'CW3E.{var}.{tstep1}_to_{tstep2}.pfb'), os.path.join(args.new_forcing_path, f'CW3E.{var}.{tstep1}_to_{tstep2}.pfb'))
        
        timestep +=24
    
        print(f'done {day}')

if __name__ == "__main__":
    main()

    
    