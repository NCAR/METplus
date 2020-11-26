import sys
import os
import numpy as np
import netCDF4
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
    os.pardir)))
sys.path.insert(0, "/glade/u/home/kalb/UIUC/METplotpy/metplotpy/blocking_s2s")
sys.path.insert(0, "/glade/u/home/kalb/UIUC/METplotpy_feature_33/metplotpy/blocking_s2s")
from Blocking import BlockingCalculation
from metplus.util import config_metplus, get_start_end_interval_times, get_lead_sequence
from metplus.util import get_skip_times, skip_time, is_loop_by_init, ti_calculate, do_string_sub
from ush.master_metplus import get_config_inputs_from_command_line
from metplus.wrappers import PCPCombineWrapper
from metplus.wrappers import RegridDataPlaneWrapper
import plot_blocking as pb
from CBL_plot import create_cbl_plot

def find_input_files(inconfig, use_init, intemplate):
    loop_time, end_time, time_interval = get_start_end_interval_times(inconfig)
    skip_times = get_skip_times(inconfig)

    start_mth = loop_time.strftime('%m')
    template = inconfig.getraw('config',intemplate)

    file_list = []
    yr_list = []
    if use_init:
        timname = 'init'
    else:
        timname = 'valid'
    input_dict = {}
    input_dict['loop_by'] = timname
    pmth = start_mth
    while loop_time <= end_time:
        lead_seq = get_lead_sequence(inconfig)
        for ls in lead_seq:
            new_time = loop_time + ls
            input_dict[timname] = loop_time
            input_dict['lead'] = ls

            outtimestuff = ti_calculate(input_dict)
            cmth = outtimestuff['valid'].strftime('%m')
            filepath = do_string_sub(template, **outtimestuff)
            if skip_time(outtimestuff, skip_times):
                continue
            if os.path.exists(filepath):
                file_list.append(filepath)
            else:
                file_list.append('')

            if (int(cmth) == int(start_mth)) and (int(pmth) != int(start_mth)):
                yr_list.append(int(outtimestuff['valid'].strftime('%Y')))
            pmth = cmth

        loop_time += time_interval
        
    yr_list.append(int(outtimestuff['valid'].strftime('%Y')))

    return file_list, yr_list


def main():

    all_steps = ["REGRID","TIMEAVE","RUNMEAN","ANOMALY","CBL","PLOTCBL","IBL","PLOTIBL","GIBL","CALCBLOCKS","PLOTBLOCKS"]

    config_list = get_config_inputs_from_command_line()


    # If the user has defined the steps they want to run
    # grab the command line parameter 
    steps_config_part_fcst = [s for s in config_list if "FCST_STEPS" in s]
    steps_list_fcst = []

    steps_config_part_obs = [s for s in config_list if "OBS_STEPS" in s]
    steps_list_obs = []

    # Setup the Steps
    if steps_config_part_fcst:
        steps_param_fcst = steps_config_part_fcst[0].split("=")[1]
        steps_list_fcst = steps_param_fcst.split("+")
        config_list.remove(steps_config_part_fcst[0])
    if steps_config_part_obs:
        steps_param_obs = steps_config_part_obs[0].split("=")[1]
        steps_list_obs = steps_param_obs.split("+")
        config_list.remove(steps_config_part_obs[0])

    config = config_metplus.setup(config_list)
    if not steps_config_part_fcst:
        steps_param_fcst = config.getstr('config','FCST_STEPS','')
        steps_list_fcst = steps_param_fcst.split("+")
    if not steps_config_part_obs:
        steps_param_obs = config.getstr('config','OBS_STEPS','')
        steps_list_obs = steps_param_obs.split("+")

    if not steps_list_obs and not steps_list_fcst:
        print('No processing steps requested for either the model or observations,')
        print('no data will be processed')


    ######################################################################
    # Pre-Process Data:
    ######################################################################
    # Regrid
    if ("REGRID" in steps_list_obs):
        print('Regridding Observations')
        regrid_config = config_metplus.replace_config_from_section(config, 'regrid_obs')
        RegridDataPlaneWrapper(regrid_config).run_all_times()

    if ("REGRID" in steps_list_fcst):
       print('Regridding Model')
       regrid_config = config_metplus.replace_config_from_section(config, 'regrid_fcst')
       RegridDataPlaneWrapper(regrid_config).run_all_times()

    #Compute Daily Average
    if ("TIMEAVE" in steps_list_obs):
        print('Computing Daily Averages')
        daily_config = config_metplus.replace_config_from_section(config, 'daily_mean_obs')
        PCPCombineWrapper(daily_config).run_all_times()

    if ("TIMEAVE" in steps_list_fcst):
        print('Computing Daily Averages')
        daily_config = config_metplus.replace_config_from_section(config, 'daily_mean_fcst')
        PCPCombineWrapper(daily_config).run_all_times()

    #Take a running mean
    if ("RUNMEAN" in steps_list_obs):
        print('Computing Obs Running means')
        rmean_config = config_metplus.replace_config_from_section(config, 'running_mean_obs')
        PCPCombineWrapper(rmean_config).run_all_times()

    if ("RUNMEAN" in steps_list_fcst):
        print('Computing Model Running means')
        rmean_config = config_metplus.replace_config_from_section(config, 'running_mean_fcst')
        PCPCombineWrapper(rmean_config).run_all_times()

    #Compute anomaly
    if ("ANOMALY" in steps_list_obs):
        print('Computing Obs Anomalies')
        anomaly_config = config_metplus.replace_config_from_section(config, 'anomaly_obs')
        PCPCombineWrapper(anomaly_config).run_all_times()

    if ("ANOMALY" in steps_list_fcst):
        print('Computing Model Anomalies')
        anomaly_config = config_metplus.replace_config_from_section(config, 'anomaly_fcst')
        PCPCombineWrapper(anomaly_config).run_all_times()


    ######################################################################
    # Blocking Calculation and Plotting
    ######################################################################
    # Set up the data
    steps_fcst = BlockingCalculation(config,'FCST')
    steps_obs = BlockingCalculation(config,'OBS')

    # Check to see if CBL's are used from an obs climatology
    use_cbl_obs = config.getbool('Blocking','USE_CBL_OBS',False)

    # Calculate Central Blocking Latitude
    cbl_config = config_metplus.replace_config_from_section(config,'Blocking')
    cbl_config_init = config.find_section('Blocking','CBL_INIT_BEG')
    cbl_config_valid = config.find_section('Blocking','CBL_VALID_BEG')
    use_init =  is_loop_by_init(cbl_config)
    if use_init and (cbl_config_init is not None):
        config.set('Blocking','INIT_BEG',config.getstr('Blocking','CBL_INIT_BEG'))
        config.set('Blocking','INIT_END',config.getstr('Blocking','CBL_INIT_END'))
        cbl_config = config_metplus.replace_config_from_section(config, 'Blocking')
    elif cbl_config_valid is not None:
        config.set('Blocking','VALID_BEG',config.getstr('Blocking','CBL_VALID_BEG'))
        config.set('Blocking','VALID_END',config.getstr('Blocking','CBL_VALID_END'))
        cbl_config = config_metplus.replace_config_from_section(config, 'Blocking')

    if ("CBL" in steps_list_obs):
        print('Computing Obs CBLs')
        obs_infiles, yr_obs = find_input_files(cbl_config, use_init, 'OBS_BLOCKING_ANOMALY_TEMPLATE')
        cbls_obs,lats_obs,lons_obs,yr_obs,mhweight_obs = steps_obs.run_CBL(obs_infiles,yr_obs)

    if ("CBL" in steps_list_fcst):
        # Add in step to use obs for CBLS
        print('Computing Forecast CBLs')
        fcst_infiles,yr_fcst = find_input_files(cbl_config, use_init, 'FCST_BLOCKING_ANOMALY_TEMPLATE')
        cbls_fcst,lats_fcst,lons_fcst,yr_fcst,mhweight_fcst = steps_fcst.run_CBL(fcst_infiles,yr_fcst)
    elif use_cbl_obs:
        cbls_fcst = cbls_obs
        lats_fcst = lats_obs
        lons_fcst = lons_obs
        yr_fcst = yr_obs
        mhweight_fcst = mhweight_obs

    #Plot Central Blocking Latitude
    if ("PLOTCBL" in steps_list_obs):
        cbl_plot_mthstr = config.getstr('Blocking','OBS_CBL_PLOT_MTHSTR')
        cbl_plot_outname = config.getstr('Blocking','OBS_CBL_PLOT_OUTPUT_NAME')
        create_cbl_plot(lons_obs, lats_obs, cbls_obs, mhweight_obs, cbl_plot_mthstr, cbl_plot_outname, do_averaging=True)
    if ("PLOTCBL" in steps_list_fcst):
        cbl_plot_mthstr = config.getstr('Blocking','FCST_CBL_PLOT_MTHSTR')
        cbl_plot_outname = config.getstr('Blocking','FCST_CBL_PLOT_OUTPUT_NAME')
        create_cbl_plot(lons_fcst, lats_fcst, cbls_fcst, mhweight_fcst, cbl_plot_mthstr, cbl_plot_outname, 
            do_averaging=True)


    # Run IBL
    ibl_config = config_metplus.replace_config_from_section(config,'Blocking')
    use_init =  is_loop_by_init(ibl_config)
    if ("IBL" in steps_list_obs) and not ("IBL" in steps_list_fcst):
        print('Computing Obs IBLs')
        obs_infiles, yr_obs = find_input_files(ibl_config, use_init, 'OBS_BLOCKING_TEMPLATE') 
        ibls_obs = steps_obs.run_Calc_IBL(cbls_obs,obs_infiles,yr_obs)
        daynum_obs = np.arange(0,len(ibls_obs[0,:,0]),1)
    elif ("IBL" in steps_list_fcst) and not ("IBL" in steps_list_obs):
        print('Computing Forecast IBLs')
        fcst_infiles, yr_fcst = find_input_files(ibl_config, use_init, 'FCST_BLOCKING_TEMPLATE')
        ibls_fcst = steps_fcst.run_Calc_IBL(cbls_fcst,fcst_infiles,yr_fcst)
        daynum_fcst = np.arange(0,len(ibls_fcst[0,:,0]),1)
    elif ("IBL" in steps_list_obs) and ("IBL" in steps_list_fcst):
        ## FIX THIS LINE obs_infiles, yr_obs = find_infiles(ibl_config, use_init, 'OBS')
        ibls_obs = steps_obs.run_Calc_IBL(cbls_obs,obs_infiles,yr_obs)
        daynum_obs = np.arange(0,len(ibls_obs[0,:,0]),1)
        ibls_fcst = steps_fcst.run_Calc_IBL(cbls_fcst,fcst_infiles,yr_fcst)
        daynum_fcst = np.arange(0,len(ibls_fcst[0,:,0]),1)

    # Plot IBLS
    if("PLOTIBL" in steps_list_obs) and not ("PLOTIBL" in steps_list_fcst):
        ibl_plot_title = config.getstr('Blocking','OBS_IBL_PLOT_TITLE','IBL Frequency')
        ibl_plot_outname = config.getstr('Blocking','OBS_IBL_PLOT_OUTPUT_NAME','')
        ibl_plot_label1 = config.getstr('Blocking','IBL_PLOT_OBS_LABEL','')
        pb.plot_ibls(ibls_obs,lons_obs,ibl_plot_title,ibl_plot_outname,label1=ibl_plot_label1)
    elif ("PLOTIBL" in steps_list_fcst) and not ("PLOTIBL" in steps_list_obs):
        ibl_plot_title = config.getstr('Blocking','FCST_IBL_PLOT_TITLE','IBL Frequency')
        ibl_plot_outname = config.getstr('Blocking','FCST_IBL_PLOT_OUTPUT_NAME')
        ibl_plot_label1 = config.getstr('Blocking','IBL_PLOT_FCST_LABEL',None)
        pb.plot_ibls(ibls_fcst,lons_fcst,ibl_plot_title,ibl_plot_outname,label1=ibl_plot_label1)
    elif ("PLOTIBL" in steps_list_obs) and ("PLOTIBL" in steps_list_fcst):
        ibl_plot_title = config.getstr('Blocking','IBL_PLOT_TITLE')
        ibl_plot_outname = config.getstr('Blocking','IBL_PLOT_OUTPUT_NAME')
        #Check to see if there are plot legend labels
        ibl_plot_label1 = config.getstr('Blocking','IBL_PLOT_OBS_LABEL','Observation')
        ibl_plot_label2 = config.getstr('Blocking','IBL_PLOT_FCST_LABEL','Forecast')
        pb.plot_ibls(ibls_obs,lons_obs,ibl_plot_title,ibl_plot_outname,data2=ibls_fcst,lon2=lons_fcst,
            label1=ibl_plot_label1,label2=ibl_plot_label2)


    # Run GIBL
    if ("GIBL" in steps_list_obs):
        print('Computing GIBLs')
        gibls_obs = steps_obs.run_Calc_GIBL(ibls_obs,lons_obs)

    if ("GIBL" in steps_list_fcst):
        print('Computing GIBLs')
        gibls_fcst = steps_fcst.run_Calc_GIBL(ibls_fcst,lons_fcst)


    # Calc Blocks
    if ("CALCBLOCKS" in steps_list_obs):
        print('Computing Blocks')
        block_freq_obs = steps_obs.run_Calc_Blocks(ibls_obs,gibls_obs,lons_obs,daynum_obs,yr_obs)

    if ("CALCBLOCKS" in steps_list_fcst):
        print('Computing Blocks')
        block_freq_fcst = steps_fcst.run_Calc_Blocks(ibls_fcst,gibls_fcst,lons_fcst,daynum_fcst,yr_fcst)

    # Plot Blocking Frequency
    if ("PLOTBLOCKS" in steps_list_obs) and not ("PLOTBLOCKS" in steps_list_fcst):
        blocking_plot_title = config.getstr('Blocking','OBS_BLOCKING_PLOT_TITLE')
        blocking_plot_outname = config.getstr('Blocking','OBS_BLOCKING_PLOT_OUTPUT_NAME')
        pb.plot_blocks(block_freq_obs,gibls_obs,ibls_obs,lons_obs,blocking_plot_title,blocking_plot_outname)
    elif ("PLOTBLOCKS" in steps_list_fcst) and not ("PLOTBLOCKS" in steps_list_obs):
        blocking_plot_title = config.getstr('Blocking','FCST_BLOCKING_PLOT_TITLE')
        blocking_plot_outname = config.getstr('Blocking','FCST_BLOCKING_PLOT_OUTPUT_NAME')
        pb.plot_blocks(block_freq_fcst,gibls_fcst,ibls_fcst,lons_fcst,blocking_plot_title,blocking_plot_outname)
    elif ("PLOTBLOCKS" in steps_list_obs) and ("PLOTBLOCKS" in steps_list_fcst):
        blocking_plot_title = config.getstr('Blocking','BLOCKING_PLOT_TITLE')
        blocking_plot_outname = config.getstr('Blocking','BLOCKING_PLOT_OUTPUT_NAME')
        pb.plot_blocks(block_freq,gibls,ibls,lons,blocking_plot_title,blocking_plot_outname)


if __name__ == "__main__":
    main()
