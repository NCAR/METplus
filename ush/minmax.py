#!/usr/bin/python

import os
import sys
import re
import constants_pdef as P

def get_nc_files():

    base_dir = "/d1/minnawin/SBU_out/series_analysis/python_lead"

    dirs = [os.path.normcase(f) for f in os.listdir(base_dir)]
    filename_regex = "series_F[0-9]{3}.*nc"


    all_nc_files = []
    for dir in dirs:
        full_path = os.path.join(base_dir,dir)
        #print("full path: {} ".format(full_path))

        # Get a list of files for each of these series subdirectories
    
        nc_files_list = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path,f))]
        for cur_nc in nc_files_list:
            match = re.match(filename_regex,cur_nc)
            if match:
                nc_file = os.path.join(full_path,cur_nc)
                all_nc_files.append(nc_file)
    return all_nc_files


def get_min_max(nc_files):
    '''Get the min and max values for all lead times for variables and statistics.  
       The min and max are computed using the NCO utility ncap2.
       
       Args:  
          nc_files:  A list of all the netCDF files generated by the MET series analysis tool.


       Returns:
       tuple(min,max): The min and max value for a given variable and statistic.

    '''

    p = P.Params()
    p.init(__doc__) 

    var_list = p.opt["VAR_LIST"]
    stat_list = p.opt["STAT_LIST"]
    out_dir_base = p.opt["OUT_DIR"]
    ncap2_exe = p.opt["NCAP2_EXE"]
    ncdump_exe = p.opt["NCDUMP_EXE"]

    VMIN = 999999
    VMAX = -999999

  
    for cur_stat in stat_list:
        os.environ['CUR_STAT'] = cur_stat
        cleanup_min_max_tempfiles(p)
    
        for cur_nc in nc_files:
            # Determine the series_F<fhr> subdirectory where this netCDF file
            # resides.
            match = re.match(r'(.*/series_F[0-9]{3})/series_F[0-9]{3}.*nc', cur_nc)
            if match:
                base_nc_dir = match.group(1)
            else:
                logger.error("Cannot determine base directory path for netCDF files")
                logger.error("current netCDF file: " + cur_nc)
                sys.exit()
     
            min_nc_path = os.path.join(base_nc_dir, 'min.nc')
            max_nc_path = os.path.join(base_nc_dir, 'max.nc')
            nco_min_cmd_parts = [ncap2_exe, ' -v -s ', '"','min=min(series_cnt_', cur_stat,')', '" ', cur_nc, ' ', min_nc_path]
            nco_max_cmd_parts = [ncap2_exe, ' -v -s ', 'max=max(series_cnt_', cur_stat,') ', cur_nc, ' ', max_nc_path]
            nco_min_cmd = ''.join(nco_min_cmd_parts)
            nco_max_cmd = ''.join(nco_max_cmd_parts)
            #print("MIN cmd: {}".format(nco_min_cmd))
            #print("MAX cmd: {}".format(nco_max_cmd))
            os.system(nco_min_cmd)
            os.system(nco_max_cmd)
        
         
            min_txt_path = os.path.join(base_nc_dir, 'min.txt')
            max_txt_path = os.path.join(base_nc_dir, 'max.txt')
            ncdump_min_cmd_parts = [ncdump_exe, ' ', base_nc_dir,'/min.nc > ', min_txt_path]
            ncdump_min_cmd = ''.join(ncdump_min_cmd_parts)
            ncdump_max_cmd_parts = [ncdump_exe,' ', base_nc_dir, '/max.nc > ', max_txt_path]
            ncdump_max_cmd = ''.join(ncdump_max_cmd_parts)
            #print("ncdump min cmd: {}".format(ncdump_min_cmd))
            #print("ncdump max cmd: {}".format(ncdump_max_cmd))
            os.system(ncdump_min_cmd)
            os.system(ncdump_max_cmd)

            # Look for the min and max values in each netCDF file.
            try:
                with open(min_txt_path,'r') as fmin:
                    for line in fmin:
                        min_match = re.match(r'.*min.*=\([0-9]{1,}.*;', line)
                        if min_match:
                            cur_min = min_match.group(1)    
                            if cur_min < VMIN:
                                VMIN = cur_min
                with open(max_txt_path,'r') as fmax:
                    for line in fmax:
                        max_match = re.match(r'.*max.*=\([0-9]{1,}.*;', line)
                        if max_match:
                            cur_max = max_match.group(1)
                            if cur_max >= VMAX:
                                VMAX = cur_max
                print("VMAX = {}".format(str(VMAX)))
                print("VMIN = {}".format(str(VMIN)))
            except IOError as e:
                print("ERROR cannot open the min or max text file")
                 


    return VMIN,VMAX




def cleanup_min_max_tempfiles(p):
    '''Clean up all the temporary netCDF and txt
       files used to determine the min and max.

       Args:
           p: ConfigMaster config file object.

       Returns:
           None:  removes any existing min.nc, max.nc,
                  min.txt, and max.txt files.

    '''
    stat_list = p.opt["STAT_LIST"]
    out_dir_base = p.opt["OUT_DIR"]
    rm_exe = p.opt["RM_EXE"]
    print("INSIDE cleanup of min max temp files")
    
    for cur_stat in stat_list: 
        minmax_nc_path = os.path.join(out_dir_base, 'python_lead/')
        # Iterate through all the series_F<fhr> directories and remove the 
        # temporary files created by other runs.
        series_dirs = [os.path.normcase(f) for f in os.listdir(minmax_nc_path)] 
        for dir in series_dirs:
            # Create the directory path that includes the series_F<fhr>.
            full_path = os.path.join(minmax_nc_path,dir)
             
            #print("minmax nc path: {}".format(full_path))
            min_nc_path = os.path.join(full_path, 'min.nc')
            max_nc_path = os.path.join(full_path, 'max.nc')
            rm_min_cmd_parts = [rm_exe,' ', min_nc_path]
            rm_max_cmd_parts = [rm_exe,' ', max_nc_path]
            rm_min_cmd = ''.join(rm_min_cmd_parts)
            rm_max_cmd = ''.join(rm_max_cmd_parts)
            print("rm min.nc cmd: {}".format(rm_min_cmd))
 
            min_txt_path = os.path.join(full_path, 'min.txt')
            max_txt_path = os.path.join(full_path, 'max.txt')
            print("min text path: {}".format(min_txt_path))
            #print("max text path: {}".format(max_txt_path))
 
            rm_min_txt_parts = [rm_exe,' ', min_txt_path]
            rm_max_txt_parts = [rm_exe,' ', max_txt_path]
            rm_min_txt = ''.join(rm_min_txt_parts)
            rm_max_txt = ''.join(rm_max_txt_parts)
            os.system(rm_min_cmd)
            os.system(rm_max_cmd)
            os.system(rm_min_txt)
            os.system(rm_max_txt)




if __name__ == "__main__":
    nc_files = get_nc_files()
    min,max = get_min_max(nc_files)

