# wmp_log_extract

This tool will parse given system log files or all messages, even archived ones,
in `/var/log/*` for entries of `wmp_memory_current` and present the data as 
human-readable table or as CSV file.

It is possible to limit the data to certain timestamps, cgroups or data and convert
the output to different units (KiB, MiB or GiB).  

The human readable output also lists the maximum and minimum values

CSV output can be used as import to other tools for further analysis or drawing graphs.

`wmp_memory_current` is part of the sapwmp package. For details read the chapter about
Workload Memory Protection in the official Guide of SLES for SAP Applications 15.

[SLES for SAP Applications SLES 15 SP2 - WMP](https://documentation.suse.com/sles-sap/15-SP2/html/SLES-SAP-guide/cha-tune.html#sec-memory-protection)

## Usage
```
wmp_log_extract.py [-h] [--timestamp PATTERN]
                          [--unit {B,kB,kiB,MB,MiB,GB,GiB}]
                          [--cgroup CGROUP,...] [--param PARAM,...] [--sort]
                          [--csv] [--delim DELIM]
                          [LOGFILE [LOGFILE ...]]

Extracts WMP cgroup memory data from system log and prints it as CSV or as a human-readable table.

positional arguments:
  LOGFILE               (xz compressed) system log file (default is /var/log/messages*)

optional arguments:
  -h, --help            show this help message and exit
  --timestamp PATTERN   regular expression used to filter timestamps
  --unit {B,kB,kiB,MB,MiB,GB,GiB}
                        unit for memory values
  --cgroup CGROUP,...   extract only these cgroups
  --param PARAM,...     extract only these controller parameters
  --sort                sort timestamps
  --csv                 print data as CSV with delimiter character (default is
                        comma)
  --delim DELIM         delimiter character for CSV output
```

If no log files are given, the script will parse all messages files in `/var/log/` in alphabetical order. If you list log files as arguments, please make sure the files ar in the correct order or use `--sort` to have sorted timestamps.
The memory values in the logs are in bytes. Especially on larger systems, this is hard to grasp, so you can switch to a more convinient uint with `--unit`.

If you are interested only in specific cgroups or controller parameters you can limit the output with `--cgroup` and `--param`.  

For analysis most times only data of a specific time range are useful, like for a specific day, week or moth. With `--timestamp` you can define a regular expression to filter only specific timestamps.

The default output is a human-readable table including maximum and minimum values. 
For deeper analysis or drawing graphs you can export the data as CSV with `--csv` to process them with other tools. Default separator is the comma, but this can be changed with `--delim`.


## Examples

### Getting an overview of all collected data in the system log

```
 # ./wmp_log_extract.py

           timestamp             SAP.slice    SAP.slice    user.slice   user.slice   init.scope   init.scope   data-protector.socket data-protector.socket csync2.socket csync2.socket  rpcbind.socket rpcbind.socket system.slice  system.slice 
                                 memory.low memory.current memory.low memory.current memory.low memory.current      memory.low          memory.current      memory.low   memory.current   memory.low   memory.current  memory.low  memory.current
================================ ========== ============== ========== ============== ========== ============== ===================== ===================== ============= ============== ============== ============== ============ ==============
2020-09-18T08:10:59.506261+00:00          0              0          0       92217344          0       10584064                     0                  4096             0           4096              0          12288            0     1198563328
2020-09-18T08:21:05.958765+00:00          0              0          0      655872000          0       10125312                     0                  4096             0           4096              0          12288            0     1246830592
2020-09-18T08:30:58.541972+00:00          0              0          0      689807360          0       10354688                     0                  4096             0           4096              0          12288            0     1249996800
2020-09-18T08:42:50.716478+00:00          0    53765943296          0      788279296          0       12677120                     0                  4096             0           4096              0          12288            0     1973104640
...
2020-09-28T23:31:47.894334+00:00          0    66897539072          0     1268387840          0       57430016                     0                  4096             0           4096              0          12288            0     2255523840
2020-09-28T23:40:26.761930+00:00          0    66980184064          0     1280581632          0       57647104                     0                  4096             0           4096              0          12288            0     2271358976
2020-09-28T23:50:36.559319+00:00          0    66981888000          0     1279131648          0       57384960                     0                  4096             0           4096              0          12288            0     2275016704

                                 SAP.slice    SAP.slice    user.slice   user.slice   init.scope   init.scope   data-protector.socket data-protector.socket csync2.socket csync2.socket  rpcbind.socket rpcbind.socket system.slice  system.slice 
                                 memory.low memory.current memory.low memory.current memory.low memory.current      memory.low          memory.current      memory.low   memory.current   memory.low   memory.current  memory.low  memory.current
================================ ========== ============== ========== ============== ========== ============== ===================== ===================== ============= ============== ============== ============== ============ ==============
                         minimum          0              0          0       92217344          0       10125312                     0                  4096             0           4096              0          12288            0     1198563328
                         maximum          0   109700108288          0     3650109440          0      226021376                     0                155648             0           4096              0          12288            0    26687668224
```

You can see for each timestamp the values of `memory.low` and `memory.current` for each cgroup. Below also the maximum and minimum value is displayed.
The unit is byte.

### Display only the data for the `SAP.slice` on a specific day with a more convenient unit

```
 # ./wmp_log_extract.py --unit GiB --timestamp '^2020-09-28' --cgroup SAP.slice 

           timestamp             SAP.slice    SAP.slice   
                                 memory.low memory.current
================================ ========== ==============
2020-09-28T00:00:30.632187+00:00        0.0          101.5
2020-09-28T00:10:41.036439+00:00        0.0          101.5
2020-09-28T00:22:21.723392+00:00        0.0          101.5
...
2020-09-28T23:40:26.761930+00:00        0.0           62.4
2020-09-28T23:50:36.559319+00:00        0.0           62.4

                                 SAP.slice    SAP.slice   
                                 memory.low memory.current
================================ ========== ==============
                         minimum        0.0            0.0
                         maximum        0.0          102.2
```

You can see for the 28th the values of `memory.low` and `memory.current` for `SAP.slice`. Below also the maximum and minimum value is displayed.
The unit is byte.


### Display only the data for `memory.current` and `memory.swap.current` of all cgroups on a specific month with a more convenient unit 

```
 # ./wmp_log_extract.py  --unit GiB --timestamp '^2020-09' --param memory.current,memory.swap.current

           timestamp               SAP.slice         SAP.slice        user.slice       user.slice        init.scope       init.scope       system.slice     system.slice    
                                 memory.current memory.swap.current memory.current memory.swap.current memory.current memory.swap.current memory.current memory.swap.current
================================ ============== =================== ============== =================== ============== =================== ============== ===================
2020-09-01T00:00:01.477420+02:00            3.3                 0.0            1.9                 0.0            0.0                 0.0            0.7                 0.0
2020-09-01T00:02:57.964914+02:00            3.3                 0.0            1.9                 0.0            0.0                 0.0            0.7                 0.0
2020-09-01T00:03:08.768000+02:00            3.3                 0.0            1.9                 0.0            0.0                 0.0            0.7                 0.0
...
2020-09-30T17:51:25.047972+02:00            3.3                 0.0            2.0                 0.0            0.0                 0.0            0.7                 0.0
2020-09-30T17:52:50.021523+02:00            3.3                 0.0            2.0                 0.0            0.0                 0.0            0.7                 0.0
2020-09-30T17:54:25.047338+02:00            3.3                 0.0            2.0                 0.0            0.0                 0.0            0.7                 0.0

                                   SAP.slice         SAP.slice        user.slice       user.slice        init.scope       init.scope       system.slice     system.slice    
                                 memory.current memory.swap.current memory.current memory.swap.current memory.current memory.swap.current memory.current memory.swap.current
================================ ============== =================== ============== =================== ============== =================== ============== ===================
                         minimum            3.3                 0.0            1.9                 0.0            0.0                 0.0            0.7                 0.0
                         maximum            3.3                 0.0            2.2                 0.0            0.0                 0.0            0.7                 0.0
```

You can see the values of `memory.current` and `memory.swap.current` for all cgroups in GiB. Below also the maximum and minimum value is displayed.
This would be useful to see the memeory consuption of the system and if and in which cgroup swapping occured.


### Create a CSV file with all data and enforce sorted timestamps

```
# ./wmp_log_extract.py --csv --sort > wmp_data.csv

# cat wmp_data.csv
timestamp,SAP.slice/memory.low,SAP.slice/memory.current,SAP.slice/memory.swap.current,user.slice/memory.low,user.slice/memory.current,user.slice/memory.swap.current,init.scope/memory.low,init.scope/memory.current,init.scope/memory.swap.current,system.slice/memory.low,system.slice/memory.current,system.slice/memory.swap.current
2020-09-24T00:00:01.477420+02:00,16106127360,3552940032,0,0,2083557376,0,0,7647232,0,0,731123712,0
2020-09-24T00:02:57.964914+02:00,16106127360,3552976896,0,0,2080681984,0,0,7421952,0,0,706076672,0
2020-09-24T00:03:08.768000+02:00,16106127360,3552919552,0,0,2080833536,0,0,7467008,0,0,705712128,0
...
```

All collected data in CSV for further processing, like drawing graphs with gnuplot, LibreCalc, Excel or other tools.

