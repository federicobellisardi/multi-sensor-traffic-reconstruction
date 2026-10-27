### JUST ONCE

#### I part: which OD corresponds to which coil

1. Find match between OD cities/provs and coils (for each pair OD among the N num_city more active it print the augmented config file if signal are present (max N^2-N config file) + the augmented config file) for Oprov-Dprov if signal are present. In this case you should consider just src-dest sources between cities and provs adding the tag -wr to the command line.
```
  od_match_confgen.py -c conf_od_match.json -o outputdir -m all -wr
```

  Conf file is like this:
```
  {
  "sim_times" : [
  [
  "2020-02-17 01:00:00",
  "2020-02-17 23:58:00"
  ]
  ],
  "coils_table_file" : "../work_spire/coils_table_200201-000000_200831-214500.csv",
  "od_average_dir" : "../work_od_average",
  "dir_table" : "../tables_fake",
  "num_city" : 50
  }
```

2. Run all the config file with `python/scan/scan_par_aug.py` on CNAF and obtain barriers file for each simulation

3. Measure ration areas between zero simulation (without any augmentation) and previous sim, select which coils are affected from OD variation charge and save OD-coils connection.
```
  od_match_make_distance.py -s0 barriers_sim0 -d dirofcsvbarriersfile
```
  this script make a "matched.csv" file with this heder: "Coil;O;D;ra"


#### II part: what is their relation

1. Just for OD pairs previously selected make scan with different value of augmentation and generate config files.
```
   od_match_confgen.py -c conf_od_match.json -o outputdir -m matched -mf "matched.csv"
```
2. Run all the config file with python/scan/scan_par_aug.py on CNAF and obtain barriers file for each simulation

3. Make fit in order to obtain the value of A and B in relation y = A*x+B where y=ratio areas and x=n of augmentation. This script add two columns of A and B in matched.csv file and plot trend for each coil in outputdir
```
  multiple_config_plot.py -i "path of dir with barriers file" -o "path of plot outputdir" -mf "matched.csv"
```
### FOR EACH SIMULATION

4. Generate the metric_score_coils.csv that contains the ratio between simulated and read signal for each coil
```
  single_run.py -c config.json -r -p
```
5. Make a new run with augmented value for OD matched with coils and plot coils signal (synthetic and real)
```
  final_single_run.py -c config.json -mf matched.csv -mv metric_score_coils.csv -r -cp
```
 sim_plot_coils_syntvscam.py: used for plot synthetic and real signal of single run

