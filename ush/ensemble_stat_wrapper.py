#!/usr/bin/env python

'''
Program Name: ensemble_stat_wrapper.py
Contact(s): metplus-dev
Abstract:  Initial template based on grid_stat_wrapper by George McCabe
History Log:  Initial version
Usage: 
Parameters: None
Input Files:
Output Files:
Condition codes: 0 for success, 1 for failure
'''

from __future__ import (print_function, division)

import os
import glob
import met_util as util
from compare_gridded_wrapper import CompareGriddedWrapper
import string_template_substitution as sts

"""!@namespace EnsembleStatWrapper
@brief Wraps the MET tool ensemble_stat to compare ensemble datasets
@endcode
"""
class EnsembleStatWrapper(CompareGriddedWrapper):
    """!Wraps the MET tool ensemble_stat to compare ensemble datasets
    """
    def __init__(self, config, logger):
        super(EnsembleStatWrapper, self).__init__(config, logger)
        self.met_install_dir = self.config.getdir('MET_INSTALL_DIR')
        self.app_path = os.path.join(self.met_install_dir, 'bin/ensemble_stat')
        self.app_name = os.path.basename(self.app_path)

        # create the ensemble stat dictionary.
        self.c_dict = self.create_c_dict()

    def create_c_dict(self):
        """!Create a dictionary containing the values set in the config file
           that are required for running ensemble stat.
           This will make it easier for unit testing.

           Returns:
               @returns A dictionary of the ensemble stat values 
                        from the config file.
        """
        c_dict = super(EnsembleStatWrapper, self).create_c_dict()

        c_dict['ONCE_PER_FIELD'] = self.config.getbool('config',
                                                'ENSEMBLE_STAT_ONCE_PER_FIELD',
                                                False)

        c_dict['FCST_INPUT_DATATYPE'] = \
          self.config.getstr('config', 'FCST_ENSEMBLE_STAT_INPUT_DATATYPE', '')

        c_dict['OBS_POINT_INPUT_DATATYPE'] = \
          self.config.getstr('config', 'OBS_ENSEMBLE_STAT_INPUT_POINT_DATATYPE', '')

        c_dict['OBS_GRID_INPUT_DATATYPE'] = \
          self.config.getstr('config', 'OBS_ENSEMBLE_STAT_INPUT_GRID_DATATYPE', '')

        c_dict['GRID_VX'] = self.config.getstr('config', 'ENSEMBLE_STAT_GRID_VX', 'FCST')

        c_dict['CONFIG_FILE'] = \
            self.config.getstr('config', 'ENSEMBLE_STAT_CONFIG_FILE',
                          c_dict['CONFIG_DIR']+'/EnsembleStatConfig_SFC')

        c_dict['ENS_THRESH'] = \
          self.config.getstr('config', 'ENSEMBLE_STAT_ENS_THRESH', '1.0')

        # met_obs_error_table is not required, if it is not defined
        # set it to the empty string '', that way the MET default is used.
        c_dict['MET_OBS_ERROR_TABLE'] = \
            self.config.getstr('config', 'ENSEMBLE_STAT_MET_OBS_ERROR_TABLE','')

        # No Default being set this is REQUIRED TO BE DEFINED in conf file.
        c_dict['N_MEMBERS'] = \
            self.config.getint('config','ENSEMBLE_STAT_N_MEMBERS')

        c_dict['OBS_POINT_INPUT_DIR'] = \
          self.config.getdir('OBS_ENSEMBLE_STAT_POINT_INPUT_DIR', '')

        c_dict['OBS_POINT_INPUT_TEMPLATE'] = \
          self.config.getraw('filename_templates',
                               'OBS_ENSEMBLE_STAT_POINT_INPUT_TEMPLATE')

        c_dict['OBS_GRID_INPUT_DIR'] = \
          self.config.getdir('OBS_ENSEMBLE_STAT_GRID_INPUT_DIR', '')

        c_dict['OBS_GRID_INPUT_TEMPLATE'] = \
          self.config.getraw('filename_templates',
                               'OBS_ENSEMBLE_STAT_GRID_INPUT_TEMPLATE')

        # The ensemble forecast files input directory and filename templates
        c_dict['FCST_INPUT_DIR'] = \
          self.config.getdir('FCST_ENSEMBLE_STAT_INPUT_DIR', '')

        # This is a raw string and will be interpreted to generate the 
        # ensemble member filenames. This may be a list of 1 or n members.
        c_dict['FCST_INPUT_TEMPLATE'] = \
          util.getlist(self.config.getraw('filename_templates',
                               'FCST_ENSEMBLE_STAT_INPUT_TEMPLATE'))

        c_dict['OUTPUT_DIR'] =  self.config.getdir('ENSEMBLE_STAT_OUTPUT_DIR')

        # handle window variables [FCST/OBS]_[FILE_]_WINDOW_[BEGIN/END]
        self.handle_window_variables(c_dict)

        # need to set these so that find_data will succeed
        c_dict['OBS_POINT_WINDOW_BEGIN'] = c_dict['OBS_WINDOW_BEGIN']
        c_dict['OBS_POINT_WINDOW_END'] = c_dict['OBS_WINDOW_END']
        c_dict['OBS_GRID_WINDOW_BEGIN'] = c_dict['OBS_WINDOW_BEGIN']
        c_dict['OBS_GRID_WINDOW_END'] = c_dict['OBS_WINDOW_END']

        c_dict['OBS_POINT_FILE_WINDOW_BEGIN'] = c_dict['OBS_FILE_WINDOW_BEGIN']
        c_dict['OBS_POINT_FILE_WINDOW_END'] = c_dict['OBS_FILE_WINDOW_END']
        c_dict['OBS_GRID_FILE_WINDOW_BEGIN'] = c_dict['OBS_FILE_WINDOW_BEGIN']
        c_dict['OBS_GRID_FILE_WINDOW_END'] = c_dict['OBS_FILE_WINDOW_END']

        return c_dict


    def run_at_time_one_field(self, time_info, v):
        self.logger.error("run_at_time_one_field not implemented yet for {}"
                    .format(self.app_name))
        exit()


    def run_at_time_all_fields(self, time_info):
        """! Runs the MET application for a given time and forecast lead combination
              Args:
                @param time_info dictionary containing timing information
        """
        # get ensemble model files
        fcst_file_list = self.find_model_members(time_info)
        if not fcst_file_list:
            return

        self.infiles.append(fcst_file_list)

        v = self.c_dict['var_list']
        # get point observation file if requested
        if self.c_dict['OBS_POINT_INPUT_DIR'] != '':
            point_obs_path = self.find_data(time_info, v[0], 'OBS_POINT')
            if point_obs_path == None:
                self.logger.error("Could not find point obs file in " + self.c_dict['OBS_POINT_INPUT_DIR'] +\
                                  " for valid time " + time_info['valid_fmt'])
                return
            self.point_obs_files.append(point_obs_path)

        # get grid observation file if requested
        if self.c_dict['OBS_GRID_INPUT_DIR'] != '':
            grid_obs_path = self.find_data(time_info, v[0], 'OBS_GRID')
            if grid_obs_path == None:
                self.logger.error("Could not find grid obs file in " + self.c_dict['OBS_GRID_INPUT_DIR'] +\
                                  " for valid time " + time_info['valid_fmt'])
                return
            self.grid_obs_files.append(grid_obs_path)


        # set field info
        fcst_field = self.get_field_info(v, "something.grb2", 'FCST')
        obs_field = self.get_field_info(v, "something.grb2", 'OBS')
        ens_field = self.get_field_info(v, 'something.grb2', 'ENS')

        # run
        self.process_fields(time_info, fcst_field, obs_field, ens_field)


    def get_field_info(self, var_list, model_path, data_type):
        field_list = []
        for v in var_list:
            if data_type == 'FCST':
                level = v.fcst_level
                thresh = v.fcst_thresh
                name = v.fcst_name
                extra = v.fcst_extra
            elif data_type == 'OBS':
                level = v.obs_level
                thresh = v.obs_thresh
                name = v.obs_name
                extra = v.obs_extra
            elif data_type == 'ENS':
                if hasattr(v, 'ens_name'):
                    level = v.ens_level
                    thresh = v.ens_thresh
                    name = v.ens_name
                    extra = v.ens_extra
                else:
                    level = v.fcst_level
                    thresh = v.fcst_thresh
                    name = v.fcst_name
                    extra = v.fcst_extra
            else:
                return ''

            next_field = self.get_one_field_info(level, thresh, name, extra, data_type)
            field_list.append(next_field)

        return ','.join(field_list)


    def find_model_members(self, time_info):
        """! Finds the model member files to compare
              Args:
                @param time_info dictionary containing timing information
                @rtype string
                @return Returns a list of the paths to the ensemble model files
        """
        model_dir = self.c_dict['FCST_INPUT_DIR']
        # used for filling in missing files to ensure ens_thresh check is accurate
        fake_dir = '/ensemble/member/is/missing'

        # model_template is a list of 1 or more.
        ens_members_template = self.c_dict['FCST_INPUT_TEMPLATE']
        ens_members_path = []
        # get all files that exist
        for ens_member_template in ens_members_template:
            model_ss = sts.StringSub(self.logger, ens_member_template,
                                     **time_info)
            member_file = model_ss.doStringSub()
            expected_path = os.path.join(model_dir, member_file)

            # if wildcard expression, get all files that match
            if '?' in expected_path:
                wildcard_files = sorted(glob.glob(expected_path))
                self.logger.debug('Ensemble members file pattern: {}'
                                  .format(expected_path))
                self.logger.debug('{} members match file pattern'
                                  .format(str(len(wildcard_files))))

                # add files to list of ensemble members
                for wf in wildcard_files:
                    ens_members_path.append(wf)
            else:
                # otherwise check if file exists
                member_path = util.preprocess_file(expected_path,
                                    self.c_dict['FCST_INPUT_DATATYPE'],
                                                   self.config)

                # if the file exists, add it to the list
                if member_path != None:
                    ens_members_path.append(member_path)
                else:
                    # add relative path to fake dir and add to list
                    fake_path = os.path.join(fake_dir, member_file)
                    ens_members_path.append(fake_path)
                    self.logger.warning('Expected ensemble file {} not found'
                                        .format(member_file))

        # if more files found than expected, error and exit
        if len(ens_members_path) > self.c_dict['N_MEMBERS']:
            msg = 'Found more files than expected! ' +\
                  'Found {} expected {}. '.format(len(ens_members_path),
                                                 self.c_dict['N_MEMBERS']) +\
                  'Adjust wildcard expression in [filename_templates] '+\
                  'FCST_ENSEMBLE_STAT_INPUT_TEMPLATE or adjust [config] '+\
                  'ENSEMBLE_STAT_N_MEMBERS. Files found: {}'.format(ens_members_path)
            self.logger.error(msg)
            self.logger.error("Could not file files in {} for init {} f{} "
                              .format(model_dir, time_info['init_fmt'],
                                      str(time_info['lead_hours'])))
            return False
        # if fewer files found than expected, warn and add fake files
        elif len(ens_members_path) < self.c_dict['N_MEMBERS']:
            msg = 'Found fewer files than expected. '+\
              'Found {} expected {}.'.format(len(ens_members_path),
                                             self.c_dict['N_MEMBERS'])
            self.logger.warning(msg)
            # add fake files to list to get correct number of files for ens_thresh
            diff = self.c_dict['N_MEMBERS'] - len(ens_members_path)
            self.logger.warning('Adding {} fake files to '.format(str(diff))+\
                                'ensure ens_thresh check is accurate')
            for r in range(0, diff, 1):
                ens_members_path.append(fake_dir)

        # write file that contains list of ensemble files
        list_filename = time_info['init_fmt'] + '_' + \
          str(time_info['lead_hours']) + '_ensemble.txt'
        return self.write_list_file(list_filename, ens_members_path)


    def process_fields(self, time_info, fcst_field, obs_field, ens_field):
        """! Set and print environment variables, then build/run MET command
              Args:
                @param time_info dictionary containing timing information
                @param fcst_field field information formatted for MET config file
                @param obs_field field information formatted for MET config file
        """
        # set config file since command is reset after each run
        self.param = self.c_dict['CONFIG_FILE']

        # set up output dir with time info
        self.create_and_set_output_dir(time_info)

        # list of fields to print to log
        print_list = ["MODEL", "GRID_VX", "OBTYPE",
                      "CONFIG_DIR", "FCST_LEAD",
                      "FCST_FIELD", "OBS_FIELD",
                      'ENS_FIELD', "INPUT_BASE",
                      "OBS_WINDOW_BEGIN", "OBS_WINDOW_END",
                      "ENS_THRESH"]

        if self.c_dict["MET_OBS_ERROR_TABLE"]:
            self.add_env_var("MET_OBS_ERROR_TABLE",
                             self.c_dict["MET_OBS_ERROR_TABLE"])
            print_list.append("MET_OBS_ERROR_TABLE")

        self.add_env_var("FCST_FIELD", fcst_field)
        self.add_env_var("OBS_FIELD", obs_field)
        if ens_field != '':
            self.add_env_var("ENS_FIELD", ens_field)
        else:
            self.add_env_var("ENS_FIELD", fcst_field)
        self.add_env_var("MODEL", self.c_dict['MODEL'])
        self.add_env_var("OBTYPE", self.c_dict['OBTYPE'])
        self.add_env_var("GRID_VX", self.c_dict['GRID_VX'])
        self.add_env_var("CONFIG_DIR", self.c_dict['CONFIG_DIR'])
        self.add_env_var("INPUT_BASE", self.c_dict['INPUT_BASE'])
        self.add_env_var("FCST_LEAD", str(time_info['lead_hours']).zfill(3))
        self.add_env_var("OBS_WINDOW_BEGIN", str(self.c_dict['OBS_WINDOW_BEGIN']))
        self.add_env_var("OBS_WINDOW_END", str(self.c_dict['OBS_WINDOW_END']))
        self.add_env_var("ENS_THRESH", self.c_dict['ENS_THRESH'])

        # send environment variables to logger
        self.logger.debug("ENVIRONMENT FOR NEXT COMMAND: ")
        self.print_user_env_items()
        for l in print_list:
            self.print_env_item(l)
        self.logger.debug("COPYABLE ENVIRONMENT FOR NEXT COMMAND: ")
        self.print_env_copy(print_list)

        # check if METplus can generate the command successfully
        cmd = self.get_command()
        if cmd is None:
            self.logger.error("Could not generate command")
            return

        # run the MET command
        self.build()


    def clear(self):
        """!Unset class variables to prepare for next run time
        """
        self.args = []
        self.input_dir = ""
        self.infiles = []
        self.outdir = ""
        self.outfile = ""
        self.param = ""
        self.point_obs_files = []
        self.grid_obs_files = []


    def get_command(self):
        """! Builds the command to run the MET application
           @rtype string
           @return Returns a MET command with arguments that you can run
        """
        if self.app_path is None:
            self.logger.error(self.app_name + ": No app path specified. \
                              You must use a subclass")
            return None

        cmd = '{} -v {} '.format(self.app_path, self.verbose)

        for a in self.args:
            cmd += a + " "

        if len(self.infiles) == 0:
            self.logger.error(self.app_name+": No input filenames specified")
            return None

        for f in self.infiles:
            cmd += f + " "

        if self.param != "":
            cmd += self.param + " "

        for f in self.point_obs_files:
            cmd += "-point_obs " + f + " "

        for f in self.grid_obs_files:
            cmd += "-grid_obs " + f + " "

        if self.outdir == "":
            self.logger.error(self.app_name+": No output directory specified")
            return None

        cmd += '-outdir {}'.format(self.outdir)
        return cmd


if __name__ == "__main__":
        util.run_stand_alone("ensemble_stat_wrapper", "EnsembleStat")
