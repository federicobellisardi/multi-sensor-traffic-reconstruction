#!/usr/bin/env python3

"""
Module: Viasat Analysis

Compare Viasat flux data with simulation data and generate detailed reports.
"""

# ----------------------------
# Standard Library Imports
# ----------------------------
import os, glob, json, argparse
from datetime import datetime, timedelta

# ----------------------------
# Data Processing Imports
# ----------------------------
import numpy as np
import pandas as pd
import geopandas as gpd

# ----------------------------
# Visualization Imports
# ----------------------------
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import rgb2hex
import folium

# ----------------------------
# Scientific / ML Imports
# ----------------------------
import scipy.spatial.distance as ssd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ----------------------------
# Helper Functions
# ----------------

def save_plot(fig, filename, dpi=150):
    """Save matplotlib figure to file and close it."""
    fig.savefig(filename, dpi=dpi)
    plt.close(fig)
    print(f"Image saved: {filename}")


def ensure_dir(path):
    """Create directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def get_viasat_filepath(year):
    """Return the Viasat data file path for a given year."""
    # mapping year to file
    base = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat')
    mapping = {
        '2021': 'viasat_20210628_20210705_timed_fluxes.csv',
        '2020': 'viasat_20200210_20200218_timed_fluxes.csv',
    }
    try:
        return os.path.join(base, mapping[year])
    except KeyError:
        raise ValueError(f"Unsupported year: {year}")


# ----------------------------
# Main Analysis Class
# -------------------
class ViasatAnalysis:
    """
    Core class for Viasat vs simulation analysis.
    Provides methods to load data, compute penetration statistics,
    detect anomalies, perform clustering, and generate visual reports.
    """

    def __init__(self, ncluster=3):
        """Initialize analysis parameters and empty DataFrames."""
        # Initialize parameters and empty dataframes
        self.ncluster = ncluster
        self.viasat_df = pd.DataFrame()
        self.uniq_df = pd.DataFrame()
        self.penetrazione_df = pd.DataFrame()
        self.cluster_df = pd.DataFrame()
        self.log_cluster_df = pd.DataFrame()
        self.cluster_dict = {}

        # output attributes (set in main)
        self.center_coords = None
        self.save_folder = None
        self.save_penetrazione = None

    def dist(self, a, b, metric='euclidean'):
        """Compute distance between two arrays (euclidean or correlation)."""
        # Compute distance between two arrays. Supports euclidean or correlation.
        if metric == 'euclidean':
            return np.linalg.norm(a - b)
        elif metric == 'correlation':
            return ssd.correlation(a, b)
        else:
            raise ValueError(f"Unknown metric: {metric}")

    def norm(self, a):
        """Normalize array by sum; return zeros if sum is zero."""
        # Normalize array by its sum; returns zero-array if sum is zero.
        total = a.sum()
        return a / total if total != 0 else np.zeros_like(a)

    def poly_filter(self, polycid):
        """Filter a list of polygon IDs or return all if none provided."""
        # Return filtered list of polygon IDs or all IDs if none specified.
        if polycid:
            return [int(i) for i in polycid]
        return list(self.viasat_df.columns)    

    # ----------------------------
    # Data Builders
    # ----------------------------
    def viasat_builder(self, viasatfile):
        """Load Viasat CSV and aggregate by hour."""
        # Load Viasat CSV, aggregate by hour and return dataframe.
        viasat_df = pd.read_csv(viasatfile, sep=';')
        viasat_df.set_index(pd.to_datetime(viasat_df.time), inplace=True)
        self.startdate_sim = viasat_df.index[0]
        self.stopdate_sim = viasat_df.index[-1]
        viasat_df = viasat_df[(viasat_df.index >= self.startdate_sim ) & (viasat_df.index < self.stopdate_sim)]
        viasat_df = viasat_df[['total_fluxes','cid']]
        viasat_df['time_hour'] = viasat_df.index.time
        viasat_df = viasat_df.groupby(['time_hour','cid']).sum()
        viasat_df = viasat_df.unstack(level='cid')
        viasat_df.columns = viasat_df.columns.droplevel(level=0)
        self.viasat_df = viasat_df.loc[:, (viasat_df != 0).any(axis=0)]
        # self.viasat_df = viasat_df[v.poly_filter(polyfilter)]
        return self.viasat_df

    def uniq_builder(self, polyfilter, year):
      self.poly_list = self.poly_filter(polyfilter)
      try:
        if year == '2020':
          uniq_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'sim2020', 'uniq')
        elif year == '2021':
          uniq_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'sim2021', 'uniq')
  
        uniq_all = sorted(glob.glob(uniq_path + '/*.csv.corrected'))
        uniq_all_df = pd.DataFrame()
        for uniq_file in uniq_all:
          uniq_df = pd.read_csv(uniq_file, sep=';')
          uniq_df = uniq_df.groupby('poly_cid').sum()
          uniq_df = uniq_df.drop(['poly_lid', 'oneway'], axis=1)
          uniq_df.columns = pd.to_datetime(uniq_df.columns)
          uniq_df = uniq_df.loc[self.poly_list]
          uniq_df = uniq_df.T
          uniq_df.index.rename('datetime', inplace=True)
          # uniq_df.index = uniq_df.index.tz_localize(None).tz_convert('Europe/Rome')
          uniq_df['new_time'] = [i+timedelta(minutes=75) for i in uniq_df.index]
          uniq_df.set_index('new_time', inplace=True)
          uniq_df['hour'] = [int(str(i).split(' ')[-1].split(':')[0]) for i in uniq_df.index]
          datetime_list = [i for i in uniq_df.index.to_list() if "15:00" in str(i)]
          uniq_df = uniq_df.groupby(by='hour').sum()
          uniq_df['datetime'] = datetime_list
          uniq_df.set_index('datetime', inplace=True)
          uniq_df['time_index'] = uniq_df.index.time
          uniq_df.set_index('time_index', inplace=True)
          uniq_all_df=pd.concat([uniq_all_df, uniq_df], axis=1).fillna(0)
        self.uniq_df = uniq_all_df.groupby(by=uniq_all_df.columns, axis=1).mean()
      except Exception as e:
        print("Error: ", e)
      return self.uniq_df


    # ----------------------------
    # Analysis Methods
    # ----------------------------
    def penetrazione(self, carto):
        """Compute penetration rates and generate statistical plots."""
        # Compute penetration rates, plot statistics, and generate cluster maps.

        plt.rcParams.update({
            'font.size': 18,         # default text size
            'axes.titlesize': 22,    # axes title
            'axes.labelsize': 20,    # x/y labels
            'xtick.labelsize': 18,   # x‐tick labels
            'ytick.labelsize': 18    # y‐tick labels
        })

        print(f"-> Start Statistical Penetration\n")
        penetration_list = []
        log_penetration_list = []
        for col in self.uniq_df.columns:
            uniq_single = self.uniq_df[col]
            viasat_single = self.viasat_df[col]

            unique_sum = uniq_single.to_numpy().sum()
            viasat_sum = viasat_single.to_numpy().sum()
            if unique_sum == 0: continue
            penetration = viasat_sum / unique_sum
            log_penetration = np.log10(penetration)
            penetration = penetration * 100
            penetration_list.append((col,penetration))
            log_penetration_list.append((col, log_penetration))

        penetration_df = pd.DataFrame(penetration_list, columns=['poly_cid','penetration'])
        penetration_df.set_index('poly_cid', inplace=True)
        self.penetrazione_df = penetration_df.copy()
        log_penetration_df = pd.DataFrame(log_penetration_list, columns=['poly_cid','log_penetration'])
        log_penetration_df.set_index('poly_cid', inplace=True)
       
        # print(f"-> -> Creating .html Major Cluster")
        # cluster_plot = self.major_cluster(penetration_df, carto, '')
        cluster_log_plot = self.major_cluster(log_penetration_df, carto, 'Log_')
        print(f"-> -> Done - .html Major Cluster\n")

        start = self.startdate_sim.date().strftime("%Y%m%d")
        stop  = self.stopdate_sim.date().strftime("%Y%m%d")
        out_txt = os.path.join(
            self.save_penetrazione,
            f"log_eta_{start}_{stop}.txt"
        )

        log_penetration_df['log_penetration'].to_csv(out_txt, index=False, header=False)
        print(f"  Text file saved to {out_txt}")

        ## Plot Stat Penetration %
        max_hight = penetration_df.values.max() + 0.25*penetration_df.values.max()
        w, h, d = 12, 7, 100
        fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
        tsd = [ p for p in range(len(penetration_df.index)) ]
        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ str(p) for p in penetration_df.index ]
        tsd_lbl = tsd_lbl[::lusd]
        width = 0.8
        bar_1 = ax.bar(tsd, penetration_df.penetration, width=width)
        for rect in bar_1:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
        ax.set_xticks(tsd_ticks)
        ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
        ax.set_ylabel('Penetration [%]')
        ax.set_xlabel('Poly CID')
        ax.set_ylim(0, max_hight)
        plt.title(f'Statistic penetration from {str(self.startdate_sim).split(" ")[0]} to {str(self.stopdate_sim).split(" ")[0]}\n viasat/sim')

        outname = os.path.join(self.save_penetrazione, f'penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png')
        fig.savefig(outname, dpi=150)
        print(f'  Image saved in {outname}')
        plt.clf()
        plt.close()

        # Sorted df
        penetration_df_sorted = penetration_df.sort_values(by=['penetration'], ascending=False)
        w, h, d = 12, 7, 100
        fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
        tsd = [ p for p in range(len(penetration_df_sorted.index)) ]

        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ str(p) for p in penetration_df_sorted.index ]
        tsd_lbl = tsd_lbl[::lusd]
        width = 0.8
        bar_1 = ax.bar(tsd, penetration_df_sorted.penetration, width=width, label=f'Mean Value = {penetration_df_sorted.penetration.mean():.1f} %')
        # for rect in bar_1:
        #   height = rect.get_height()
        #   ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
        ax.set_xticks(tsd_ticks)
        ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
        ax.set_ylabel('Penetration [%]')
        ax.set_xlabel('Poly CID')
        ax.set_ylim(0, max_hight)
        ax.legend(loc='upper left')
        plt.title(f'Sorted statistic penetration from {str(self.startdate_sim).split(" ")[0]} to {str(self.stopdate_sim).split(" ")[0]}\n viasat/sim')
        outname = os.path.join(self.save_penetrazione, f'sorted_penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png')
        fig.savefig(outname, dpi=150)
        print(f'  Image saved in {outname}')
        plt.clf()
        plt.close()

        # Log Scale
        log_penetration_df['round_value'] = (round(log_penetration_df.log_penetration, 0)).astype(int)
        fig, axh = plt.subplots(1, 1,figsize=(w,h), dpi=d)
        log_penetration_df['round_value'].value_counts().plot(kind='bar', rot=0, width=.5)

        axh.set_xlabel(f'Log scale')
        axh.set_ylabel("Occurencies")
        axh.yaxis.grid(True, linestyle='-')
        plt.title(f"Log Scale penetration distribution")
        outname2 = os.path.join(self.save_penetrazione, f'histlog_penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png')
        fig.savefig(outname2, dpi=150)
        print(f'  Image saved in {outname2}')
        plt.clf()
        plt.close()



        counts = log_penetration_df['round_value'].value_counts().sort_index()

        # define bins of interest and extract counts
        bins_interest = [-1, -2, -3]
        counts_filtered = counts.reindex(bins_interest).fillna(0).astype(int)

        # group the 'other' bins (0 and -4)
        other_bins = [0, -4]
        other_count = counts.reindex(other_bins).fillna(0).sum().astype(int)
        counts_filtered['others'] = other_count

        total_count = counts_filtered.sum()

        label_map = {
            -1: r'$\eta \sim 10^{-1}$',
            -2: r'$\eta \sim 10^{-2}$',
            -3: r'$\eta \sim 10^{-3}$',
            'others': 'others'
        }
        display_labels = [label_map[idx] for idx in counts_filtered.index]


        # plot pie chart with custom colors
        fig, axp = plt.subplots(figsize=(12, 12), dpi=d)
        axp.pie(
            counts_filtered.values,
            labels=display_labels,
            autopct='%1.1f%%',
            startangle=90,
            counterclock=False,
            colors=['yellow', 'red', 'blue', 'grey'],
            wedgeprops={'edgecolor': 'black', 'linewidth': 1},
            textprops={'fontsize': 20}

        )
        axp.set_title(f"Log Penetration Distribution (Pie Chart) — total={total_count}")
        outname3 = os.path.join(
            self.save_penetrazione,
            f'pie_penetrazione_log_{self.startdate_sim.date().strftime("%Y%m%d")}_'
            f'{self.stopdate_sim.date().strftime("%Y%m%d")}.png'
        )
        fig.savefig(outname3, dpi=150)
        print(f'  Image saved in {outname3}')
        plt.clf()
        plt.close()


        # Boxplot of penetration percentage by log10 bins
        import seaborn as sns
        df_bp = pd.DataFrame({
            'penetration': self.penetrazione_df['penetration'],
            'bin': log_penetration_df['round_value'].map({-1:r'$10^{-1}$', -2:r'$10^{-2}$', -3:r'$10^{-3}$', 0:'others', -4:'others'})
        })
        fig, axbp = plt.subplots(figsize=(12,10), dpi=d)
        sns.boxplot(
            x='bin',
            y='penetration',
            data=df_bp,
            palette=['yellow','red','black','grey'],
            order=[r'$10^{-1}$',r'$10^{-2}$',r'$10^{-3}$','others'],
            ax=axbp
        )
        # axbp.set_title('Penetration % Distribution by Log10 Bins')
        axbp.set_xlabel(r"$\log_{10}(\eta)$ Bins", fontsize=20)
        axbp.set_ylabel('Penetration [%]', fontsize=20)
        out_bp = os.path.join(self.save_penetrazione, f'boxplot_penetrazione_by_bin_{self.startdate_sim.date().strftime("%Y%m%d")}_{self.stopdate_sim.date().strftime("%Y%m%d")}.png')
        save_plot(fig, out_bp)

        # existing histogram and ECDF follow...
        # after you have log_penetration_df
        fig, ax = plt.subplots(figsize=(12,10), dpi=d)
        sns.histplot(
            log_penetration_df['log_penetration'],
            bins=20,
            kde=True,
            color='C2',
            ax=ax
        )
        # ax.set_title(r"Distribution of $\log_{10}(\eta)$")
        ax.set_xlabel(r"$\log_{10}(\eta)$")
        ax.set_ylabel("Number of polylines")
        ax.grid(True, linestyle=":")
        out = os.path.join(self.save_penetrazione, f"kde_log_pen_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png")
        save_plot(fig, out)

        fig, ax = plt.subplots(figsize=(12,12), dpi=d)
        sns.ecdfplot(
            data=log_penetration_df['log_penetration'],
            stat='proportion',
            ax=ax
        )
        # ax.set_title(r"ECDF of $\log_{10}(\eta)$")
        ax.set_xlabel(r"$\log_{10}(\eta)$")
        ax.set_ylabel("Cumulative fraction of polylines")
        ax.grid(True, linestyle=":")
        out = os.path.join(self.save_penetrazione, f"ecdf_log_pen_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png")
        save_plot(fig, out)

        print(f"-> Done - Statistical Penetration")

    # Generate quantile penetration map
    def geo_pen(self, carto):
        import matplotlib
        """Generate folium map with quantile-based penetration coloring."""
        print(f'->  Creating quantile penetration and Coils geoloc html file')
        merged = self.penetrazione_df.join(carto.geometry)
        merged = merged[merged.geometry.notnull()]

        merged['cid'] = merged.index
        quantiles_val = [0.0, 0.20, 0.40, 0.60, 0.80, 0.90, 1.0]
        quantiles = self.penetrazione_df.penetration.quantile(quantiles_val).to_list()
        bins = [float(q) for q in quantiles]

        cmap = cm.get_cmap('seismic', len(bins)-1)
        rgb_scale = cmap(quantiles_val)
        color_scale = [rgb2hex(r) for r in rgb_scale]
        color_scale = color_scale[:-1]
        default_color = color_scale[1]
        map_col_quantil={}
        for i in np.arange(0, len(color_scale)):
            label = f'{quantiles_val[i]} < q <= {quantiles_val[i+1]}'
            map_col_quantil[color_scale[i]]=label

        list_color = pd.cut(merged.penetration, bins=bins, labels=color_scale)

        merged['color'] = list_color.to_list()
        merged['color'] = merged['color'].fillna(default_color)
        merged['quantile'] = [map_col_quantil[i] for i in merged.color]

        merged.sort_values(by='quantile', inplace=True)

        m = folium.Map(location=self.center_coords, control_scale=True)
        import warnings
        warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)

        layerlabel = '<span style="color: {col};">{txt}</span>'
        for qval, grp in merged.groupby('quantile'):
            col = grp.color.to_list()[0]
            flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'{qval}'))
            for i, row in grp.iterrows():
                coords = list(row.geometry.coords)
                start_coord = coords[0]
                end_coord   = coords[-1]
                begin = (str(start_coord).split(' ',1)[1])[1:-1]
                begin = begin.split(' ')
                begin = '(' + ' '.join(reversed(begin)) + ')'

                end = (str(end_coord).split(' ',1)[1])[1:-1]
                end = end.split(' ')
                end = '(' + ' '.join(reversed(end)) + ')'

                pol = folium.PolyLine(
                    locations=[ [lat,lon] for lon,lat in row.geometry.coords],
                    fill_color=col,
                    color=col,
                    popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></br>Penetrazione Statistica: <b>{round(row.penetration, 2)} %</b></p>', show=False, sticky=True),
                )
                flayer_sel.add_child(pol)
            m.add_child(flayer_sel)
        coils_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'er_barriers.csv')
        coils = pd.read_csv(coils_file, sep=';')
        dir_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'coils-dir-mapping_template_0.50.csv')
        dirs = pd.read_csv(dir_file, sep=';')
        coils_yep = coils[ coils.Description.isin(dirs.coil_id.values) ]
        coils_yep = coils_yep.loc[coils_yep.PRO =='FO']
        flayer_coils = folium.FeatureGroup(name=layerlabel.format(col='blue', txt='selected coil'))
        for cid, row in coils_yep.iterrows():
            pt = folium.CircleMarker(
                location=[row.Lat, row.Lon],
                radius=5,
                fill_color='blue',
                color='blue',
                popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
            )
            flayer_coils.add_child(pt)
        m.add_child(flayer_coils)
        coils_nope = coils[ ~coils.Description.isin(dirs.coil_id.values) ]
        coils_nope = coils_nope.loc[coils_nope.PRO =='FO']

        flayer_nope = folium.FeatureGroup(name=layerlabel.format(col='red', txt='coil'))
        for cid, row in coils_nope.iterrows():
            pt = folium.CircleMarker(
                location=[row.Lat, row.Lon],
                radius=5,
                fill_color='red',
                color='red',
                popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
            )
            flayer_nope.add_child(pt)
        m.add_child(flayer_nope)
        folium.map.LayerControl(collapsed=True).add_to(m)
        html_file = f'{self.save_penetrazione}/penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.html'
        m.save(html_file)
        print(f'File saved: {os.path.abspath(html_file)} ')
        print(f"->  Done quantile penetration html file")

    # Local anomalies detection
    def norm_analysis(self, test_mode):
        """Identify and plot local anomalies between simulation and Viasat data."""
        # Identify and plot local anomalies between Viasat and simulation series.
        print(f"->  Start local analysis")
        uniq_df = self.uniq_df.loc[:, (self.uniq_df != 0).any(axis=0)]
        viasat_df = self.viasat_df.copy()

        if len(uniq_df.columns) > 40: uniq_df = uniq_df.sample(10, axis=1)
        if test_mode:
            print('Test mode Enabled')
            poly_col = [23357, 23511, 23909, 31724, 31785, 32114, 32250, 32704, 32724, 32739, 33149, 33322, 33619, 33818, 33828, 34018]
            uniq_df = uniq_df[poly_col]
  
        for col in uniq_df.columns:
            uniq_norm = uniq_df[col]/uniq_df[col].sum()
            viasat_norm = viasat_df[col]/viasat_df[col].sum()

            diff_df = viasat_norm.copy().to_frame().rename(columns={col:"viasat_cnt"})
            diff_df['uniq_cnt'] = uniq_norm.values
            diff_df['perc_diff'] = (diff_df.uniq_cnt - diff_df.viasat_cnt) * 100
            y_limits = max(abs(diff_df.perc_diff)) + 2/100 * max(abs(diff_df.perc_diff))

            w, h, d = 12, 7, 150
            fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
            tsd = [ t for t in range(len(viasat_norm.index)) ]
            tusd = 1
            lusd = 1
            tsd_ticks = tsd[::tusd]
            tsd_lbl = [ t.strftime('%H:%M') for t in viasat_norm.index ]
            tsd_lbl = tsd_lbl[::lusd]
            ax = axs[0]
            ax.plot(tsd, uniq_norm, color='C0', label='Normalized sim mean data')
            ax.set_ylabel('Norm SIM', color="C0")
            ax.grid()
            ax.legend(loc='upper left')
            ax2=ax.twinx()
            ax2.plot(tsd, viasat_norm, '--', color="C1", label='Normalized VIASAT sum data')
            ax2.set_ylabel('Norm viasat', color="C1")
            ax2.legend(loc='upper right')

            ax1 = axs[1]
            ax1.plot(tsd, diff_df.perc_diff, color='k', label='Difference simulation - viasat data')
            ax1.set_ylabel('Percentage difference [%]', color="k")
            ax1.set_xlabel('Time (H:M:S)')
            ax1.set_xticks(tsd_ticks)
            ax1.set_xticklabels(tsd_lbl, rotation=45)
            ax1.set_ylim(-y_limits, y_limits)
            ax1.grid()
            ax1.legend(loc='upper left')

            string_save_text = str(self.startdate_sim).split(' ')[0].replace('-','') +  str(self.stopdate_sim).split(' ')[0].replace('-','')
            string_title_text = 'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
            plt.title(f'Poly cid {col} \n{string_title_text}')
            plt.tight_layout()

            single_save = f'{self.save_folder}/local_anomalies'
            if not os.path.exists(single_save): os.makedirs(single_save)

            outname = os.path.join(single_save, f'cid_{col}_{string_save_text}.png')
            fig.savefig(outname, dpi=150)
            print(f'Image saved in {outname}')
            plt.clf()
            plt.close()
        print(f"->  Done local analysis")

    # # ----------------------------
    # # Major Cluster Mapping
    # # ----------------------------
    def major_cluster(self, df, carto, outname):
        import joblib
        if outname == 'Log_':
            df['penetration'] = (round(df.log_penetration, 0)).astype(int)

        scaled_df = StandardScaler().fit_transform(df)
        kmeans_kwargs = {
        "init": "random",
        "n_init": 10,
        "random_state": 1,
        }

        sse = []
        for k in range(1, 11):
            kmeans = KMeans(n_clusters=k, **kmeans_kwargs)
            kmeans.fit(scaled_df)
            sse.append(kmeans.inertia_)

        plt.plot(range(1, 11), sse)
        plt.xticks(range(1, 11))
        plt.xlabel("Number of Major Clusters")
        plt.ylabel("SSE")
        plt.clf()
        plt.close()
        # plt.show()
        kmeans = KMeans(init="random", n_clusters=self.ncluster, n_init=10, random_state=1)
        kmeans.fit(scaled_df)
        df['cluster'] = kmeans.labels_

        merged = df.join(carto.geometry)
        merged = merged[merged.geometry.notnull()]

        merged['cid'] = merged.index

        n_cluster = sorted(list(merged.cluster.unique()))
        c_map = cm.get_cmap('gnuplot', len(n_cluster))
        rgb_scale = c_map(n_cluster)
        color_scale = [rgb2hex(r) for r in rgb_scale]
        cluster_col = dict(zip(n_cluster, color_scale))
        merged['color'] = merged.cluster.map(cluster_col)

        if outname == 'Log_':
            self.log_cluster_df = merged.copy()
        else:
            self.cluster_df = merged.copy()

        m = folium.Map(location=center_coords, control_scale=True)
        import warnings
        warnings.filterwarnings("ignore")
        layerlabel = '<span style="color: {col};">{txt}</span>'
        for clus, grp in merged.groupby('cluster'):
            col = grp.color.to_list()[0]
            flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'Cluster n°{clus+1}'))
            for i, row in grp.iterrows():
                coords = list(row.geometry.coords)
                start_coord = coords[0]
                end_coord   = coords[-1]
                begin = (str(start_coord).split(' ',1)[1])[1:-1]
                begin = begin.split(' ')
                begin = '(' + ' '.join(reversed(begin)) + ')'

                end = (str(end_coord).split(' ',1)[1])[1:-1]
                end = end.split(' ')
                end = '(' + ' '.join(reversed(end)) + ')'
                if outname == 'Log_':
                    pol = folium.PolyLine(
                        locations=[ [lat,lon] for lon,lat in row.geometry.coords],
                        fill_color=col,
                        color=col,
                        popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></br>Log Scale - Stat Penetration: <b>{round(row.penetration, 2)}</b></p>', show=False, sticky=True),
                    )
                else:
                    pol = folium.PolyLine(
                    locations=[ [lat,lon] for lon,lat in row.geometry.coords],
                    fill_color=col,
                    color=col,
                    popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></br>Percentage - Stat Penetration: <b>{round(row.penetration, 2)} %</b></p>', show=False, sticky=True),
                )
                flayer_sel.add_child(pol)
            m.add_child(flayer_sel)
        folium.map.LayerControl(collapsed=True).add_to(m)

        if outname == 'Log_':
            html_file = f'{self.save_penetrazione}/log_Cluster_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.html'
        else:
            html_file = f'{self.save_penetrazione}/cluster_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.html'
        m.save(html_file)
        print(f'File saved in {os.path.abspath(html_file)}')

        date_str = f"{self.startdate_sim:%Y%m%d}_{self.stopdate_sim:%Y%m%d}"
        run_dir = os.path.join(self.save_penetrazione, outname.strip('_'), date_str)
        os.makedirs(run_dir, exist_ok=True)

        if not isinstance(merged, gpd.GeoDataFrame):
            merged = gpd.GeoDataFrame(merged, geometry='geometry', crs=carto.crs)

        gpkg_path = os.path.join(run_dir, f"{outname}clusters.gpkg")
        merged.to_file(gpkg_path, layer="clusters", driver="GPKG")
        merged.drop(columns='geometry').to_csv(os.path.join(run_dir, f"{outname}clusters.csv"), index=False)

        # 9. save KMeans model
        model_path = os.path.join(run_dir, f"{outname}kmeans_model.pkl")
        joblib.dump(kmeans, model_path)

        # 10. save scaled array
        scaled_path = os.path.join(run_dir, f"{outname}scaled.npy")
        np.save(scaled_path, scaled_df)

        # 11. save SSE curve (JSON + CSV)
        sse_json = os.path.join(run_dir, f"{outname}sse_curve.json")
        with open(sse_json, 'w') as f:
            json.dump(sse, f)
        pd.DataFrame({'k': list(range(1, len(sse)+1)), 'sse': sse}) \
        .to_csv(os.path.join(run_dir, f"{outname}sse_curve.csv"), index=False)

        # 12. final prints
        print(f"→ GeoPackage   to {os.path.abspath(gpkg_path)}")
        print(f"→ Model        to {os.path.abspath(model_path)}")
        print(f"→ Scaled data  to {os.path.abspath(scaled_path)}")
        print(f"→ SSE JSON     to {os.path.abspath(sse_json)}")

        print(f"->  Done Major Cluster Mapping")


    # # Cluster analysis for detailed per-cluster comparison
    def cluster_analysis(self, outtype):
        """Perform cluster-level comparison and generate mean/std and L2 plots."""
        # Perform cluster-level comparison and generate mean/std and L2 plots.
        print("-> Start Cluster Analysis")
        from scipy.stats import norm
        cluster_dict = dict()
        if outtype == 'Log_':
            for cluster_num, single_cluster in self.log_cluster_df.groupby('cluster'):
                cluster_dict[cluster_num] = single_cluster.index.values.tolist()
        else:
            for cluster_num, single_cluster in self.cluster_df.groupby('cluster'):
                cluster_dict[cluster_num] = single_cluster.index.values.tolist()

        self.cluster_dict = cluster_dict
        inverse = { v: k for k, l in cluster_dict.items() for v in l }

        daily_sum = self.uniq_df.sum().reset_index()
        daily_sum = daily_sum.rename(columns={0: "sim_cnt"})
        viasat_daily_sum = self.viasat_df.sum().reset_index()
        viasat_daily_sum = viasat_daily_sum.rename(columns={0: "viasat_counter"})
        viasat_daily_cnt = pd.Series(viasat_daily_sum.viasat_counter.values,index=viasat_daily_sum.cid).to_dict()

        daily_sum['viasat_cnt'] = daily_sum['poly_cid'].map(viasat_daily_cnt)
        daily_sum['cluster'] = daily_sum['poly_cid'].map(inverse)
        daily_sum["ratio"] = daily_sum['viasat_cnt'] / daily_sum['sim_cnt']
        daily_sum.set_index('poly_cid', inplace=True)

        dendrogram = self.dendrogram(self.uniq_df, cluster_dict)
        exit()

    #     for key, values in cluster_dict.items():
    #         uniq_df = self.uniq_df[values]
    #         uniq_df = uniq_df.loc[:, (self.uniq_df != 0).any(axis=0)]
    #         viasat_df = self.viasat_df.copy()

    #         uniq_scaled_list = []
    #         viasat_scaled_list = []

    #         if outtype == 'Log_':
    #             for col in uniq_df.columns:
    #                 uniq_norm = uniq_df[col]/uniq_df[col].sum()
    #                 viasat_norm = viasat_df[col]/viasat_df[col].sum()
    #                 uniq_scaled_list.append(uniq_norm)
    #                 viasat_scaled_list.append(viasat_norm)
    #             uniq_scaled_df = pd.DataFrame(uniq_scaled_list).T
    #             viasat_scaled_df = pd.DataFrame(viasat_scaled_list).T

    #             viasat_scaled_df = viasat_scaled_df[uniq_scaled_df.columns]
    #             df_1_stat = pd.DataFrame(index=uniq_scaled_df.index, columns=['media', 'std_dev'])  
    #             df_1_stat['media'] = uniq_scaled_df.mean(axis=1)
    #             df_1_stat['std_dev'] = uniq_scaled_df.std(axis=1)

    #             df_2_stat = pd.DataFrame(index=viasat_scaled_df.index, columns=['media', 'std_dev'])  
    #             df_2_stat['media'] = viasat_scaled_df.mean(axis=1)
    #             df_2_stat['std_dev'] = viasat_scaled_df.std(axis=1)
                
    #             uniq_stat = pd.concat([uniq_scaled_df,df_1_stat], axis=1).reset_index()
    #             uniq_stat = uniq_stat.drop(columns='time_index')
    #             uniq_stat.set_index(df_2_stat.index, inplace=True)

    #             viasat_stat = pd.concat([viasat_scaled_df,df_2_stat], axis=1).reset_index()
    #             viasat_stat = viasat_stat.drop(columns='time_hour')
    #             viasat_stat.set_index(df_2_stat.index, inplace=True)

    #             def euc_dist(first, second):
    #                 euc_dict = dict()
    #                 for col in first.columns:
    #                     first_df = first[col]
    #                     second_df = second[col]
    #                     euc_dict[col] = np.sqrt(np.sum((first_df - second_df) ** 2))
    #                 return euc_dict

    #             euclidean_dict = euc_dist(uniq_stat,viasat_stat)
    #             names = list(euclidean_dict.keys())
    #             values = list(euclidean_dict.values())

    #             plt.bar(range(len(names)), values, width = .5, color='b')
    #             string_title_text = 'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
    #             plt.title(f'Cluster {key} - Distribution of euclidean distances\n{string_title_text}')
    #             plt.xlabel("Polylines")

    #             string_save_text = str(self.startdate_sim).split(' ')[0].replace('-','') +  str(self.stopdate_sim).split(' ')[0].replace('-','')
    #             cluster_la = f'{self.save_folder}/local_anomalies'
    #             if not os.path.exists(cluster_la): os.makedirs(cluster_la)
    #             cluster_dist = f'{cluster_la}/log_cluster_distances'
    #             if not os.path.exists(cluster_dist): os.makedirs(cluster_dist)
    #             outname_dist = os.path.join(cluster_dist, f'log_cluster_{key}_distance_{string_save_text}.png')
    #             plt.savefig(outname_dist, dpi=150)
    #             print(f'  Image saved in {outname_dist}')
    #             plt.close()
    #             plt.clf()

    #             w, h, d = 12, 7, 150
    #             fig, axa=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
    #             tsd = [ t for t in range(len(df_1_stat.index)) ]
    #             tusd = 1
    #             lusd = 1
    #             tsd_ticks = tsd[::tusd]
    #             tsd_lbl = [ t.strftime('%H:%M') for t in df_2_stat.index ]
    #             tsd_lbl = tsd_lbl[::lusd]
    #             ax = axa[0]
    #             ax.plot(tsd, df_1_stat.media, color='k', label=f'Sim Mean in cluster #{key}')
    #             ax.fill_between(tsd, df_1_stat.media - df_1_stat.std_dev, df_1_stat.media + df_1_stat.std_dev, alpha = 0.4, label=f'Std Sim #{key}')
                
    #             ax.plot(tsd, df_2_stat.media, '-',color='b', label=f'Viasat Mean in cluster #{key}')
    #             ax.fill_between(tsd, df_2_stat.media - df_2_stat.std_dev, df_2_stat.media + df_2_stat.std_dev, color='yellow', alpha = 0.2, label=f'Std Viasat #{key}')
    #             ax.set_ylabel('Norm counter', color="k")
    #             ax.grid()
    #             ax.legend(loc='upper left')

    #             df_reset = df_1_stat[['media']].reset_index()
    #             df_reset['time_hour'] = df_2_stat.index
    #             df_reset = df_reset.drop(columns="time_index")
    #             df_reset.set_index(df_reset.time_hour, inplace=True)
    #             df_l2 = pd.concat([df_reset['media'], df_2_stat['media']], axis=1, keys=['media_uniq', 'media_viasat'])
    #             df_l2['euc_dist'] = np.sqrt((df_l2.media_uniq - df_l2.media_viasat) ** 2)

    #             ax = axa[1]
    #             ax.bar(tsd, df_l2.euc_dist, color='blue', label=f'Euclidean distance in cluster #{key}')
    #             ax.set_ylabel('Euclidean distance', color="k")
    #             # ax.grid()
    #             ax.legend(loc='upper left')
    #             ax.set_xticks(tsd_ticks)
    #             ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
    #             ax.set_ylim(0,.04)
    #             ax.set_xlabel('Datetime')

    #             plt.suptitle(f"Cluster # {key}\n{string_title_text}")
    #             cluster_mean_save = f'{cluster_la}/log_cluster_mean'
    #             if not os.path.exists(cluster_mean_save): os.makedirs(cluster_mean_save)
    #             outname = os.path.join(cluster_mean_save, f'log_cluster_mean_{key}_{string_save_text}.png')
    #             plt.savefig(outname, dpi=150)
    #             # plt.show()
    #             plt.clf()
    #             plt.close()
    #             print(f'  Image saved in {outname}')


    #         if len(uniq_df.columns) > 40: uniq_df = uniq_df.sample(10, axis=1)

    #         for col in uniq_df.columns:
    #             uniq_norm = uniq_df[col]/uniq_df[col].sum()
    #             viasat_norm = viasat_df[col]/viasat_df[col].sum()

    #             diff_df = viasat_norm.copy().to_frame().rename(columns={col:"viasat_cnt"})
    #             diff_df['uniq_cnt'] = uniq_norm.values
    #             diff_df['perc_diff'] = (diff_df.uniq_cnt - diff_df.viasat_cnt) * 100
    #             y_limits = max(abs(diff_df.perc_diff)) + 2/100 * max(abs(diff_df.perc_diff))

    #             w, h, d = 12, 7, 150
    #             fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
    #             tsd = [ t for t in range(len(viasat_norm.index)) ]
    #             tusd = 1
    #             lusd = 1
    #             tsd_ticks = tsd[::tusd]
    #             tsd_lbl = [ t.strftime('%H:%M') for t in viasat_norm.index ]
    #             tsd_lbl = tsd_lbl[::lusd]
    #             ax = axs[0]
    #             ax.plot(tsd, uniq_norm, color='C0', label='Normalized sim mean data')
    #             ax.set_ylabel('Norm SIM', color="C0")
    #             ax.grid()
    #             ax.legend(loc='upper left')
    #             ax2=ax.twinx()
    #             ax2.plot(tsd, viasat_norm, '--', color="C1", label='Normalized VIASAT sum data')
    #             ax2.set_ylabel('Norm viasat', color="C1")
    #             ax2.legend(loc='upper right')

    #             ax1 = axs[1]
    #             ax1.plot(tsd, diff_df.perc_diff, color='k', label='Difference simulation - viasat data')
    #             ax1.set_ylabel('Percentage difference [%]', color="k")
    #             ax1.set_xlabel('Time (H:M:S)')
    #             ax1.set_xticks(tsd_ticks)
    #             ax1.set_xticklabels(tsd_lbl, rotation=45)
    #             ax1.set_ylim(-y_limits, y_limits)
    #             ax1.grid()
    #             ax1.legend(loc='upper left')

    #             string_save_text = str(self.startdate_sim).split(' ')[0].replace('-','') +  str(self.stopdate_sim).split(' ')[0].replace('-','')
    #             string_title_text = 'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
    #             if outtype == 'Log_':
    #                 plt.title(f'Log Cluster {key}\nPoly cid {col} \n{string_title_text}')
    #             else:
    #                 plt.title(f'Cluster {key}\nPoly cid {col} \n{string_title_text}')
    #             plt.tight_layout()

    #             single_save = f'{self.save_folder}/cluster_analysis'
    #             if not os.path.exists(single_save): os.makedirs(single_save)
    #             if outtype == 'Log_':
    #                 cluster_save = f'{single_save}/log_cluster_{key}'
    #                 if not os.path.exists(cluster_save): os.makedirs(cluster_save)
    #                 outname = os.path.join(cluster_save, f'log_cluster_{key}_cid_{col}_{string_save_text}.png')
    #             else:
    #                 cluster_save = f'{single_save}/cluster_{key}'
    #                 if not os.path.exists(cluster_save): os.makedirs(cluster_save)
    #                 outname = os.path.join(cluster_save, f'cluster_{key}_cid_{col}_{string_save_text}.png')

    #             fig.savefig(outname, dpi=150)

    #             print(f'  Image saved in {outname}')
    #             plt.clf()
    #             plt.close()    
    #     print("-> Done - Cluster Analysis")

    # ----------------------------
    # Dendrogram
    # ----------------------------

    def dendrogram(self, df, dict_cluster):
        from scipy.spatial.distance import pdist, squareform
        import scipy.cluster.hierarchy as sch
        """Create and save hierarchical clustering dendrogram of your polylines."""
        # Parameters
        clus_major = 0
        dist_metric = 'euclidean'
        linkage_method = 'ward'
        normalize = False   # set True if you want to z-score each series first

        #—– Prepare save folder
        out_dir = os.path.join(self.save_folder, "cluster_analysis")
        os.makedirs(out_dir, exist_ok=True)

        #—– Build new_df: index=time, columns=polyline IDs
        df2 = df.reset_index().set_index('time_index')
        df2 = df2.loc[:, (df2 != 0).any(axis=0)]
        poly_ids = dict_cluster[clus_major]
        new_df = df2[poly_ids].copy()

        print(new_df)

        normalize = False
        #—– (Optional) normalize each column
        if normalize:
            new_df = (new_df - new_df.mean()) / new_df.std()

        #—– Compute linkage on the transposed data matrix
        #    rows = polylines, columns = time-points
        data_matrix = new_df.T.values
        Z = sch.linkage(data_matrix,
                        method=linkage_method,
                        metric=dist_metric)

        #—– Plot dendrogram
        plt.figure(figsize=(12, 8), dpi=150)
        sch.dendrogram(Z,
                    labels=new_df.columns,
                    leaf_rotation=90,
                    leaf_font_size=7,
                    color_threshold=None)   # color_threshold=None means no automatic color-cut
        
        # plt.set_xticks([])             # no tick *locations*
        plt.xticks([])
        # plt.title(f"HCA dendrogram (method={linkage_method}, metric={dist_metric})")
        plt.ylabel(r"Ward linkage distance [($N_{sim}/h)^2$]")
        plt.xlabel("Polyline ID")
        plt.tight_layout()
        out_path = os.path.join(out_dir, "inner_dendrogram.png")
        plt.savefig(out_path)
        plt.close()

        print(f"-> Dendrogram saved to {out_path}")

        exit()

        if normalize: cut_distance = 0.4 
        else: cut_distance = 17000 

        clusterlist = sch.fcluster(linkg, cut_distance, criterion='distance')-1
        df_cluster = pd.DataFrame({'cid':tags,'cluster':clusterlist})
        nclusters = len(np.unique(clusterlist))
        df_cluster.set_index(df_cluster.cid, inplace=True)

        merged = df_cluster.join(self.carto.geometry)
        merged['cid'] = merged.index

        nclusters = sorted(list(merged.cluster.unique()))
        c_map = cm.get_cmap('gnuplot', len(nclusters))
        rgb_scale = c_map(nclusters)
        color_scale = [rgb2hex(r) for r in rgb_scale]
        cluster_col = dict(zip(nclusters, color_scale))
        merged['color'] = merged.cluster.map(cluster_col)

        m = folium.Map(location=self.center_coords, control_scale=True)
        import warnings
        warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)
        layerlabel = '<span style="color: {col};">{txt}</span>'
        for clus, grp in merged.groupby('cluster'):
            col = grp.color.to_list()[0]
            flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'Cluster num {clus}'))
            for i, row in grp.iterrows():
                start_coord, end_coord = row.geometry.boundary
                begin = (str(start_coord).split(' ',1)[1])[1:-1]
                begin = begin.split(' ')
                begin = '(' + ' '.join(reversed(begin)) + ')'

                end = (str(end_coord).split(' ',1)[1])[1:-1]
                end = end.split(' ')
                end = '(' + ' '.join(reversed(end)) + ')'
                pol = folium.PolyLine(
                    locations=[ [lat,lon] for lon,lat in row.geometry.coords],
                    fill_color=col,
                    color=col,
                    popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></p>', show=False, sticky=True),
                )
                flayer_sel.add_child(pol)
            m.add_child(flayer_sel)
        folium.map.LayerControl(collapsed=True).add_to(m)
        set_date_save = f'{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}'
        html_file = f'{single_save}/inner_cluster_{clus_major}_{set_date_save}.html'
        m.save(html_file)
        print(f'   File saved: {os.path.abspath(html_file)} ')

    # # Smooth data using FFT convolution
    # def smooth(self, df):
    #     """Apply centered moving average smoothing using FFT convolution."""
    #     # Apply centered moving average smoothing using FFT convolution.
    #     dfsm = pd.DataFrame([], columns=df.columns, index=df.index)
    #     def box_centered_kernel(tot_len, box_len):
    #       pad_len = tot_len - box_len
    #       kern = np.concatenate([
    #       np.zeros((pad_len // 2)),
    #       np.ones((box_len)) / box_len,
    #       np.zeros((pad_len - pad_len // 2))# for odd box_len
    #       ])
    #       return kern

    #     ma_size = 5 # running average idx interval from time in seconds
    #     kern = box_centered_kernel(len(df), ma_size)
    #     for c in df.columns:
    #       conv = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( df[c].values ) * np.fft.fft(kern) )))
    #       dfsm[c] = conv
    #     return dfsm

    #         sim_series = df[col]
    #         via_series = df2[col]
    #         # scale Viasat to simulation total
    #         factor = via_series.sum() / sim_series.sum() if sim_series.sum() != 0 else 1
    #         via_scaled = via_series / factor
    #         # compute difference array
    #         if norm_flag:
    #             arr1 = self.norm(sim_series.values)
    #             arr2 = self.norm(via_scaled.values)
    #         else:
    #             arr1 = sim_series.values
    #             arr2 = via_scaled.values
    #         l2_diff = np.sqrt((arr1 - arr2) ** 2)
    #         # plot selected polylines
    #         if good_list and col in good_list:
    #             fig, ax = plt.subplots()
    #             ax.plot(arr1, label='sim')
    #             ax.plot(arr2, label='viasat')
    #             ax.set_title(f'CID {col} L2 difference')
    #             ax.legend()
    #             # save and clear
    #             save_plot(fig, f'{col}_l2_diff.png')
    #             plt.clf()




# ----------------------------
# CLI Entry Point
# ----------------------------
# Parse CLI arguments and run the full analysis pipeline.
def main():
    """Parse arguments and execute the analysis workflow."""

    conf_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'article', 'vars', 'conf.json')

    parser = argparse.ArgumentParser(description="Viasat vs simulation analysis")
    parser.add_argument('-c', '--cfg', help='Path to JSON config file', default= conf_path)
    parser.add_argument('-l', '--local', choices=['montagna', 'imola', 'faenza', 'forli', 'cesena'], help='Select area')
    parser.add_argument('-p', '--polycid', nargs='+', default=[], help='List of poly_cid to filter')
    parser.add_argument('-t', '--test_mode', action='store_true', help='Enable test mode')
    args = parser.parse_args()

    # Load configuration
    with open(args.cfg) as f:
        config = json.load(f)

    year = config.get('year')
    viasat_file = get_viasat_filepath(year)

    # Prepare output directories
    base_out = os.path.join(config['outdir'], year)
    ensure_dir(base_out)
    save_folder = os.path.join(base_out, args.local or 'global')
    ensure_dir(save_folder)
    save_penetrazione = os.path.join(save_folder, 'penetrazione')
    ensure_dir(save_penetrazione)

    # Load cartography data
    carto = gpd.read_file(config['carto']).set_index('poly_cid')
    center_coords = config.get('center_coords', [44.176684, 12.151647])

    # Initialize analysis
    analysis = ViasatAnalysis()
    # Pass output directories and map center to analysis
    analysis.center_coords = center_coords
    analysis.save_folder = save_folder
    analysis.save_penetrazione = save_penetrazione
    viasat_df = analysis.viasat_builder(viasat_file)
    uniq_df = analysis.uniq_builder(args.polycid or config['city'].get(args.local, []), year)

    analysis.penetrazione(carto)
    try:
        analysis.geo_pen(carto)
    except Exception as e:
        print(f"Geo plot skipped due to: {e}")
    analysis.norm_analysis(args.test_mode)
    if not args.local:
        analysis.cluster_analysis('Log_')
        analysis.L2_diff()


if __name__ == '__main__':
    center_coords = [44.176684, 12.151647] # Default center coordinates
    main()
