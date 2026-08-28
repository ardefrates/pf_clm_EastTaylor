import os
import sys
import numpy as np
from datetime import datetime
import argparse
from glob import glob
import parflow as pf
from parflow.tools import Run
from parflow.tools.fs import mkdir, cp, get_absolute_path, exists
from parflow.tools.settings import set_working_directory
from parflow.tools.io import read_pfb,write_pfb, read_clm
import parflow.tools.hydrology as hydro
import matplotlib.pyplot as plt
from matplotlib import colors 
import calendar

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--runname',
        type=str,
        required=True
    )
    
    parser.add_argument(
        '--run_dir',
        type=str,
        required=True
    )
    
    parser.add_argument(
        '--forcing_dir',
        type=str,
        required=True
    )
    
    parser.add_argument(
        '--WY',
        type=int,
        required=True
    )
    
    parser.add_argument(
        '--out_path',
        type=str,
        required=True
    )
    
    args = parser.parse_args()

    os.makedirs(args.out_path, exist_ok=True)
    
    run_path = os.path.join(args.run_dir, args.runname)

    run = Run.from_definition(f'{run_path}/{args.runname}.pfidb')

    run.Solver.CLM.MetFilePath = args.forcing_dir
    
    data = run.data_accessor # creating data accessor object 
    dx = data.dx
    dy = data.dy
    dz = data.dz
    nz,ny,nx = data.shape
    
    porosity= data.computed_porosity
    specific_storage = data.specific_storage
    
    mask = data.mask
    mask[mask>0]=1 # PF has big # instead of 1 so change to 1 bc more manageable
    surf_mask = mask[-1,:,:] # last element of first axis (always be surface no matter what)
    nanmask=mask.copy()
    nanmask[nanmask == 0] = 'NaN'
    nanmask[nanmask > 0] = 1
       
    
    if run.Mannings.Type == 'PFBFile':
        mannings = np.squeeze(read_pfb(f'{run.Mannings.FileName}'))
    elif run.Mannings.Type == 'Constant':
        mannings = run.Mannings.Geom.domain.Value
    slopex = np.squeeze(data.slope_x)
    slopey = np.squeeze(data.slope_y)
    
    # for converting from LE to ET
    rho_w = 1000 # kg/m3
    hvap   = 2.5104e06
    
    # save out raw infil, ET, tran, evaptrans, sub storage, swe 
    year = args.WY
    if calendar.isleap(year) == False:
    
        num_tsteps = 8760+1
    else: 
        num_tsteps = 8784+1

    infil = np.zeros((num_tsteps, ny, nx))
    et = np.zeros((num_tsteps, ny, nx))
    tran = np.zeros((num_tsteps, ny, nx))
    evaptrans = np.zeros((num_tsteps, nz, ny, nx))
    sub_storage = np.zeros((num_tsteps, nz, ny, nx))
    swe = np.zeros((num_tsteps, ny, nx))
    wtd = np.zeros((num_tsteps, ny, nx))
    surf_storage = np.zeros((num_tsteps, ny, nx))

    
    # for subsurface storage calc
    press_files = sorted(glob(f'{run_path}/{args.runname}*out.press*.pfb'))
    pressure_arrays = pf.read_pfb_sequence(press_files) * nanmask
    satur_files = sorted(glob(f'{run_path}/{args.runname}*out.satur*.pfb'))
    saturation_arrays = pf.read_pfb_sequence(satur_files) * nanmask
    
    for t in range(0,num_tsteps):
        print(f'timestep {t}')
        
        data.time = t
        sub_storage[t, :,:,:] = hydro.calculate_subsurface_storage(porosity, pressure_arrays[t,:,:,:], saturation_arrays[t,:,:,:], specific_storage, dx, dy, dz, mask = nanmask)
        surf_storage[t, :,:] = hydro.calculate_surface_storage(pressure_arrays[t,:,:,:], dx, dy, mask = nanmask)

        if t > 0: 
            data.forcing_time = t-1        

            infil[t, :, :] = data.clm_output('qflx_infl')*3600 #mm/hr
            et[t, :, :] = data.clm_output('eflx_lh_tot') * (1 / rho_w) * (1 / hvap)*3600*1000 # mm/hr
            tran[t, :, :] = data.clm_output('qflx_tran_veg') *3600 # mm/hr
            swe[t, :, :]  = data.clm_output('swe_out')
            evaptrans[t,:,:,:] = read_pfb(os.path.join(run_path, f"{args.runname}.out.evaptrans.{t:05d}.pfb"))
            
            wtd[t, :, :] = data.wtd
            
    np.save(os.path.join(args.out_path, 'infil.npy'), infil)
    np.save(os.path.join(args.out_path, 'et.npy'), et)
    np.save(os.path.join(args.out_path, 'transpiration.npy'), tran)
    np.save(os.path.join(args.out_path, 'swe.npy'), swe)
    np.save(os.path.join(args.out_path, 'sub_storage.npy'), sub_storage)
    np.save(os.path.join(args.out_path, 'evaptrans.npy'), evaptrans)
    np.save(os.path.join(args.out_path, 'wtd.npy'), wtd)
    np.save(os.path.join(args.out_path, 'surf_storage.npy'), surf_storage)


if __name__ == "__main__":
    main()



