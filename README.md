# Code and model I/O for "Modeled reconfiguration of root water uptake amplifies warming-induced subsurface storage depletion in a high elevation catchment"

### pfclm_inputs: Scripts and files for running PF-CLM over the East Taylor
adjust_forcing.py: Increasing temperature by 1.5 degrees Celsius and adjusting specific humidity accordingly using the Magnus-Tetens equation for saturation vapor pressure

subset_pf_inputs.ipynb: Subsetting necessary PF-CLM inputs for the East Taylor over the CONUS2 grid.

inputs/*: PF-CLM inputs for the East Taylor Watershed gathered using subset_pf_inputs.ipynb. Note that the CW3E forcing is not included in this repository due to size, but can be gathered by replicating the st.subset_forcing codeblock in the above notebook.

### runscript.py : script used to run PF-CLM 
Model spinup, baseline, and warming runs were executed with this script by supplying arguments in a .txt file, and executing with bash.

### pfclm_outputs/*: Outputs from each PF-CLM run analyzed in this study. 
Because 4D numpy arrays for subsurface storage and evaptrans PF-CLM output (which gives ET flux per subsurface layer) exceeded the 2.0 GB file limit, numpy files that include information for these variables over the July-September period analyzed in the study are included instead. All additional numpy arrays provide hourly data for the entire water year considered. 

save_pf_output.py: Script for saving out .npy files from PF-CLM runs.

### analysis/* scripts used to produce figures / analyses
main_figures.ipynb: creation of figures for the main text of the paper.

##### SI analyses:
assess_spinup.ipynb: assessing normalized storage change over each run of spinup, and residual storage change from the final cycle

model_validation.ipynb: comparison of PF-CLM output against data from an Eddy Covariance Tower. This in-situ data can be found at https://doi.org/10.15485/3004241

lateral_flow_analysis.ipynb: calculating the effects of lateral flow on subsurface storage during the study period 

overland_flow.ipynb: assessing the effect of warming and water uptake formulation on basin outflow

snowpack_response.ipynb: determining the effect of warming on peak SWE, snow free day, and start of summer subsurface storage
