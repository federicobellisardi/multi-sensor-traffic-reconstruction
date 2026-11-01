#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import argparse
import glob
import json
import os
import sys
from datetime import datetime
from itertools import product
from scipy.optimize import curve_fit

def func_l1(x, a):
    return a*x - a

def func_ra(x, a, b):
    return a*x + b

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-i', '--input_dir', help='directory of barriers.csv', required=True)
  parser.add_argument('-o', '--output_dir', help='directory of output plot', required=True)
  parser.add_argument('-mf', '--matchfile', help='dataframe of match coil-OD', required=True)
  args = parser.parse_args()

  indir= args.input_dir
  outdir= args.output_dir

  barries_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers_mini.csv')
  df_bar = pd.read_csv(barries_path, sep=';')

  df_match = pd.read_csv(args.matchfile, sep=';')
  list_coils = df_match['Coil'].to_list()
  list_a=[]
  list_b=[]

  file_list = [f for f in os.listdir(indir) if os.path.isfile(os.path.join(indir, f))]
  aug_range = np.arange(1.0, 12.0, 2.0)

  if not os.path.exists(outdir): os.mkdir(outdir)

  for k in list_coils:
    print('Analisi di: ', k)
    metric_val=[]

    file_0 = [f for f in file_list if k+'_1.0' in f]
    df_0 = pd.read_csv(os.path.join(indir, file_0[0]), sep=';')
    df_0_coil = df_0[df_0.columns.intersection([k])].sum(axis=1)

    for a in aug_range:
      file_w = [f for f in file_list if k+'_'+str(a) in f]
      df_w = pd.read_csv(os.path.join(indir, file_w[0]), sep=';')
      df_w_coil = df_w[df_w.columns.intersection([k])].sum(axis=1)

      v0   = df_0_coil.to_numpy()
      vsyn = df_w_coil.to_numpy()

      ### metric: l1 distance
      #l1 = abs(vsyn-v0)
      #l1 = l1.sum()
      #l1 /= abs(v0).sum(axis=0)
      #metric_val.append(l1)

      ### metric: area ratio
      asyn = vsyn.sum()
      a0 = v0.sum()
      ratio =asyn/a0
      metric_val.append(ratio)


    plt.plot(aug_range, metric_val, 'o-')
    plt.xlabel('Multiplication Factor')
    plt.ylabel('Ratio area')
    plt.title(k)
    plt.savefig(os.path.join(outdir, k+'.png'), dpi=150)
    plt.clf()


    #popt, pcov = curve_fit(func_l1, aug_range, l1_val_coil)
    popt, pcov = curve_fit(func_ra, aug_range, metric_val)
    list_a.append(popt[0])
    list_b.append(popt[1])


  df_match['A'] = list_a
  df_match['B'] = list_b
  df_match.to_csv(args.matchfile, sep=';', index=False)
