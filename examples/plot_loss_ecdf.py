import pandas as pd
import matplotlib.pyplot as plt
from numpy import max, std, ceil, arange, sort, Inf
import numpy as np
from statsmodels.distributions.empirical_distribution import ECDF
import argparse
import os
from pandas.api.types import is_string_dtype
from itertools import cycle
parser = argparse.ArgumentParser(
    description='Plotting ECDF')
parser.add_argument('--slice', type=str,
                    help='plot from a time slice of the whold data. [t1, t2]',
                    default='all')
parser.add_argument('--with-opf', action="store_true",
                    help='plot OPF data as well')
parser.add_argument('--with-pi', action="store_true",
                    help='plot PI data as well')
parser.add_argument('--results', type=str, 
                    default='./raw')
parser.add_argument('--runs', nargs='+', type=int,
                    default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
parser.add_argument('--losses', nargs='+', type=int,
                    default=[0, 5, 10, 15, 20, 40, 50, 60])

args = parser.parse_args()
losses = args.losses
runs = args.runs
results = args.results
tslice = args.slice
with_pi = args.with_pi
with_opf = args.with_opf

if tslice != 'all':
    tslice = [float(i) for i in args.slice.split(',')]
    if len(tslice) == 1:
        tslice.append(Inf)
else:
    tslice = [0, Inf]

assert len(tslice) == 2

width=0.4

def get_voltages(data, slice: list = [0, Inf]):
    assert len(slice) <=2
    if is_string_dtype(data[0]):
        data.drop(data[data[0].str.contains('LOAD')].index, inplace=True)
        data[0]=data[0].str.replace('VOLTAGE ', '')
        data[0]=pd.to_numeric(data[0],errors='coerce')
        data.reset_index(drop=True, inplace=True)
    data[0]=data[0]-data.loc[0,0]
    # data[0]=data[0].apply(ceil)
    # data.drop_duplicates(subset=[0,1], inplace=True, keep='last')
    # data.reset_index(drop=True, inplace=True)

    data.drop(data[data[0]>287].index, inplace=True)
    data.drop(data[data[0]==0].index, inplace=True)
    data.reset_index(drop=True, inplace=True)
    print("slicing for opf {}% loss: {}".format(j, i))
    # slicing
    data.drop(data[data[0]<tslice[0]].index, inplace=True)
    data.reset_index(drop=True, inplace=True)
    data.drop(data[data[0]>tslice[1]].index, inplace=True)
    data.reset_index(drop=True, inplace=True)
    return data[2].tolist()

data_opf: dict = {}
data_pi: dict = {}
for j in losses:
    data_opf[j] = []
    data_pi[j] = []
    for i in runs:
        try:
            if with_opf:
                print("reading for opf {}% loss: {}".format(j, i))
                data = pd.read_csv(os.path.join(results, 'sim_opf_{}loss_5.{}.log'.format(j,i)), header=None, delimiter='\t')
                data_opf[j] = data_opf[j] + get_voltages(data)
            if with_pi:
                print("reading for pi {}% loss: {}".format(j, i))
                data = pd.read_csv(os.path.join(results, 'sim_pi_{}loss_5.{}.log'.format(j,i)), header=None, delimiter='\t')
                data_pi[j] = data_pi[j] + get_voltages(data)
        except Exception as e:
            print(e)

print("reading for no control")
data = pd.read_csv(os.path.join(results, 'sim_no_control.log'), header=None, delimiter='\t')
data_pv =  get_voltages(data)
ecdf_pv = ECDF(data_pv)

fig = plt.figure()
ax1 = fig.add_subplot(121)
ax2 = fig.add_subplot(122)
lines = ["-","--","-.",":"]
linecycler = cycle(lines)
bbox = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
size=15
i=0
for j in losses:
    if with_opf:
        ecdf_opf = ECDF(data_opf[j])
        x = [i for i in arange(0.98, max(data_opf[j]), 0.001)]
        y = ecdf_opf(x)
        ax1.plot(x, y, next(linecycler), label="%d%% loss"%j)
        ax1.plot([1.01], [ecdf_opf(1.01)], marker='d', color='black')
        ax1.plot([1.01, 1.01], [0, 1], '--', color='black')
        ax1.annotate("OPF: %0.2f"%ecdf_opf(1.01), xy=(1.01, ecdf_opf(1.01)), 
                    xycoords='data', xytext=(1.04, 0.8-i/10), textcoords='data', 
                    bbox=bbox, size=size, #fontsize=8,
                    arrowprops=dict(arrowstyle="->"))

        ax1.plot([1.0], [ecdf_opf(1.0)], marker='d', color='black')
        ax1.annotate("OPF: %0.2f"%ecdf_opf(1.0), xy=(1.0, ecdf_opf(1.0)), 
                    xycoords='data', xytext=(1.04, 0.6-i/10), textcoords='data',  
                    bbox=bbox, size=size, #fontsize=8,
                    arrowprops=dict(arrowstyle="->"))
        # ax1.title.set_text('OPF Control')
    if with_pi:
        ecdf_pi = ECDF(data_pi[j])
        x = [i for i in arange(0.98, max(data_pi[j]), 0.001)]
        y = ecdf_pi(x)
        ax2.plot(x, y, next(linecycler), label="%d%% loss"%j)
        ax2.plot([1.01], [ecdf_pi(1.01)], marker='d', color='black')
        ax2.plot([1.01, 1.01], [0, 1], '--', color='black')
        ax2.annotate("PI: %0.2f"%ecdf_pi(1.01), xy=(1.01, ecdf_pi(1.01)), 
                    xycoords='data', xytext=(1.04, 0.8-i/10), textcoords='data', 
                    bbox=bbox, size=size, #fontsize=8,
                    arrowprops=dict(arrowstyle="->"))


        ax2.plot([1.0], sort([ecdf_pi(1.0)]), marker='d', color='black')
        ax2.annotate("PI: %0.2f"%ecdf_pi(1.0), xy=(1.0, ecdf_pi(1.0)), 
                    xycoords='data', xytext=(1.04, 0.6-i/10), textcoords='data', 
                    bbox=bbox, size=size, #fontsize=8,
                    arrowprops=dict(arrowstyle="->"))
        # ax2.title.set_text('PI Control', fontsize=12)                    
    i=i+1

x = [i for i in arange(0.98, max(data_pv), 0.001)]
y = ecdf_pv(x)
for ax in [ax1, ax2]:
    ax.plot(x, y, color="red", label="No Control")
    ax.annotate("NC: %0.2f"%ecdf_pv(1.01), xy=(1.01, ecdf_pv(1.01)), 
                xycoords='data', xytext=(0.97, 0.6), textcoords='data',
                bbox=bbox, size=size, #fontsize=8,
                arrowprops=dict(arrowstyle="->"))
    ax.annotate("NC: %0.2f"%ecdf_pv(1.0), xy=(1.0, ecdf_pv(1.0)), 
                xycoords='data', xytext=(0.97, 0.4), textcoords='data',
                bbox=bbox, size=size, #fontsize=8,
                arrowprops=dict(arrowstyle="->"))
    ax.plot([1.01], [ecdf_pv(1.01)], marker='d', color='black')
    ax.plot([1.0], [ecdf_pv(1.0)], marker='d', color='black')
    ax.plot([1.0, 1.0], [0, 1], '--', color='black')
    ax.set_xticks([0.97, 1.01, 1.05])
    ax.set_xticklabels(["0.97", "1.01", "1.05"])
    ax.xaxis.set_tick_params(labelsize=15)
    ax.yaxis.set_tick_params(labelsize=15)
    ax.set_xlabel("vm (p.u.)", fontsize=20)
    ax.set_ylabel("ECDF", fontsize=20)
    ax.legend(fontsize=15, loc=1)

plt.tight_layout()
plt.savefig('ecdf_loss.png', dpi=600)
plt.show()