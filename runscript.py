import os
import sys
import argparse
from parflow.tools import Run
from parflow.tools.fs import mkdir, cp, get_absolute_path, exists
from parflow.tools.settings import set_working_directory, get_working_directory
from parflow.tools.io import read_pfb,write_pfb, read_clm
import parflow.tools.hydrology as hydro
import parflow as pf
from parflow import Run
import matplotlib.patches as mpatches
import shutil
from glob import glob
import numpy as np 
import pandas as pd 
import matplotlib.pyplot as plt
import calendar
from matplotlib import colors 
import matplotlib.dates as mdates

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
        '--rzwaterstress',
        type=int,
        required=True
    )
    
    parser.add_argument(
        '--restart_from_previous',
        action = 'store_true'
    )
    
    parser.add_argument(
        '--prior_run',
        type=str
    )
    parser.add_argument(
        '--forcing_dir',
        type=str,
        required=True
    )

    parser.add_argument(
        '--input_dir',
        type=str,
        required=True
    )

    parser.add_argument(
        '--distribute_forcing',
        action = 'store_true'
    )
    
    parser.add_argument(
        '--WY',
        type=int,
        required=True
    )

    args = parser.parse_args()

    run_path = args.run_dir + args.runname 

    os.makedirs(run_path, exist_ok=True)

    set_working_directory(run_path)
    os.chdir(run_path)
    print("working dir:",get_working_directory())
    
    # ParFlow Inputs - these are located in the inputs_path
    domain_file            = 'solidfile.pfsol'  
    mannings_file          = 'mannings.pfb'
    subsurface_file        = 'pf_indicator.pfb'
    slope_x_file           = 'slope_x.pfb'
    slope_y_file           = 'slope_y.pfb'
    flow_barrier_file      = 'pf_flowbarrier.pfb'
    initial_file           = 'ss_pressure_head.pfb' # initial file from subsetting
    
    #clm inputs - subset using subsettools
    filename_drv_vegm = 'drv_vegm.dat'
    filename_drv_vegp = 'drv_vegp.dat'
    #filename_drv_clmin = f'~/EastTaylor_inputs/drv_clmin.dat'
    filename_drv_clmin_in = 'drv_clmin_newstart.dat' # change if starting from default pressure
    
    cp(args.input_dir + domain_file)
    cp(args.input_dir + mannings_file)
    cp(args.input_dir + subsurface_file)
    cp(args.input_dir + slope_x_file)
    cp(args.input_dir + slope_y_file)
    cp(args.input_dir + flow_barrier_file)
    cp(args.input_dir + initial_file)
    cp(args.input_dir + filename_drv_vegm)
    cp(args.input_dir + filename_drv_vegp)
    cp(args.input_dir + filename_drv_clmin_in, 'drv_clmin.dat')
    cp('/home/ad4430/new_runs/runscript.py')
    # Create ParFlow run object 'model'
    __file__ = '/home/ad4430/new_runs/runscript.py'
    ETW = Run(args.runname, __file__)
    ETW.FileVersion = 4


    # Timing (time units is set by units of permeability) 
    istep = 0
    
    if calendar.isleap(args.WY):
        n_hours = 8784
    else:
        n_hours = 8760
    
    ETW.TimingInfo.BaseUnit      = 1.0  
    ETW.TimingInfo.StartCount    = istep
    ETW.TimingInfo.StartTime     = istep
    ETW.TimingInfo.StopTime      = n_hours
    ETW.TimingInfo.DumpInterval  = 1.0 #-1 (-1 dumps output at every partial timestep...)
    ETW.TimeStep.Type            = 'Constant'
    ETW.TimeStep.Value           = 1.0 #0.1 #0.25 #1.0 


    # Set Processor topology 
    ETW.Process.Topology.P = 4
    ETW.Process.Topology.Q = 4
    ETW.Process.Topology.R = 1
    
    nproc = ETW.Process.Topology.P * ETW.Process.Topology.Q * ETW.Process.Topology.R


    ## restarting

    # if not restarting
    default_initial_pressure = f'{args.input_dir}ss_pressure_head.pfb'
    
    if (istep > 0) and (args.restart_from_previous == False): # starting in the middle of a run
        for i in range(0,ETW.Process.Topology.P*ETW.Process.Topology.Q):
            rst_timestamp = str(int(istep)).rjust(5, '0')
            cp(f'clm.rst.00000.{i}',f'clm.rst.{rst_timestamp}.{i}')
            print('cond 1')
        t0_istep = str(int(istep)).rjust(5, '0')
        filename_initialpressure = f'{args.runname}.out.press.{t0_istep}.pfb'
        print(filename_initialpressure)
    
    
    elif args.restart_from_previous:
    
        restart_dir = f'{args.run_dir}{args.prior_run}'
    
        # ParFlow pressure restart
        restart_pressure_file = (
            f'{restart_dir}/'
            f'{args.prior_run}.out.press.08760.pfb'
        )
    
        initial_file = (
            f'{args.prior_run}.out.press.08760.pfb'
        )
    
        destination_pressure_file = (
            f'{run_path}/{initial_file}'
        )
    
        if not os.path.isfile(restart_pressure_file):
            raise FileNotFoundError(
                f"Missing pressure restart: {restart_pressure_file}"
            )
    
        shutil.copy2(
            restart_pressure_file,
            destination_pressure_file
        )
    
        print("cond 2")
        print(
            f"Copied pressure restart: "
            f"{restart_pressure_file} -> "
            f"{destination_pressure_file}"
        )
    
        # CLM restart
        # WriteLastRST=True means final files are clm.rst.00000.*
        for i in range(
            ETW.Process.Topology.P *
            ETW.Process.Topology.Q *
            ETW.Process.Topology.R
        ):
            source_rst = (
                f'{restart_dir}/clm.rst.00000.{i}'
            )
    
            destination_rst = (
                f'{run_path}/clm.rst.00000.{i}'
            )
    
            if not os.path.isfile(source_rst):
                raise FileNotFoundError(
                    f"Missing CLM restart file: {source_rst}"
                )
    
            shutil.copy2(source_rst, destination_rst)
    
            print(
                f"Copied CLM restart: "
                f"{source_rst} -> {destination_rst}"
            )
        
    else: # not restarting
        filename_drv_clmin_in = 'drv_clmin_newstart.dat' 
        filename_initialpressure = default_initial_pressure
        print('cond 3',  filename_initialpressure)
    
    # Computational Grid 
    resolution = 1000
    
    ETW.ComputationalGrid.Lower.X = 0.0
    ETW.ComputationalGrid.Lower.Y = 0.0
    ETW.ComputationalGrid.Lower.Z = 0.0
    
    ETW.ComputationalGrid.DX = resolution
    ETW.ComputationalGrid.DY = resolution
    ETW.ComputationalGrid.DZ = 200.0
    
    ETW.ComputationalGrid.NX = int(67000/resolution)
    ETW.ComputationalGrid.NY = int(48000/resolution)
    ETW.ComputationalGrid.NZ = 10  

    # Names of the GeomInputs
    ETW.GeomInput.Names = "domaininput indi_input"
    
    # Domain Geometry Input
    ETW.GeomInput.domaininput.InputType  = 'SolidFile'
    ETW.GeomInput.domaininput.GeomNames  = 'domain'
    ETW.GeomInput.domaininput.FileName   = f'{run_path}/{domain_file}'
    
    
    # Domain Geometry
    ETW.Geom.domain.Patches = "top bottom side"
    
    # Indicator Geometry Input
    ETW.GeomInput.indi_input.InputType   = 'IndicatorField'
    ETW.GeomInput.indi_input.GeomNames   = 's1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13 g1 g2 g3 g4 g5 g6 g7 g8 b1 b2'
    ETW.Geom.indi_input.FileName         = f'{run_path}/{subsurface_file}'
    ETW.dist(f'{run_path}/{subsurface_file}')
    ETW.GeomInput.s1.Value = 1
    ETW.GeomInput.s2.Value = 2
    ETW.GeomInput.s3.Value = 3
    ETW.GeomInput.s4.Value = 4
    ETW.GeomInput.s5.Value = 5
    
    ETW.GeomInput.s6.Value = 6
    ETW.GeomInput.s7.Value = 7
    ETW.GeomInput.s8.Value = 8
    ETW.GeomInput.s9.Value = 9
    ETW.GeomInput.s10.Value = 10
    ETW.GeomInput.s11.Value = 11
    ETW.GeomInput.s12.Value = 12
    
    ETW.GeomInput.s13.Value = 13
    
    ETW.GeomInput.b1.Value = 19
    ETW.GeomInput.b2.Value = 20

    ETW.GeomInput.g1.Value = 21
    ETW.GeomInput.g2.Value = 22
    ETW.GeomInput.g3.Value = 23
    ETW.GeomInput.g4.Value = 24
    ETW.GeomInput.g5.Value = 25
    ETW.GeomInput.g6.Value = 26
    ETW.GeomInput.g7.Value = 27
    ETW.GeomInput.g8.Value = 28
    
    

    # variable dz assignments
    ETW.Solver.Nonlinear.VariableDz = True
    ETW.dzScale.GeomNames = 'domain'
    ETW.dzScale.Type = 'nzList'
    ETW.dzScale.nzListNumber = 10
    
    # 10 layers, starts at 0 from the bottom to 9 at the top
    # note this is opposite Noah/WRF
    # layers are 0.1 m, 0.3 m, 0.6 m, 1.0 m, 5.0 m, 10.0 m, 25.0 m, 50.0 m, 100.0m, 200.0 m
    # 200 m * 1.0 = 200 m
    ETW.Cell._0.dzScale.Value = 1.0
    # 200 m * .5 = 100 m 
    ETW.Cell._1.dzScale.Value = 0.5
    # 200 m * .25 = 50 m 
    ETW.Cell._2.dzScale.Value = 0.25
    # 200 m * 0.125 = 25 m 
    ETW.Cell._3.dzScale.Value = 0.125
    # 200 m * 0.05 = 10 m 
    ETW.Cell._4.dzScale.Value = 0.05
    # 200 m * .025 = 5 m 
    ETW.Cell._5.dzScale.Value = 0.025
    # 200 m * .005 = 1 m 
    ETW.Cell._6.dzScale.Value = 0.005
    # 200 m * 0.003 = 0.6 m 
    ETW.Cell._7.dzScale.Value = 0.003
    # 200 m * 0.0015 = 0.3 m 
    ETW.Cell._8.dzScale.Value = 0.0015
    # 200 m * 0.0005 = 0.1 m = 10 cm which is default top Noah layer
    ETW.Cell._9.dzScale.Value = 0.0005   
        
    # Flow Barrier defined by Shangguan Depth to Bedrock
    ETW.Solver.Nonlinear.FlowBarrierZ = True
    ETW.FBz.Type = 'PFBFile'
    ETW.Geom.domain.FBz.FileName = f'{run_path}/{flow_barrier_file}'
    ETW.dist(f'{run_path}/{flow_barrier_file}')

    # Permeability (values in m/hr)
    ETW.Geom.Perm.Names = 'domain s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13 g1 g2 g3 g4 g5 g6 g7 g8 b1 b2'
    
    ETW.Geom.domain.Perm.Type = 'Constant'
    ETW.Geom.domain.Perm.Value = 0.02
    
    ETW.Geom.s1.Perm.Type = 'Constant'
    ETW.Geom.s1.Perm.Value = 0.269022595
    
    ETW.Geom.s2.Perm.Type = 'Constant'
    ETW.Geom.s2.Perm.Value = 0.043630356
    
    ETW.Geom.s3.Perm.Type = 'Constant'
    ETW.Geom.s3.Perm.Value = 0.015841225
    
    ETW.Geom.s4.Perm.Type = 'Constant'
    ETW.Geom.s4.Perm.Value = 0.007582087
    
    ETW.Geom.s5.Perm.Type = 'Constant'
    ETW.Geom.s5.Perm.Value = 0.01818816
    
    ETW.Geom.s6.Perm.Type = 'Constant'
    ETW.Geom.s6.Perm.Value = 0.005009435
    
    ETW.Geom.s7.Perm.Type = 'Constant'
    ETW.Geom.s7.Perm.Value = 0.005492736
    
    ETW.Geom.s8.Perm.Type = 'Constant'
    ETW.Geom.s8.Perm.Value = 0.004675077
    
    ETW.Geom.s9.Perm.Type = 'Constant'
    ETW.Geom.s9.Perm.Value = 0.003386794
    
    ETW.Geom.s10.Perm.Type = 'Constant'
    ETW.Geom.s10.Perm.Value = 0.004783973
    
    ETW.Geom.s11.Perm.Type = 'Constant'
    ETW.Geom.s11.Perm.Value = 0.003979136
    
    ETW.Geom.s12.Perm.Type = 'Constant'
    ETW.Geom.s12.Perm.Value = 0.006162952
    
    ETW.Geom.s13.Perm.Type = 'Constant'
    ETW.Geom.s13.Perm.Value = 0.005009435
    
    ETW.Geom.b1.Perm.Type = 'Constant'
    ETW.Geom.b1.Perm.Value = 0.005
    
    ETW.Geom.b2.Perm.Type = 'Constant'
    ETW.Geom.b2.Perm.Value = 0.01
    
    ETW.Geom.g1.Perm.Type = 'Constant'
    ETW.Geom.g1.Perm.Value = 0.02
    
    ETW.Geom.g2.Perm.Type = 'Constant'
    ETW.Geom.g2.Perm.Value = 0.03
    
    ETW.Geom.g3.Perm.Type = 'Constant'
    ETW.Geom.g3.Perm.Value = 0.04
    
    ETW.Geom.g4.Perm.Type = 'Constant'
    ETW.Geom.g4.Perm.Value = 0.05
    
    ETW.Geom.g5.Perm.Type = 'Constant'
    ETW.Geom.g5.Perm.Value = 0.06
    
    ETW.Geom.g6.Perm.Type = 'Constant'
    ETW.Geom.g6.Perm.Value = 0.08
    
    ETW.Geom.g7.Perm.Type = 'Constant'
    ETW.Geom.g7.Perm.Value = 0.1
    
    ETW.Geom.g8.Perm.Type = 'Constant'
    ETW.Geom.g8.Perm.Value = 0.2
    
    ETW.Perm.TensorType = 'TensorByGeom'
    ETW.Geom.Perm.TensorByGeom.Names = 'domain b1 b2 g1 g2 g4 g5 g6 g7'
    
    ETW.Geom.domain.Perm.TensorValX = 1.0
    ETW.Geom.domain.Perm.TensorValY = 1.0
    ETW.Geom.domain.Perm.TensorValZ = 1.0
    
    ETW.Geom.b1.Perm.TensorValX = 1.0
    ETW.Geom.b1.Perm.TensorValY = 1.0
    ETW.Geom.b1.Perm.TensorValZ = 0.1
    
    ETW.Geom.b2.Perm.TensorValX = 1.0
    ETW.Geom.b2.Perm.TensorValY = 1.0
    ETW.Geom.b2.Perm.TensorValZ = 0.1
    
    ETW.Geom.g1.Perm.TensorValX = 1.0
    ETW.Geom.g1.Perm.TensorValY = 1.0
    ETW.Geom.g1.Perm.TensorValZ = 0.1
    
    ETW.Geom.g2.Perm.TensorValX = 1.0
    ETW.Geom.g2.Perm.TensorValY = 1.0
    ETW.Geom.g2.Perm.TensorValZ = 0.1
    
    ETW.Geom.g4.Perm.TensorValX = 1.0
    ETW.Geom.g4.Perm.TensorValY = 1.0
    ETW.Geom.g4.Perm.TensorValZ = 0.1
    
    ETW.Geom.g5.Perm.TensorValX = 1.0
    ETW.Geom.g5.Perm.TensorValY = 1.0
    ETW.Geom.g5.Perm.TensorValZ = 0.1
    
    ETW.Geom.g6.Perm.TensorValX = 1.0
    ETW.Geom.g6.Perm.TensorValY = 1.0
    ETW.Geom.g6.Perm.TensorValZ = 0.1
    
    ETW.Geom.g7.Perm.TensorValX = 1.0
    ETW.Geom.g7.Perm.TensorValY = 1.0
    ETW.Geom.g7.Perm.TensorValZ = 0.1
            
    
    # Specific Storage
    
    ETW.SpecificStorage.Type                 = 'Constant'
    ETW.SpecificStorage.GeomNames            = 'domain b1 b2'
    ETW.Geom.domain.SpecificStorage.Value    = 1.0e-4
    ETW.Geom.b1.SpecificStorage.Value        = 1.0e-5
    ETW.Geom.b2.SpecificStorage.Value        = 1.0e-5


    # Phases
    ETW.Phase.Names                  = 'water'
    ETW.Phase.water.Density.Type     = 'Constant'
    ETW.Phase.water.Density.Value    = 1.0
    ETW.Phase.water.Viscosity.Type   = 'Constant'
    ETW.Phase.water.Viscosity.Value  = 1.0


    # Contaminants
    ETW.Contaminants.Names = ''
    
    # Gravity
    ETW.Gravity = 1.0


    # Porosity
    #bedrock layers added by MP 08/13/24
    ETW.Geom.Porosity.GeomNames = 'domain s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13 g1 g2 g3 g4 g5 g6 g7 g8 b1 b2'
    
    ETW.Geom.domain.Porosity.Type = 'Constant'
    ETW.Geom.domain.Porosity.Value = 0.33
    
    ETW.Geom.s1.Porosity.Type = 'Constant'
    ETW.Geom.s1.Porosity.Value = 0.375
    
    ETW.Geom.s2.Porosity.Type = 'Constant'
    ETW.Geom.s2.Porosity.Value = 0.39
    
    ETW.Geom.s3.Porosity.Type = 'Constant'
    ETW.Geom.s3.Porosity.Value = 0.387
    
    ETW.Geom.s4.Porosity.Type = 'Constant'
    ETW.Geom.s4.Porosity.Value = 0.439
    
    ETW.Geom.s5.Porosity.Type = 'Constant'
    ETW.Geom.s5.Porosity.Value = 0.489
    
    ETW.Geom.s6.Porosity.Type = 'Constant'
    ETW.Geom.s6.Porosity.Value = 0.399
    
    ETW.Geom.s7.Porosity.Type = 'Constant'
    ETW.Geom.s7.Porosity.Value = 0.384
    
    ETW.Geom.s8.Porosity.Type = 'Constant'
    ETW.Geom.s8.Porosity.Value = 0.482
    
    ETW.Geom.s9.Porosity.Type = 'Constant'
    ETW.Geom.s9.Porosity.Value = 0.442
    
    ETW.Geom.s10.Porosity.Type = 'Constant'
    ETW.Geom.s10.Porosity.Value = 0.385
    
    ETW.Geom.s11.Porosity.Type = 'Constant'
    ETW.Geom.s11.Porosity.Value = 0.481
    
    ETW.Geom.s12.Porosity.Type = 'Constant'
    ETW.Geom.s12.Porosity.Value = 0.459
    
    ETW.Geom.s13.Porosity.Type = 'Constant'
    ETW.Geom.s13.Porosity.Value = 0.399
    
    ETW.Geom.g1.Porosity.Type = 'Constant'
    ETW.Geom.g1.Porosity.Value = 0.12
    
    ETW.Geom.g2.Porosity.Type = 'Constant'
    ETW.Geom.g2.Porosity.Value = 0.30
    
    ETW.Geom.g3.Porosity.Type = 'Constant'
    ETW.Geom.g3.Porosity.Value = 0.01
    
    ETW.Geom.g4.Porosity.Type = 'Constant'
    ETW.Geom.g4.Porosity.Value = 0.15
    
    ETW.Geom.g5.Porosity.Type = 'Constant'
    ETW.Geom.g5.Porosity.Value = 0.22
    
    ETW.Geom.g6.Porosity.Type = 'Constant'
    ETW.Geom.g6.Porosity.Value = 0.27
    
    ETW.Geom.g7.Porosity.Type = 'Constant'
    ETW.Geom.g7.Porosity.Value = 0.06
    
    ETW.Geom.g8.Porosity.Type = 'Constant'
    ETW.Geom.g8.Porosity.Value = 0.30
    
    ETW.Geom.b1.Porosity.Type = 'Constant'
    ETW.Geom.b1.Porosity.Value = 0.05
    
    ETW.Geom.b2.Porosity.Type = 'Constant'
    ETW.Geom.b2.Porosity.Value = 0.1

    ETW.Domain.GeomName = 'domain'
    
    # Mobility
    ETW.Phase.water.Mobility.Type = 'Constant'
    ETW.Phase.water.Mobility.Value = 1.0

    ETW.Wells.Names = ''

    # Relative Permeability
    ETW.Phase.RelPerm.Type = 'VanGenuchten'
    ETW.Phase.RelPerm.GeomNames = 'domain s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13'
    
    ETW.Geom.domain.RelPerm.Alpha                = 0.5
    ETW.Geom.domain.RelPerm.N                    = 2.5
    ETW.Geom.domain.RelPerm.NumSamplePoints      = 20000
    ETW.Geom.domain.RelPerm.MinPressureHead      = -500
    ETW.Geom.domain.RelPerm.InterpolationMethod  = 'Linear'
    
    ETW.Geom.s1.RelPerm.Alpha                    = 3.548
    ETW.Geom.s1.RelPerm.N                        = 4.162
    ETW.Geom.s1.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s1.RelPerm.MinPressureHead          = -300
    ETW.Geom.s1.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s2.RelPerm.Alpha                    = 3.467
    ETW.Geom.s2.RelPerm.N                        = 2.738
    ETW.Geom.s2.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s2.RelPerm.MinPressureHead          = -300
    ETW.Geom.s2.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s3.RelPerm.Alpha                    = 2.692
    ETW.Geom.s3.RelPerm.N                        = 2.445
    ETW.Geom.s3.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s3.RelPerm.MinPressureHead          = -300
    ETW.Geom.s3.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s4.RelPerm.Alpha                    = 0.501
    ETW.Geom.s4.RelPerm.N                        = 2.659
    ETW.Geom.s4.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s4.RelPerm.MinPressureHead          = -300
    ETW.Geom.s4.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s5.RelPerm.Alpha                    = 0.661
    ETW.Geom.s5.RelPerm.N                        = 2.659
    ETW.Geom.s5.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s5.RelPerm.MinPressureHead          = -300
    ETW.Geom.s5.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s6.RelPerm.Alpha                    = 1.122
    ETW.Geom.s6.RelPerm.N                        = 2.479
    ETW.Geom.s6.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s6.RelPerm.MinPressureHead          = -300
    ETW.Geom.s6.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s7.RelPerm.Alpha                    = 2.089
    ETW.Geom.s7.RelPerm.N                        = 2.318
    ETW.Geom.s7.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s7.RelPerm.MinPressureHead          = -300
    ETW.Geom.s7.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s8.RelPerm.Alpha                    = 0.832
    ETW.Geom.s8.RelPerm.N                        = 2.514
    ETW.Geom.s8.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s8.RelPerm.MinPressureHead          = -300
    ETW.Geom.s8.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s9.RelPerm.Alpha                    = 1.585
    ETW.Geom.s9.RelPerm.N                        = 2.413
    ETW.Geom.s9.RelPerm.NumSamplePoints          = 20000
    ETW.Geom.s9.RelPerm.MinPressureHead          = -300
    ETW.Geom.s9.RelPerm.InterpolationMethod      = 'Linear'
    
    ETW.Geom.s10.RelPerm.Alpha                   = 3.311
    ETW.Geom.s10.RelPerm.N                       = 2.202
    ETW.Geom.s10.RelPerm.NumSamplePoints         = 20000
    ETW.Geom.s10.RelPerm.MinPressureHead         = -300
    ETW.Geom.s10.RelPerm.InterpolationMethod     = 'Linear'
    
    ETW.Geom.s11.RelPerm.Alpha                   = 1.622
    ETW.Geom.s11.RelPerm.N                       = 2.318
    ETW.Geom.s11.RelPerm.NumSamplePoints         = 20000
    ETW.Geom.s11.RelPerm.MinPressureHead         = -300
    ETW.Geom.s11.RelPerm.InterpolationMethod     = 'Linear'
    
    ETW.Geom.s12.RelPerm.Alpha                   = 1.514
    ETW.Geom.s12.RelPerm.N                       = 2.259
    ETW.Geom.s12.RelPerm.NumSamplePoints         = 20000
    ETW.Geom.s12.RelPerm.MinPressureHead         = -300
    ETW.Geom.s12.RelPerm.InterpolationMethod     = 'Linear'
    
    ETW.Geom.s13.RelPerm.Alpha                   = 1.122
    ETW.Geom.s13.RelPerm.N                       = 2.479
    ETW.Geom.s13.RelPerm.NumSamplePoints         = 20000
    ETW.Geom.s13.RelPerm.MinPressureHead         = -300
    ETW.Geom.s13.RelPerm.InterpolationMethod     = 'Linear'
    
    # Saturation
    
    ETW.Phase.Saturation.Type = 'VanGenuchten'
    ETW.Phase.Saturation.GeomNames = 'domain s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13'
    
    ETW.Geom.domain.Saturation.Alpha = 0.5
    ETW.Geom.domain.Saturation.N = 2.5
    ETW.Geom.domain.Saturation.SRes = 0.00001
    ETW.Geom.domain.Saturation.SSat = 1.0
    
    ETW.Geom.s1.Saturation.Alpha = 3.548
    ETW.Geom.s1.Saturation.N = 4.162
    ETW.Geom.s1.Saturation.SRes = 0.0001
    ETW.Geom.s1.Saturation.SSat = 1.0
    
    ETW.Geom.s2.Saturation.Alpha = 3.467
    ETW.Geom.s2.Saturation.N = 2.738
    ETW.Geom.s2.Saturation.SRes = 0.0001
    ETW.Geom.s2.Saturation.SSat = 1.0
    
    ETW.Geom.s3.Saturation.Alpha = 2.692
    ETW.Geom.s3.Saturation.N = 2.445
    ETW.Geom.s3.Saturation.SRes = 0.0001
    ETW.Geom.s3.Saturation.SSat = 1.0
    
    ETW.Geom.s4.Saturation.Alpha = 0.501
    ETW.Geom.s4.Saturation.N = 2.659
    ETW.Geom.s4.Saturation.SRes = 0.0001
    ETW.Geom.s4.Saturation.SSat = 1.0
    
    ETW.Geom.s5.Saturation.Alpha = 0.661
    ETW.Geom.s5.Saturation.N = 2.659
    ETW.Geom.s5.Saturation.SRes = 0.0001
    ETW.Geom.s5.Saturation.SSat = 1.0
    
    ETW.Geom.s6.Saturation.Alpha = 1.122
    ETW.Geom.s6.Saturation.N = 2.479
    ETW.Geom.s6.Saturation.SRes = 0.0001
    ETW.Geom.s6.Saturation.SSat = 1.0
    
    ETW.Geom.s7.Saturation.Alpha = 2.089
    ETW.Geom.s7.Saturation.N = 2.318
    ETW.Geom.s7.Saturation.SRes = 0.0001
    ETW.Geom.s7.Saturation.SSat = 1.0
    
    ETW.Geom.s8.Saturation.Alpha = 0.832
    ETW.Geom.s8.Saturation.N = 2.514
    ETW.Geom.s8.Saturation.SRes = 0.0001
    ETW.Geom.s8.Saturation.SSat = 1.0
    
    ETW.Geom.s9.Saturation.Alpha = 1.585
    ETW.Geom.s9.Saturation.N = 2.413
    ETW.Geom.s9.Saturation.SRes = 0.0001
    ETW.Geom.s9.Saturation.SSat = 1.0
    
    ETW.Geom.s10.Saturation.Alpha = 3.311
    ETW.Geom.s10.Saturation.N = 2.202
    ETW.Geom.s10.Saturation.SRes = 0.0001
    ETW.Geom.s10.Saturation.SSat = 1.0
    
    ETW.Geom.s11.Saturation.Alpha = 1.622
    ETW.Geom.s11.Saturation.N = 2.318
    ETW.Geom.s11.Saturation.SRes = 0.0001
    ETW.Geom.s11.Saturation.SSat = 1.0
    
    ETW.Geom.s12.Saturation.Alpha = 1.514
    ETW.Geom.s12.Saturation.N = 2.259
    ETW.Geom.s12.Saturation.SRes = 0.0001
    ETW.Geom.s12.Saturation.SSat = 1.0
    
    ETW.Geom.s13.Saturation.Alpha = 1.122
    ETW.Geom.s13.Saturation.N = 2.479
    ETW.Geom.s13.Saturation.SRes = 0.0001
    ETW.Geom.s13.Saturation.SSat = 1.0    
        

    # Time Cycles
    ETW.Cycle.Names                      = 'constant'
    ETW.Cycle.constant.Names             = 'alltime'
    ETW.Cycle.constant.alltime.Length    = 10000000
    ETW.Cycle.constant.Repeat            = -1        
        
    # Boundary Conditions
    ETW.BCPressure.PatchNames = ETW.Geom.domain.Patches
    
    ETW.Patch.side.BCPressure.Type = 'FluxConst'
    ETW.Patch.side.BCPressure.Cycle = 'constant'
    ETW.Patch.side.BCPressure.alltime.Value = 0.0
    
    ETW.Patch.bottom.BCPressure.Type = 'FluxConst'
    ETW.Patch.bottom.BCPressure.Cycle = 'constant'
    ETW.Patch.bottom.BCPressure.alltime.Value = 0.0
    
    ETW.Patch.top.BCPressure.Type = 'OverlandKinematic'
    ETW.Patch.top.BCPressure.Cycle = 'constant'
    ETW.Patch.top.BCPressure.alltime.Value = 0            


    # Topo slopes in x-direction
    ETW.TopoSlopesX.Type = 'PFBFile'
    ETW.TopoSlopesX.GeomNames = 'domain'
    ETW.TopoSlopesX.FileName = f'{run_path}/{slope_x_file}'
    ETW.dist(f'{run_path}/{slope_x_file}')
    
    # Topo slopes in y-direction
    ETW.TopoSlopesY.Type = 'PFBFile'
    ETW.TopoSlopesY.GeomNames = 'domain'
    ETW.TopoSlopesY.FileName = f'{run_path}/{slope_y_file}'
    ETW.dist(f'{run_path}/{slope_y_file}')

    # Initial conditions: water pressure
    ETW.ICPressure.Type = 'HydroStaticPatch'
    ETW.ICPressure.Type = 'PFBFile'
    ETW.ICPressure.GeomNames = 'domain'
    ETW.Geom.domain.ICPressure.RefPatch = 'bottom'
    ETW.Geom.domain.ICPressure.FileName = f'{run_path}/{initial_file}'
    ETW.dist(f'{run_path}/{initial_file}')
    # ETW.Geom.domain.ICPressure.RefGeom = 'domain'
    # ETW.Geom.domain.ICPressure.Value = 372.
        
    # Phase sources:
    ETW.PhaseSources.water.Type = 'Constant'
    ETW.PhaseSources.water.GeomNames = 'domain'
    ETW.PhaseSources.water.Geom.domain.Value = 0.0   

    # Mannings coefficient
    ETW.Mannings.Type = 'PFBFile'
    ETW.Mannings.FileName = f'{run_path}/{mannings_file}'
    ETW.dist(f'{run_path}/{mannings_file}')

    # Exact solution specification for error calculations
    ETW.KnownSolution = 'NoKnownSolution'

    
    # Set LSM parameters
    ETW.Solver.LSM                   = 'CLM'
    ETW.Solver.CLM.CLMFileDir        = '.'
    ETW.Solver.CLM.Print1dOut        = False
    ETW.Solver.CLM.CLMDumpInterval   = 1
    
    ETW.Solver.CLM.MetForcing        = '3D'
    ETW.Solver.CLM.MetFileName       = 'CW3E'
    ETW.Solver.CLM.MetFilePath       = args.forcing_dir 
    ETW.Solver.CLM.MetFileNT         = 24
    ETW.Solver.CLM.IstepStart        = istep + 1 # changed from clmstep, matches elena's
    
    ETW.Solver.CLM.EvapBeta          = 'Linear'
    ETW.Solver.CLM.VegWaterStress    = 'Saturation'
    ETW.Solver.CLM.ResSat            = 0.2
    ETW.Solver.CLM.WiltingPoint      = 0.2
    ETW.Solver.CLM.FieldCapacity     = 1.00
    ETW.Solver.CLM.IrrigationType    = 'none'
    
    ETW.Solver.CLM.RootZoneNZ        = 5
    ETW.Solver.CLM.SoiLayer          = 4
    ETW.Solver.CLM.ReuseCount        = 1 #10 #4 #1
    ETW.Solver.CLM.WriteLogs         = False
    ETW.Solver.CLM.WriteLastRST      = True
    ETW.Solver.CLM.DailyRST          = True
    ETW.Solver.CLM.SingleFile        = True

    ETW.Solver.CLM.RZWaterStress     = args.rzwaterstress


    # Set solver parameters
    ETW.Solver = 'Richards'
    ETW.Solver.MaxIter = 250000
    #ETW.Solver.Drop = 1E-30
    #ETW.Solver.AbsTol = 1E-9
    ETW.Solver.MaxConvergenceFailures = 5
    ETW.Solver.Nonlinear.MaxIter = 250
    ETW.Solver.Nonlinear.ResidualTol = 1e-5
    
    ETW.Solver.OverlandDiffusive.Epsilon = 0.1
    ETW.Solver.TerrainFollowingGrid = True
    ETW.Solver.TerrainFollowingGrid.SlopeUpwindFormulation = 'Upwind'
    
    ETW.Solver.WriteCLMBinary = False
    ETW.Solver.PrintCLM = True
    ETW.Solver.EvapTransFile = False
    ETW.Solver.BinaryOutDir = False
    
    ETW.Solver.PrintTop = True
    ETW.Solver.Nonlinear.EtaChoice = 'EtaConstant'
    ETW.Solver.Nonlinear.EtaValue = 0.01
    ETW.Solver.Nonlinear.UseJacobian = True
    ETW.Solver.Nonlinear.DerivativeEpsilon = 1e-16
    ETW.Solver.Nonlinear.StepTol = 1e-15
    ETW.Solver.Nonlinear.Globalization = 'LineSearch'
    
    ETW.Solver.Linear.KrylovDimension = 500
    ETW.Solver.Linear.MaxRestarts = 8
    ETW.Solver.Linear.Preconditioner = 'PFMG'
    ETW.Solver.Linear.Preconditioner.PCMatrixType = 'PFSymmetric'
    #ETW.Solver.Linear.Preconditioner.PFMG.NumPreRelax = 3
    #ETW.Solver.Linear.Preconditioner.PFMG.NumPostRelax = 2
    
    ETW.Solver.PrintSubsurfData = True
    ETW.Solver.PrintMask = True
    ETW.Solver.PrintSaturation = True
    ETW.Solver.PrintPressure = True
    ETW.Solver.PrintSlopes = True
    ETW.Solver.PrintMannings = True
    ETW.Solver.PrintEvapTrans = True
    ETW.Solver.PrintVelocities = False
    
    # surface pressure test, new solver settings
    ETW.Solver.ResetSurfacePressure = True
    ETW.Solver.ResetSurfacePressure.ThresholdPressure = 20.
    ETW.Solver.ResetSurfacePressure.ResetPressure  =  -0.00001
    
    # surface flow predictor feature, new solver settings 2/24/23
    ETW.Solver.SurfacePredictor = True 
    ETW.Solver.SurfacePredictor.PrintValues = True 
    ETW.Solver.SurfacePredictor.PressureValue = 0.00001

    ETW.Solver.WriteSiloSpecificStorage = False
    ETW.Solver.WriteSiloMannings = False
    ETW.Solver.WriteSiloMask = False
    ETW.Solver.WriteSiloSlopes = False
    ETW.Solver.WriteSiloSubsurfData = False
    ETW.Solver.WriteSiloPressure = False
    ETW.Solver.WriteSiloSaturation = False
    ETW.Solver.WriteSiloEvapTrans = False
    ETW.Solver.WriteSiloEvapTransSum = False
    ETW.Solver.WriteSiloOverlandSum = False
    ETW.Solver.WriteSiloCLM = False

    # Distribute Forcing
    # copy and distribute all year of forcing, regardless of no_days
    if args.distribute_forcing:
        for filename_forcing in os.listdir(args.forcing_dir):
            if filename_forcing[-3:]=='pfb':
                ETW.dist(f'{args.forcing_dir}/{filename_forcing}')


    ETW.run(working_directory=run_path)
    print("ParFlow run complete")

if __name__ == "__main__":
    main()