#!/usr/bin/env python

'''
Program Name: mtd_wrapper.py
Contact(s): George McCabe
Abstract: Runs mode time domain
History Log:  Initial version
Usage: 
Parameters: None
Input Files:
Output Files:
Condition codes: 0 for success, 1 for failure
'''

from __future__ import (print_function, division)

import os
import met_util as util
import time_util
from mode_wrapper import ModeWrapper

class MTDWrapper(ModeWrapper):

    def __init__(self, p, logger):
        super(MTDWrapper, self).__init__(p, logger)
        self.app_path = os.path.join(self.config.getdir('MET_INSTALL_DIR'),
                                     'bin/mtd')
        self.app_name = os.path.basename(self.app_path)
        self.fcst_file = None
        self.obs_file = None
        self.c_dict = self.create_c_dict()


    # TODO : Set defaults for all items that need them
    def create_c_dict(self):
        c_dict = super(ModeWrapper, self).create_c_dict()

        # set to prevent find_obs from getting multiple files within
        #  a time window. Does not refer to time series of files
        c_dict['ALLOW_MULTIPLE_FILES'] = False

        c_dict['OUTPUT_DIR'] = self.config.getdir('MTD_OUTPUT_DIR',
                                           self.config.getdir('OUTPUT_BASE'))
        c_dict['CONFIG_FILE'] = self.config.getstr('config', 'MTD_CONFIG', '')
        c_dict['MIN_VOLUME'] = self.config.getstr('config', 'MTD_MIN_VOLUME', '2000')
        c_dict['SINGLE_RUN'] = self.config.getbool('config', 'MTD_SINGLE_RUN', False)
        c_dict['SINGLE_DATA_SRC'] = self.config.getstr('config', 'MTD_SINGLE_DATA_SRC', 'FCST')

        # only read FCST conf if processing forecast data
        if not c_dict['SINGLE_RUN'] or c_dict['SINGLE_DATA_SRC'] == 'FCST':
            c_dict['FCST_IS_PROB'] = self.config.getbool('config', 'FCST_IS_PROB', False)
            c_dict['FCST_INPUT_DIR'] = \
              self.config.getdir('FCST_MTD_INPUT_DIR', c_dict['INPUT_BASE'])
            c_dict['FCST_INPUT_TEMPLATE'] = \
              self.config.getraw('filename_templates',
                                 'FCST_MTD_INPUT_TEMPLATE')
            c_dict['FCST_INPUT_DATATYPE'] = \
                self.config.getstr('config', 'FCST_MTD_INPUT_DATATYPE', '')

            if self.config.has_option('config', 'MTD_FCST_CONV_RADIUS'):
                c_dict['FCST_CONV_RADIUS'] = self.config.getstr('config', 'MTD_FCST_CONV_RADIUS')
            else:
                c_dict['FCST_CONV_RADIUS'] = self.config.getstr('config', 'MTD_CONV_RADIUS', '5')

            if self.config.has_option('config', 'MTD_FCST_CONV_THRESH'):
                c_dict['FCST_CONV_THRESH'] = self.config.getstr('config', 'MTD_FCST_CONV_THRESH')
            else:
                c_dict['FCST_CONV_THRESH'] = self.config.getstr('config', 'MTD_CONV_THRESH', '>0.5')

            # check that values are valid
            if not util.validate_thresholds(util.getlist(c_dict['FCST_CONV_THRESH'])):
                self.logger.error('MTD_FCST_CONV_THRESH items must start with a comparison operator (>,>=,==,!=,<,<=,gt,ge,eq,ne,lt,le)')
                exit(1)

        # only read OBS conf if processing observation data
        if not c_dict['SINGLE_RUN'] or c_dict['SINGLE_DATA_SRC'] == 'OBS':
            c_dict['OBS_IS_PROB'] = self.config.getbool('config', 'OBS_IS_PROB', False)
            c_dict['OBS_INPUT_DIR'] = \
            self.config.getdir('OBS_MTD_INPUT_DIR', c_dict['INPUT_BASE'])
            c_dict['OBS_INPUT_TEMPLATE'] = \
              self.config.getraw('filename_templates',
                                   'OBS_MTD_INPUT_TEMPLATE')
            c_dict['OBS_INPUT_DATATYPE'] = \
                self.config.getstr('config', 'OBS_MTD_INPUT_DATATYPE', '')

            if self.config.has_option('config', 'MTD_OBS_CONV_RADIUS'):
                c_dict['OBS_CONV_RADIUS'] = self.config.getstr('config', 'MTD_OBS_CONV_RADIUS')
            else:
                c_dict['OBS_CONV_RADIUS'] = self.config.getstr('config', 'MTD_CONV_RADIUS', '5')

            if self.config.has_option('config', 'MTD_OBS_CONV_THRESH'):
                c_dict['OBS_CONV_THRESH'] = self.config.getstr('config', 'MTD_OBS_CONV_THRESH')
            else:
                c_dict['OBS_CONV_THRESH'] = self.config.getstr('config', 'MTD_CONV_THRESH', '>0.5')


        # if window begin/end is set specific to mode, override
        # OBS_WINDOW_BEGIN/END
        if self.config.has_option('config', 'OBS_MTD_WINDOW_BEGIN'):
            c_dict['OBS_WINDOW_BEGIN'] = \
              self.config.getint('config', 'OBS_MTD_WINDOW_BEGIN')
        if self.config.has_option('config', 'OBS_MTD_WINDOW_END'):
            c_dict['OBS_WINDOW_END'] = \
              self.config.getint('config', 'OBS_MTD_WINDOW_END')

        # same for FCST_WINDOW_BEGIN/END
        if self.config.has_option('config', 'FCST_MTD_WINDOW_BEGIN'):
            c_dict['FCST_WINDOW_BEGIN'] = \
              self.config.getint('config', 'FCST_MTD_WINDOW_BEGIN')
        if self.config.has_option('config', 'FCST_MTD_WINDOW_END'):
            c_dict['FCST_WINDOW_END'] = \
              self.config.getint('config', 'FCST_MTD_WINDOW_END')

            # check that values are valid
            if not util.validate_thresholds(util.getlist(c_dict['OBS_CONV_THRESH'])):
                self.logger.error('MTD_OBS_CONV_THRESH items must start with a comparison operator (>,>=,==,!=,<,<=,gt,ge,eq,ne,lt,le)')
                exit(1)

        return c_dict


    def run_at_time(self, input_dict):
        """! Runs the MET application for a given run time. This function loops
              over the list of forecast leads and runs the application for each.
              Overrides run_at_time in compare_gridded_wrapper.py
              Args:
                @param init_time initialization time to run. -1 if not set
                @param valid_time valid time to run. -1 if not set
        """        
        var_list = util.parse_var_list(self.config)
#        current_task = TaskInfo()
#        max_lookback = self.c_dict['MAX_LOOKBACK']
#        file_interval = self.c_dict['FILE_INTERVAL']

        lead_seq = util.get_lead_sequence(self.config, input_dict)
        for v in var_list:
            if self.c_dict['SINGLE_RUN']:
                self.run_single_mode(input_dict, v)
                continue

            model_list = []
            obs_list = []
            # find files for each forecast lead time
            tasks = []
            for lead in lead_seq:
                input_dict['lead_hours'] = lead
                time_info = time_util.ti_calculate(input_dict)
                tasks.append(time_info)

            # TODO: implement mode to keep fcst lead constant and increment init/valid time
            # loop from valid time to valid time + offset by step, set lead and find files
            for current_task in tasks:
                # call find_model/obs as needed
                model_file = self.find_model(current_task, v)
                obs_file = self.find_obs(current_task, v)
                if model_file is None and obs_file is None:
                    self.logger.warning('Obs and fcst files were not found for init {} and lead {}'.
                                        format(current_task['init_fmt'], current_task['lead_hours']))
                    continue
                if model_file is None:
                    self.logger.warning('Forecast file was not found for init {} and lead {}'.
                                        format(current_task['init_fmt'], current_task['lead_hours']))
                    continue
                if obs_file is None:
                    self.logger.warning('Observation file was not found for init {} and lead {}'.
                                        format(current_task['init_fmt'], current_task['lead_hours']))
                    continue
                model_list.append(model_file)
                obs_list.append(obs_file)

            if len(model_list) == 0:
                return

            # write ascii file with list of files to process
            input_dict['lead_hours'] = 0
            time_info = time_util.ti_calculate(input_dict)
            model_outfile = time_info['valid_fmt'] + '_mtd_fcst_' + v.fcst_name + '.txt'
            obs_outfile = time_info['valid_fmt'] + '_mtd_obs_' + v.obs_name + '.txt'
            model_list_path = self.write_list_file(model_outfile, model_list)
            obs_list_path = self.write_list_file(obs_outfile, obs_list)

            arg_dict = {'obs_path' : obs_list_path,
                        'model_path' : model_list_path }

            self.process_fields_one_thresh(current_task, v, **arg_dict)


    def run_single_mode(self, input_dict, v):
        single_list = []

        if self.c_dict['SINGLE_DATA_SRC'] == 'OBS':
            find_method = self.find_obs
            s_name = v.obs_name
            s_level = v.obs_level
        else:
            find_method = self.find_model
            s_name = v.fcst_name
            s_level = v.fcst_level

        lead_seq = util.get_lead_sequence(self.config, input_dict)
        for lead in lead_seq:
            input_dict['lead_hours'] = lead
            current_task = time_util.ti_calculate(input_dict)

            single_file = find_method(current_task, v)
            if single_file is None:
                self.logger.warning('Single file was not found for init {} and lead {}'.
                                    format(current_task['init_fmt'], current_task['lead_hours']))
                continue
            single_list.append(single_file)

        if len(single_list) == 0:
            return

        # write ascii file with list of files to process
        input_dict['lead_hours'] = 0
        time_info = time_util.ti_calculate(input_dict)
        single_outfile = time_info['valid_fmt'] + '_mtd_single_' + s_name + '.txt'
        single_list_path = self.write_list_file(single_outfile, single_list)

        arg_dict = {}
        if self.c_dict['SINGLE_DATA_SRC'] == 'OBS':
            arg_dict['obs_path'] = single_list_path
            arg_dict['model_path'] = None
        else:
            arg_dict['model_path'] = single_list_path
            arg_dict['obs_path'] = None

        self.process_fields_one_thresh(current_task, v, **arg_dict)


    def process_fields_one_thresh(self, time_info, v, model_path, obs_path):
        """! For each threshold, set up environment variables and run mode
              Args:
                @param time_info dictionary containing timing information
                @param v var_info object containing variable information
                @param model_path forecast file list path
                @param obs_path observation file list path
        """
        # if no thresholds are specified, run once
        fcst_thresh_list = [0]
        obs_thresh_list = [0]
        if len(v.fcst_thresh) != 0:
            fcst_thresh_list = v.fcst_thresh
            obs_thresh_list = v.obs_thresh

        for fthresh, othresh in zip(fcst_thresh_list, obs_thresh_list):
            self.set_param_file(self.c_dict['CONFIG_FILE'])
            self.create_and_set_output_dir(time_info)

            print_list = [ 'MIN_VOLUME', 'MODEL', 'FCST_VAR', 'OBTYPE',
                           'OBS_VAR', 'LEVEL', 'CONFIG_DIR',
                           'MET_VALID_HHMM', 'FCST_FIELD', 'OBS_FIELD',
                           'FCST_CONV_RADIUS', 'FCST_CONV_THRESH',
                           'OBS_CONV_RADIUS', 'OBS_CONV_THRESH' ]
            self.add_env_var("MIN_VOLUME", self.c_dict["MIN_VOLUME"] )
            self.add_env_var("MODEL", self.c_dict['MODEL'])
            self.add_env_var("FCST_VAR", v.fcst_name)
            self.add_env_var("OBTYPE", self.c_dict['OBTYPE'])
            self.add_env_var("OBS_VAR", v.obs_name)
            self.add_env_var("LEVEL", util.split_level(v.fcst_level)[1])
            self.add_env_var("CONFIG_DIR", self.c_dict['CONFIG_DIR'])
            self.add_env_var("MET_VALID_HHMM", time_info['valid_fmt'][4:8])

            # single mode - set fcst file, field, etc.
            if self.c_dict['SINGLE_RUN']:
                if self.c_dict['SINGLE_DATA_SRC'] == 'OBS':
                    self.set_fcst_file(obs_path)
                    obs_field = self.get_one_field_info(v.obs_name, v.obs_level, v.obs_extra,
                                                        othresh, 'OBS')
                    self.add_env_var("FCST_FIELD", obs_field)
                    self.add_env_var("OBS_FIELD", obs_field)
                    self.add_env_var("OBS_CONV_RADIUS", self.c_dict["OBS_CONV_RADIUS"] )
                    self.add_env_var("FCST_CONV_RADIUS", self.c_dict["OBS_CONV_RADIUS"] )
                    self.add_env_var("OBS_CONV_THRESH", self.c_dict["OBS_CONV_THRESH"] )
                    self.add_env_var("FCST_CONV_THRESH", self.c_dict["OBS_CONV_THRESH"] )
                else:
                    self.set_fcst_file(model_path)
                    fcst_field = self.get_one_field_info(v.fcst_name, v.fcst_level, v.fcst_extra,
                                                         fthresh, 'FCST')
                    self.add_env_var("FCST_FIELD", fcst_field)
                    self.add_env_var("OBS_FIELD", fcst_field)
                    self.add_env_var("FCST_CONV_RADIUS", self.c_dict["FCST_CONV_RADIUS"] )
                    self.add_env_var("OBS_CONV_RADIUS", self.c_dict["FCST_CONV_RADIUS"] )
                    self.add_env_var("FCST_CONV_THRESH", self.c_dict["FCST_CONV_THRESH"] )
                    self.add_env_var("OBS_CONV_THRESH", self.c_dict["FCST_CONV_THRESH"] )
            else:
                self.set_fcst_file(model_path)
                self.set_obs_file(obs_path)
                self.add_env_var("FCST_CONV_RADIUS", self.c_dict["FCST_CONV_RADIUS"] )
                self.add_env_var("FCST_CONV_THRESH", self.c_dict["FCST_CONV_THRESH"] )
                self.add_env_var("OBS_CONV_RADIUS", self.c_dict["OBS_CONV_RADIUS"] )
                self.add_env_var("OBS_CONV_THRESH", self.c_dict["OBS_CONV_THRESH"] )

                fcst_field = self.get_one_field_info(v.fcst_name, v.fcst_level, v.fcst_extra,
                                                     fthresh, 'FCST')
                obs_field = self.get_one_field_info(v.obs_name, v.obs_level, v.obs_extra,
                                                    othresh, 'OBS')

                self.add_env_var("FCST_FIELD", fcst_field)
                self.add_env_var("OBS_FIELD", obs_field)

            self.logger.debug("ENVIRONMENT FOR NEXT COMMAND: ")
            self.print_user_env_items()
            for l in print_list:
                self.print_env_item(l)

            self.logger.debug("COPYABLE ENVIRONMENT FOR NEXT COMMAND: ")
            self.print_env_copy(print_list)

            cmd = self.get_command()
            if cmd is None:
                self.logger.error(self.app_name + " could not generate command")
                return
            self.build()
            self.clear()


    def set_fcst_file(self, fcst_file):
        self.fcst_file = fcst_file


    def set_obs_file(self, obs_file):
        self.obs_file = obs_file


    def clear(self):
        super(MTDWrapper, self).clear()
        self.fcst_file = None
        self.obs_file = None


    def get_command(self):
        """! Builds the command to run the MET application
           @rtype string
           @return Returns a MET command with arguments that you can run
        """
        if self.app_path is None:
            self.logger.error(self.app_name + ": No app path specified. \
                              You must use a subclass")
            return None

        cmd = self.app_path + " "
        for a in self.args:
            cmd += a + " "

        if self.c_dict['SINGLE_RUN']:
            if self.fcst_file == None:
                self.logger.error("No file path specified")
                return None
            cmd += '-single ' + self.fcst_file + ' '
        else:
            if self.fcst_file == None:
                self.logger.error("No forecast file path specified")
                return None

            if self.obs_file == None:
                self.logger.error("No observation file path specified")
                return None

            cmd += '-fcst ' + self.fcst_file + ' '
            cmd += '-obs ' + self.obs_file + ' '

        cmd += '-config ' + self.param + ' '

        if self.outdir != "":
            cmd += self.outdir + ' '

        # TODO: is logfile and verbose ever set?
#        if self.logfile != "":
#            cmd += " -log "+self.logfile

        if self.verbose != -1:
            cmd += "-v "+str(self.verbose) + " "

        return cmd


if __name__ == "__main__":
    util.run_stand_alone("mtd_wrapper", "MTD")
