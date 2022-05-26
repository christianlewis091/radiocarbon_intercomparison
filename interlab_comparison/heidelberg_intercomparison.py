"""
Purpose:

We have two long-term record of 14C02 from the Southern Hemisphere (among some other shorter ones).
One is the Baring Head Record, from the GNS Rafter Radiocarbon Lab (measured by gas counting, then AMS)
Next is Ingeborg Levin and Sam Hammer's Tasmania Cape Grim CO2 record (measured by gas counting).
This script is meant to compare the differences between the datasets over time, to determine if
temporally consistent offsets exist, and if so, how to best correct them to create a harmonized background reference
dataset for future carbon cycle studies.

The script first imports and cleans the data, before using a CCGCRV Curve smoothing program to smooth through the data.
There is precedent for this procedure in the scientific literature following
https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/JD094iD06p08549 (Thoning et al., 1989): use of the CCGCRV
https://acp.copernicus.org/articles/17/14771/2017/ (Turnbull et al., 2017): use of CCGCRV in the Baring Head Record
https://gml.noaa.gov/ccgg/mbl/crvfit/crvfit.html: NOAA details about the CCGCRV curve smoothing.

A Monte Carlo simulation is used to determine errors on the CCGCRV smoothing data. These errors are important because
we will need them for comparison with other carbon cycle datasets, of course.

The file outputs a text file with the t-test results. However, it will keep adding to the file, so if you want a fresh
one, delete the remaining text file from the directory.
"""


# TODO:  ADD / TEST AN ALREADY CODED T_TEST to SIMPLIFY MY LIFE AND HELP PROVIDE CONFIDENCE. FINISH FIXING MY_FINCTIONS FILE.
# from __future__ import print_function, division
import numpy as np
import random
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import seaborn as sns
from miller_curve_algorithm import ccgFilter
from PyAstronomy import pyasl
from datetime import datetime
from my_functions import long_date_to_decimal_date
from my_functions import monte_carlo_randomization_smooth
from my_functions import monte_carlo_randomization_trend

# general plot parameters
colors = sns.color_palette("rocket", 6)
colors2 = sns.color_palette("mako", 6)
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['font.size'] = 10
size1 = 5

heidelberg = pd.read_excel(r'H:\The Science\Datasets\heidelberg_cape_grim.xlsx', skiprows=40)  # import heidelberg data
baringhead = pd.read_excel(r'H:\The Science\Datasets\BHD_14CO2_datasets_20211013.xlsx')  # import Baring Head data
df2_dates = pd.read_excel(r'H:\The Science\Datasets\BHD_MeasurementDates.xlsx')  # CO2 measure date
extraction_dates = pd.read_excel(r'H:\The Science\Datasets\BHDFlasks_WithExtractionDates.xlsx') # CO2 extract date

""" TIDY UP THE DATA FILES"""
""" 
Some of the "Date formatting" can be quite tricky. The first step in cleaning the data is to convert
long-format dates to decimal dates that can be used in the CCGCRV curve smoothing algorithm. This is done using a 
function I wrote and lives in my_functions.py.
"""
x_init_heid = heidelberg['Average pf Start-date and enddate']  # extract x-values from heidelberg dataset
x_init_heid = long_date_to_decimal_date(x_init_heid)           # convert the x-values to a decimal date
heidelberg['Decimal_date'] = x_init_heid                       # add these decimal dates onto the dataframe
heidelberg = heidelberg.dropna(subset=['D14C'])                # drop NaN's in the column I'm most interested in
heidelberg = heidelberg.loc[(heidelberg['D14C'] > 10)]         # Filtering out an outlier around 2019
heidelberg.reset_index()                                       # reset the index to avoid heaps of gnarly errors
baringhead = baringhead.dropna(subset=['DELTA14C'])            # drop NaN's in the column I'm most interested in


"""CAREFULLY SPLIT UP THE DATA INTO DIFFERENT TIME BINS AND GRAB VARIABLES """
""" 
Entire Baring Head File > 1980.
In this first time-indexing, we only care about values after 1980 because the earliest date from the Heidelberg 
group is 1987. For this comparison, we only care about the relevant, overlapping time periods. So we can ignore the
early periods, and early part of the bomb-spike. 
 """
baringhead = baringhead.loc[(baringhead['DEC_DECAY_CORR'] > 1980)]  # index the data. Only take post-1980 data
baringhead = baringhead.loc[(baringhead['DELTA14C_ERR'] > 0)]       # get rid of data where the error flag is -1000
baringhead = baringhead.reset_index(drop=True)                      # re-index to avoid gnarly errors

""" 
Entire Baring Head File > 1980, without 1995 - 2005. 
There is precedent for this indexing as well. In this period of time, GNS RRL switched to AMS measurements, and there 
was a significant period of anomalously high values. 
This was also highlighted in Section 3.3 of (Turnbull et al., 2017)
To accomplish this, I have to split the data into two, before 1994, and after 2006, and re-merge them. 
 """
snipmin = 1994  # was previously 1994
snipmax = 2006  # was previously 2006
snip = baringhead.loc[(baringhead['DEC_DECAY_CORR'] < snipmin)]   # index 1980 - 1994
snip2 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] > snipmax)]  # index 2006 - end
snip = pd.merge(snip, snip2, how='outer')                         # merge the files back together
snip = snip.reset_index(drop=True)                                # reset the index to avoid gnarly errors

"""
RECORDS SPLIT UP INTO 5 PARTS (1987 - 1991, 1991 - 1994, 2006 - 2016, 2006 - 2009, 2012 - 2016)
Now, I'm indexing further into smaller time intervals. The later period is broken up from 2006 - 2009 and 2012 - 2016 
because there is another small issue with the data between 2009 - 2012. This can be observed by comparing the indexed
file baringhead_2006_2016 to the other indexed records.

Because these time bins are 3-4 year periods, I also decided to similarly split up the earlier times (1987 - 1994) 
in a similar way - although I could have left this time period whole. 
"""
baringhead_1986_1991 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] >= 1987) & (baringhead['DEC_DECAY_CORR'] <= 1991)]
baringhead_1991_1994 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] >= 1991) & (baringhead['DEC_DECAY_CORR'] <= 1994)]
baringhead_2006_2016 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] > 2006) & (baringhead['DEC_DECAY_CORR'] <= 2016)]
baringhead_2006_2009 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] >= 2006) & (baringhead['DEC_DECAY_CORR'] <= 2009)]
baringhead_2012_2016 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] >= 2012) & (baringhead['DEC_DECAY_CORR'] <= 2016)]
baringhead_1986_1991 = baringhead_1986_1991.reset_index(drop=True)  # re-index to avoid gnarly errors
baringhead_1991_1994 = baringhead_1991_1994.reset_index(drop=True)  # re-index to avoid gnarly errors
baringhead_2006_2016 = baringhead_2006_2016.reset_index(drop=True)  # re-index to avoid gnarly errors
baringhead_2006_2009 = baringhead_2006_2009.reset_index(drop=True)  # re-index to avoid gnarly errors
baringhead_2012_2016 = baringhead_2012_2016.reset_index(drop=True)  # re-index to avoid gnarly errors

heidelberg_1986_1991 = heidelberg.loc[(heidelberg['Decimal_date'] >= 1987) & (heidelberg['Decimal_date'] <= 1991)]
heidelberg_1991_1994 = heidelberg.loc[(heidelberg['Decimal_date'] >= 1991) & (heidelberg['Decimal_date'] <= 1994)]
heidelberg_2006_2016 = heidelberg.loc[(heidelberg['Decimal_date'] > 2006)]  # BARINGHEAD2 will include the 2009-2011
heidelberg_2006_2009 = heidelberg.loc[(heidelberg['Decimal_date'] >= 2006) & (heidelberg['Decimal_date'] <= 2009)]
heidelberg_2012_2016 = heidelberg.loc[(heidelberg['Decimal_date'] >= 2012) & (heidelberg['Decimal_date'] <= 2016)]
heidelberg_1986_1991 = heidelberg_1986_1991.reset_index(drop=True)  # re-index to avoid gnarly errors
heidelberg_1991_1994 = heidelberg_1991_1994.reset_index(drop=True)  # re-index to avoid gnarly errors
heidelberg_2006_2016 = heidelberg_2006_2016.reset_index(drop=True)  # re-index to avoid gnarly errors
heidelberg_2006_2009 = heidelberg_2006_2009.reset_index(drop=True)  # re-index to avoid gnarly errors
heidelberg_2012_2016 = heidelberg_2012_2016.reset_index(drop=True)  # re-index to avoid gnarly errors

"""
After indexing into all these time-bins, now I have to extract all the x, y, and y-error variables from each and
every one of them. This region of the code could likely be vastly improved, although I don't know if there is a 
fast / easy way to get around this besides simply typing it out. 
"""
# BARING HEAD VARIABLES
xtot_bhd = baringhead['DEC_DECAY_CORR']             # entire dataset x-values
ytot_bhd = baringhead['DELTA14C']                   # entire dataset y-values
ztot_bhd = baringhead['DELTA14C_ERR']               # entire dataset z-values
x_combined = snip['DEC_DECAY_CORR']                 # dataset x-values after we remove 1995-2005
y_combined = snip['DELTA14C']                       # dataset y-values after we remove 1995-2005
z_combined = snip['DELTA14C_ERR']                   # dataset z-values after we remove 1995-2005
x1_bhd = baringhead_1986_1991['DEC_DECAY_CORR']
x2_bhd = baringhead_1991_1994['DEC_DECAY_CORR']
x3_bhd = baringhead_2006_2016['DEC_DECAY_CORR']
x4_bhd = baringhead_2006_2009['DEC_DECAY_CORR']
x5_bhd = baringhead_2012_2016['DEC_DECAY_CORR']
y1_bhd = baringhead_1986_1991['DELTA14C']  #
y2_bhd = baringhead_1991_1994['DELTA14C']
y3_bhd = baringhead_2006_2016['DELTA14C']
y4_bhd = baringhead_2006_2009['DELTA14C']
y5_bhd = baringhead_2012_2016['DELTA14C']
z1_bhd = baringhead_1986_1991['DELTA14C_ERR']
z2_bhd = baringhead_1991_1994['DELTA14C_ERR']
z3_bhd = baringhead_2006_2016['DELTA14C_ERR']
z4_bhd = baringhead_2006_2009['DELTA14C_ERR']
z5_bhd = baringhead_2012_2016['DELTA14C_ERR']
# HEIDELBERG CAPE GRIM VARIABLES
xtot_heid = heidelberg['Decimal_date']             # entire dataset x-values
ytot_heid = heidelberg['D14C']                     # entire dataset y-values
ztot_heid = heidelberg['weightedstderr_D14C']      # entire dataset error(z)-values
x1_heid = heidelberg_1986_1991['Decimal_date']
x2_heid = heidelberg_1991_1994['Decimal_date']
x3_heid = heidelberg_2006_2016['Decimal_date']
x4_heid = heidelberg_2006_2009['Decimal_date']
x5_heid = heidelberg_2012_2016['Decimal_date']
y1_heid = heidelberg_1986_1991['D14C']
y2_heid = heidelberg_1991_1994['D14C']
y3_heid = heidelberg_2006_2016['D14C']
y4_heid = heidelberg_2006_2009['D14C']
y5_heid = heidelberg_2012_2016['D14C']
z1_heid = heidelberg_1986_1991['weightedstderr_D14C']
z2_heid = heidelberg_1991_1994['weightedstderr_D14C']
z3_heid = heidelberg_2006_2016['weightedstderr_D14C']
z4_heid = heidelberg_2006_2009['weightedstderr_D14C']
z5_heid = heidelberg_2012_2016['weightedstderr_D14C']

"""
So now we're almost ready to use the CCGCRV curve smoothing. One tricky bit is that - I want to compare the Cape Grim 
and Baring Head records; however, the x-values in time are not necessarily overlapping. How to best compare them? 
Luckily, the CCGCRV algorithm allows me to OUTPUT the smoothed data at any x-time that I desire. Therefore, in the next
bit of code, I create an evenly distributed set of x-values that I will output the smoothed baringhead and heidelberg 
data, in 480 points between 1980 and 2020. 
 
"fake_x_temp" is called this way because it is an x-value I have created. Not 'fake' but I was lazy in initial naming 
when first writing the code.  
 
"""
fake_x_temp = np.linspace(1980, 2020, 480)     # create arbitrary set of x-values to control output
df_fake_xs = pd.DataFrame({'x': fake_x_temp})  # put this set into a pandas DataFrame for easier use
my_x_1986_1991 = df_fake_xs.loc[(df_fake_xs['x'] >= min(x1_heid)) & (df_fake_xs['x'] <= max(x1_heid))].reset_index(drop=True)  # index it
my_x_1991_1994 = df_fake_xs.loc[(df_fake_xs['x'] >= min(x2_bhd)) & (df_fake_xs['x'] <= max(x2_bhd))].reset_index(drop=True)    # index it
my_x_2006_2016 = df_fake_xs.loc[(df_fake_xs['x'] >= min(x3_heid)) & (df_fake_xs['x'] <= max(x3_heid))].reset_index(drop=True)  # index it
my_x_2006_2009 = df_fake_xs.loc[(df_fake_xs['x'] >= min(x4_heid)) & (df_fake_xs['x'] <= max(x4_heid))].reset_index(drop=True)  # index it
my_x_2012_2016 = df_fake_xs.loc[(df_fake_xs['x'] >= min(x5_heid)) & (df_fake_xs['x'] <= max(x5_heid))].reset_index(drop=True)  # index it
my_x_1986_1991 = my_x_1986_1991['x']  # when I wrote the function I'll be using in a few lines,
my_x_1991_1994 = my_x_1991_1994['x']  # I specify that the first 4 arguments must be input as data/variables that
my_x_2006_2016 = my_x_2006_2016['x']  # have been extracted from a pandas DataFrame, for consistency across testing
my_x_2006_2009 = my_x_2006_2009['x']
my_x_2012_2016 = my_x_2012_2016['x']
"""
Now comes the CCGCRV Curve smoothing, and Monte Carlo error analysis. 

The following description can be found in the my_functions.py file. 

This function has three separate for-loops: 
The first for-loop: 
Takes an input array of time-series data and randomizes each data point
within its measurements uncertainty. It does this "n" times, and vertically stacks it.
For example, if you have a dataset with 10 measurements, and "n" is 1000, you will end
up with an array of dimension (10x1000).
If you're interested in re-testing how the normal distribution randomization works, you can copy and paste the 
following few lines of code. This shows that indeed, the randomization does have a higher probability of putting the 
randomized point closer to the mean, but actually the distribution follows the gaussian curve. 
###########################
array = []
for i in range(0,10000):
    rand = np.random.normal(10, 2, size=None)
    array.append(rand)
plt.hist(array, bins=100)
plt.show()
###########################

The second for-loop: 
Takes each row of the array (each row of "randomized data") and puts it through
the ccgFilter curve smoother. It is important to define your own x-values that you want output
if you want to compare two curves (this will keep arrays the same dimension).
Each row from the fist loop is smoothed and stacked into yet another new array.

The third for-loop: 
Find the mean, standard deviation, and upper and lower uncertainty bounds of each
"point" in the dataset. This loop takes the mean of all the first measurements, then all the second, etc.

For clarty, I will define all of the arguments here below: 
x_init: x-values of the dataset that you want to smooth. Must be in decimal date format. 
fake_x: x-values of the data you want OUTPUT
y_init: y-values of the dataset that you want to smooth. 
y_error: y-value errors of the dataset that you want to smooth. 
cutoff: for the CCGCRV algoritm, lower numbers smooth less, and higher numbers smooth more. 
    See hyperlink above for more details. 
n: how many iterations do you want to run? When writing code, keep this low. Once code is solid, increase to 10,000. 

### If you want to see this function in action, refer to "MonteCarlo_Explained.py"
https://github.com/christianlewis091/radiocarbon_intercomparison/blob/dev/interlab_comparison/MonteCarlo_Explained.py


ESSENTIALLY WHAT WE ARE DOING: 
1. RANDOMIZE THE HEIDELBERG AND BARING HEAD DATA 10,000 TIMES ALONG ITS NORMAL DISTRIBUTION
2. SMOOTH THAT DATA USING CCGCRV
3. FIND THE MEAN OF EACH X-VALUE FOR THOSE 10,000 ITERATIONS
4. COMPARE THE HEIDELBERG AND BARING HEAD DATA IN TIME. 

"""
n = 10          # set the amount of times the code will iterate (set to 10,000 once everything is final)
cutoff = 667    # FFT filter cutoff

bhd_1986_1991_results_smooth = monte_carlo_randomization_smooth(x1_bhd, my_x_1986_1991, y1_bhd, z1_bhd, cutoff, n)
print(bhd_1986_1991_results_smooth)

"""
Extract the data back out after the smoothing process. 
The function returns:
1. A dataframe of the randomized data
2. A dataframe of the smoothed data
3. A summary dataframe (see below)
  
    summary = pd.DataFrame({"Means": mean_array, "Error": stdev_array})

    return randomized_dataframe, smoothed_dataframe, summary
    
For Figure 2 of the paper, I want to show an example of the randomization and smoothing process, for both the 
getSmoothValue and getTrendValue. 
We don't always need to extract all of the randomized data and multiple of the smooth curves (usually we just need
the mean). However, for this figure / to illustrate the point, I will extract the data for this one case. 
"""



# fig = plt.figure(2)
# plt.title('Visualization of Monte Carlo and CCGCRV Process: 1987-1991 BHD')
# plt.errorbar(xtot_bhd, ytot_bhd, label='CGO Data' , yerr=ztot_bhd, fmt='o', color='black', ecolor='black', elinewidth=1, capsize=2)
# plt.scatter(x1_bhd, data1, color = colors[0], label = 'Monte Carlo Iteration 1', alpha = 0.35, marker = 'x')
# plt.scatter(x1_bhd, data2, color = colors[1],  label = 'Monte Carlo Iteration 2', alpha = 0.35, marker = '^')
# plt.scatter(x1_bhd, data3, color = colors[2],  label = 'Monte Carlo Iteration 3', alpha = 0.35, marker = 's')
# plt.plot(my_x_1986_1991, curve1, color = colors[0], alpha = 0.35, linestyle = 'dotted')
# # plt.plot(xs, curve2, color = colors[1], alpha = 0.35, linestyle = 'dashed')
# # plt.plot(xs, curve3, color = colors[2], alpha = 0.35, linestyle = 'dashdot')
# # plt.plot(xs, means, color = 'red',  label = 'CCGCRV Smooth Values', alpha = 1, linestyle = 'solid')
# # plt.plot(xs, means2, color = 'blue',  label = 'CCGCRV Trend Values', alpha = 1, linestyle = 'solid')
# plt.xlim([1989, 1991])
# plt.ylim([140, 170])
# plt.legend()
# plt.xlabel('Date', fontsize=14)
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
# # plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figure2.png',
# #             dpi=300, bbox_inches="tight")
# plt.show()
# plt.close()
















# means = summary['Means']
# xs = summary['my_xs']
#
# summary2 = bhd_1986_1991_results_trend[2]
# means2 = summary2['Means']
# #
# """
# Data from getSmoothValue
# """
# # extract the summary DataFrame from the function
# heidelberg_1986_1991_results_smooth = heidelberg_1986_1991_results_smooth[2]
# heidelberg_1991_1994_results_smooth = heidelberg_1991_1994_results_smooth[2]
# heidelberg_2006_2016_results_smooth = heidelberg_2006_2016_results_smooth[2]
# heidelberg_2006_2009_results_smooth = heidelberg_2006_2009_results_smooth[2]
# heidelberg_2012_2016_results_smooth = heidelberg_2012_2016_results_smooth[2]
# bhd_1986_1991_results_smooth = bhd_1986_1991_results_smooth[2]
# bhd_1991_1994_results_smooth = bhd_1991_1994_results_smooth[2]
# bhd_2006_2016_results_smooth = bhd_2006_2016_results_smooth[2]
# bhd_2006_2009_results_smooth = bhd_2006_2009_results_smooth[2]
# bhd_2012_2016_results_smooth = bhd_2012_2016_results_smooth[2]
#
# # extract the means from the summary DataFrame
# heidelberg_1986_1991_mean_smooth = heidelberg_1986_1991_results_smooth['Means']
# heidelberg_1991_1994_mean_smooth = heidelberg_1991_1994_results_smooth['Means']
# heidelberg_2006_2016_mean_smooth = heidelberg_2006_2016_results_smooth['Means']
# heidelberg_2006_2009_mean_smooth = heidelberg_2006_2009_results_smooth['Means']
# heidelberg_2006_2009_mean_smooth = heidelberg_2006_2009_mean_smooth.iloc[0:34]
# heidelberg_2012_2016_mean_smooth = heidelberg_2012_2016_results_smooth['Means']
# heidelberg_2012_2016_mean_smooth = heidelberg_2012_2016_mean_smooth.iloc[1:40]
# heidelberg_2012_2016_mean_smooth = heidelberg_2012_2016_mean_smooth.reset_index(drop=True)
# bhd_1986_1991_mean_smooth = bhd_1986_1991_results_smooth['Means']
# bhd_1991_1994_mean_smooth = bhd_1991_1994_results_smooth['Means']
# bhd_2006_2016_mean_smooth = bhd_2006_2016_results_smooth['Means']
# bhd_2006_2009_mean_smooth = bhd_2006_2009_results_smooth['Means']
# bhd_2006_2009_mean_smooth = bhd_2006_2009_mean_smooth.iloc[0:34]
# bhd_2012_2016_mean_smooth = bhd_2012_2016_results_smooth['Means']
# bhd_2012_2016_mean_smooth = bhd_2012_2016_mean_smooth.iloc[1:40]
# bhd_2012_2016_mean_smooth = bhd_2012_2016_mean_smooth.reset_index(drop=True)
# my_x_2012_2016_trimmed = my_x_2012_2016[1:40]
#
#
# heidelberg_1986_1991_stdevs_smooth = heidelberg_1986_1991_results_smooth['stdevs']
# heidelberg_1991_1994_stdevs_smooth = heidelberg_1991_1994_results_smooth['stdevs']
# heidelberg_2006_2016_stdevs_smooth = heidelberg_2006_2016_results_smooth['stdevs']
# heidelberg_2006_2009_stdevs_smooth = heidelberg_2006_2009_results_smooth['stdevs']
# heidelberg_2006_2009_stdevs_smooth = heidelberg_2006_2009_stdevs_smooth.iloc[0:34]
# heidelberg_2012_2016_stdevs_smooth = heidelberg_2012_2016_results_smooth['stdevs']
# heidelberg_2012_2016_stdevs_smooth = heidelberg_2012_2016_stdevs_smooth.iloc[1:40]
# heidelberg_2012_2016_stdevs_smooth = heidelberg_2012_2016_stdevs_smooth.reset_index(drop=True)
# bhd_1986_1991_stdevs_smooth = bhd_1986_1991_results_smooth['stdevs']
# bhd_1991_1994_stdevs_smooth = bhd_1991_1994_results_smooth['stdevs']
# bhd_2006_2016_stdevs_smooth = bhd_2006_2016_results_smooth['stdevs']
# # # TODO Figure out why the final row of this goes to NaN...
# bhd_2006_2009_stdevs_smooth = bhd_2006_2009_results_smooth['stdevs']
# # TODO currently I'm snipping the 2006-2009 files of the last row that goes to NaN cuz I can't debug it...
# my_x_2006_2009_trimmed = my_x_2006_2009.iloc[0:34]
# bhd_2006_2009_stdevs_smooth = bhd_2006_2009_stdevs_smooth.iloc[0:34]
# bhd_2012_2016_stdevs_smooth = bhd_2012_2016_results_smooth['stdevs']
# # TODO currently I'm snipping the first row because beginning is NAN of the last row that goes to NaN cuz I can't debug it...
# bhd_2012_2016_stdevs_smooth = bhd_2012_2016_stdevs_smooth.iloc[1:40]
# bhd_2012_2016_stdevs_smooth = bhd_2012_2016_stdevs_smooth.reset_index(drop=True)
#
# """
# Data from gettrendValue
# """
#
# # extract the summary DataFrame from the function
# heidelberg_1986_1991_results_trend = heidelberg_1986_1991_results_trend[2]
# heidelberg_1991_1994_results_trend = heidelberg_1991_1994_results_trend[2]
# heidelberg_2006_2016_results_trend = heidelberg_2006_2016_results_trend[2]
# heidelberg_2006_2009_results_trend = heidelberg_2006_2009_results_trend[2]
# heidelberg_2012_2016_results_trend = heidelberg_2012_2016_results_trend[2]
# bhd_1986_1991_results_trend = bhd_1986_1991_results_trend[2]
# bhd_1991_1994_results_trend = bhd_1991_1994_results_trend[2]
# bhd_2006_2016_results_trend = bhd_2006_2016_results_trend[2]
# bhd_2006_2009_results_trend = bhd_2006_2009_results_trend[2]
# bhd_2012_2016_results_trend = bhd_2012_2016_results_trend[2]
#
# # extract the means from the summary DataFrame
# heidelberg_1986_1991_mean_trend = heidelberg_1986_1991_results_trend['Means']
# heidelberg_1991_1994_mean_trend = heidelberg_1991_1994_results_trend['Means']
# heidelberg_2006_2016_mean_trend = heidelberg_2006_2016_results_trend['Means']
# heidelberg_2006_2009_mean_trend = heidelberg_2006_2009_results_trend['Means']
# heidelberg_2006_2009_mean_trend = heidelberg_2006_2009_mean_trend.iloc[0:34]
# heidelberg_2012_2016_mean_trend= heidelberg_2012_2016_results_trend['Means']
# heidelberg_2012_2016_mean_trend = heidelberg_2012_2016_mean_trend.iloc[1:40]
# heidelberg_2012_2016_mean_trend = heidelberg_2012_2016_mean_trend.reset_index(drop=True)
# bhd_1986_1991_mean_trend = bhd_1986_1991_results_trend['Means']
# bhd_1991_1994_mean_trend = bhd_1991_1994_results_trend['Means']
# bhd_2006_2016_mean_trend = bhd_2006_2016_results_trend['Means']
# bhd_2006_2009_mean_trend = bhd_2006_2009_results_trend['Means']
# bhd_2006_2009_mean_trend = bhd_2006_2009_mean_trend.iloc[0:34]
# bhd_2012_2016_mean_trend = bhd_2012_2016_results_trend['Means']
# bhd_2012_2016_mean_trend = bhd_2012_2016_mean_trend.iloc[1:40]
# bhd_2012_2016_mean_trend = bhd_2012_2016_mean_trend.reset_index(drop=True)
#
# heidelberg_1986_1991_stdevs_trend = heidelberg_1986_1991_results_trend['stdevs']
# heidelberg_1991_1994_stdevs_trend = heidelberg_1991_1994_results_trend['stdevs']
# heidelberg_2006_2016_stdevs_trend = heidelberg_2006_2016_results_trend['stdevs']
# heidelberg_2006_2009_stdevs_trend = heidelberg_2006_2009_results_trend['stdevs']
# heidelberg_2006_2009_stdevs_trend = heidelberg_2006_2009_stdevs_trend.iloc[0:34]
# heidelberg_2012_2016_stdevs_trend = heidelberg_2012_2016_results_trend['stdevs']
# heidelberg_2012_2016_stdevs_trend = heidelberg_2012_2016_stdevs_trend.iloc[1:40]
# heidelberg_2012_2016_stdevs_trend = heidelberg_2012_2016_stdevs_trend.reset_index(drop=True)
# bhd_1986_1991_stdevs_trend = bhd_1986_1991_results_trend['stdevs']
# bhd_1991_1994_stdevs_trend = bhd_1991_1994_results_trend['stdevs']
# bhd_2006_2016_stdevs_trend = bhd_2006_2016_results_trend['stdevs']
# # # TODO Figure out why the final row of this goes to NaN...
# bhd_2006_2009_stdevs_trend = bhd_2006_2009_results_trend['stdevs']
# bhd_2006_2009_stdevs_trend = bhd_2006_2009_stdevs_trend.iloc[0:34]
# bhd_2012_2016_stdevs_trend = bhd_2012_2016_results_trend['stdevs']
# # TODO currently I'm snipping the first row because beginning is NAN of the last row that goes to NaN cuz I can't debug it...
# bhd_2012_2016_stdevs_trend = bhd_2012_2016_stdevs_trend.iloc[1:40]
# bhd_2012_2016_stdevs_trend = bhd_2012_2016_stdevs_trend.reset_index(drop=True)
#
#
#
#
#
#
# """
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# Perform paired t-tests on sets of data and write result to file.
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# """
#
# """ paired t-tests of each of the datasets"""
# print('Baring Head vs Cape Grim between 1986 - 1991 using CCGCRV Smooth Fit', file=f)
# two_tail_paired_t_test(bhd_1986_1991_mean_smooth, bhd_1986_1991_stdevs_smooth, heidelberg_1986_1991_mean_smooth,
#                        heidelberg_1986_1991_stdevs_smooth)
# print()
# print()
# print('Baring Head vs Cape Grim between 1991 - 1994 using CCGCRV Smooth Fit', file=f)
# two_tail_paired_t_test(bhd_1991_1994_mean_smooth, bhd_1991_1994_stdevs_smooth, heidelberg_1991_1994_mean_smooth,
#                        heidelberg_1991_1994_stdevs_smooth)
# print()
# print()
# print('Baring Head vs Cape Grim between 2006 - 2016 using CCGCRV Smooth Fit', file=f)
# two_tail_paired_t_test(bhd_2006_2016_mean_smooth, bhd_2006_2016_stdevs_smooth, heidelberg_2006_2016_mean_smooth,
#                        heidelberg_2006_2016_stdevs_smooth)
# print()
# print()
# print('Baring Head vs Cape Grim between 2006 - 2009 using CCGCRV Smooth Fit', file=f)
# two_tail_paired_t_test(bhd_2006_2009_mean_smooth, bhd_2006_2009_stdevs_smooth, heidelberg_2006_2009_mean_smooth,
#                        heidelberg_2006_2009_stdevs_smooth)
# print()
# print()
# print('Baring Head vs Cape Grim between 2012 - 2016 using CCGCRV Smooth Fit', file=f)
# two_tail_paired_t_test(bhd_2012_2016_mean_smooth, bhd_2012_2016_stdevs_smooth, heidelberg_2012_2016_mean_smooth,
#                        heidelberg_2012_2016_stdevs_smooth)
# print()
# print()
#
# """ paired t-tests of each of the datasets"""
# print('Baring Head vs Cape Grim between 1986 - 1991 using CCGCRV Trend Fit', file=f)
# two_tail_paired_t_test(bhd_1986_1991_mean_trend, bhd_1986_1991_stdevs_trend, heidelberg_1986_1991_mean_trend,
#                        heidelberg_1986_1991_stdevs_trend)
# print()
# print()
# print('Baring Head vs Cape Grim between 1991 - 1994 using CCGCRV Trend Fit', file=f)
# two_tail_paired_t_test(bhd_1991_1994_mean_trend, bhd_1991_1994_stdevs_trend, heidelberg_1991_1994_mean_trend,
#                        heidelberg_1991_1994_stdevs_trend)
# print()
# print()
# print('Baring Head vs Cape Grim between 2000 - 2016 using CCGCRV Trend Fit', file=f)
# two_tail_paired_t_test(bhd_2006_2016_mean_trend, bhd_2006_2016_stdevs_trend, heidelberg_2006_2016_mean_trend,
#                        heidelberg_2006_2016_stdevs_trend)
# print()
# print()
# print('Baring Head vs Cape Grim between 2006 - 2009 using CCGCRV Trend Fit', file=f)
# two_tail_paired_t_test(bhd_2006_2009_mean_trend, bhd_2006_2009_stdevs_trend, heidelberg_2006_2009_mean_trend,
#                        heidelberg_2006_2009_stdevs_trend)
# print()
# print()
# print('Baring Head vs Cape Grim between 2012 - 2016 using CCGCRV Trend Fit', file=f)
# two_tail_paired_t_test(bhd_2012_2016_mean_trend, bhd_2012_2016_stdevs_trend, heidelberg_2012_2016_mean_trend,
#                        heidelberg_2012_2016_stdevs_trend)
#
# # testing that the functions will plot later, as I've had trouble with this before...
# # plt.scatter(my_x_1986_1991, bhd_1986_1991_mean_smooth)
# # plt.scatter(my_x_1986_1991, bhd_1986_1991_mean_trend)
# # plt.scatter(my_x_1986_1991, heidelberg_1986_1991_mean_smooth)
# # plt.scatter(my_x_1986_1991, heidelberg_1986_1991_mean_trend)
# # plt.scatter(my_x_1991_1994, bhd_1991_1994_mean_smooth)
# # plt.scatter(my_x_1991_1994, bhd_1991_1994_mean_trend)
# # plt.scatter(my_x_1991_1994, heidelberg_1991_1994_mean_smooth)
# # plt.scatter(my_x_1991_1994, heidelberg_1991_1994_mean_trend)
# # plt.scatter(my_x_2006_2009_trimmed, bhd_2006_2009_mean_smooth)
# # plt.scatter(my_x_2006_2009_trimmed, bhd_2006_2009_mean_trend)
# # plt.scatter(my_x_2006_2009_trimmed, heidelberg_2006_2009_mean_smooth)
# # plt.scatter(my_x_2006_2009_trimmed, heidelberg_2006_2009_mean_trend)
# # plt.scatter(my_x_2012_2016_trimmed, bhd_2012_2016_mean_smooth)
# # plt.scatter(my_x_2012_2016_trimmed, bhd_2012_2016_mean_trend)
# # plt.scatter(my_x_2012_2016_trimmed, heidelberg_2012_2016_mean_smooth)
# # plt.scatter(my_x_2012_2016_trimmed, heidelberg_2012_2016_mean_trend)
# # plt.show()
#
# """
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# Answering the Question "Does time in the collection flask alter final 14C value?
# To answer this: first we looked at difference in measurement - collection time. This is good initially but doesn't
# account for situation in which the CO2 was extracted from the flask early and not measured for a while.
# Therefore I will rely on the data where we have all 1) collection, 2) extraction and 3) measurement data.
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# """
# """
# The below block of code was used for the file in which we have measurement but not extraction data. Ignore for now.
# """
# # df2_dates = df2_dates.drop(columns=['∆14C', '∆14C_err',
# #                                     'Flag', 'CollectionMethod'], axis=1)
# # df2_dates = df2_dates.dropna(subset=['DateMeasured'])
# # df2_dates = df2_dates.reset_index()
# # # change the format of dates in the df2_dates
# # forchange = df2_dates['DateMeasured']
# # forchange = long_date_to_decimal_date(forchange)
# # df2_dates['DateMeasured_Decimal'] = forchange
# #
# # # find the difference between measurement date and collection date and append this to the measurement file
# # df2_dates['difference'] = df2_dates['DateMeasured_Decimal'] - np.float64(df2_dates['DecimalDateCollected'])
# # # rename the New Zealand ID for easy merging along this axis
# # df2_dates = df2_dates.rename(columns={"NZ/NZA": "NZ"})
# # # drop more columns to simplify the merge
# # df2_dates = df2_dates.drop(columns=['index', 'DecimalDateCollected', 'DateMeasured',
# #                                     'DateMeasured_Decimal'], axis=1)
# # df2_dates.drop_duplicates(subset ="NZ", keep = False, inplace = True)
# #
# # baringhead = baringhead.merge(df2_dates, how='outer')
# # baringhead = baringhead.dropna(subset=['DELTA14C'])
# # # baringhead.to_excel('testing2.xlsx')
#
# """
# This block of code deals with the extraction dates.
# I'll merge this data with the baring head file, and compare how far the D14C data is from the trend-line as a function
# of time waiting in the flask.
#
# """
# extraction_dates = extraction_dates.drop(columns=['Job', 'Samples::Sample Description', 'Samples::Sample ID',
#                                                   'AMS Submission Results Complete::Collection Date',
#                                                   'AMS Submission Results Complete::DELTA14C',
#                                                   'AMS Submission Results Complete::DELTA14C_Error',
#                                                   'AMS Submission Results Complete::Weight Initial',
#                                                   'AMS Submission Results Complete::TP',
#                                                   'AMS Submission Results Complete::TW',
#                                                   'AMS Submission Results Complete::Date Run',
#                                                   'AMS Submission Results Complete::delta13C_IRMS',
#                                                   'AMS Submission Results Complete::delta13C_AMS',
#                                                   'AMS Submission Results Complete::F_corrected_normed',
#                                                   'AMS Submission Results Complete::F_corrected_normed_error',
#                                                   'Graphite Completed::End Date', 'Graphite Completed::CO2_Yield',
#                                                   'Graphite Completed::Prebake_Yield',
#                                                   'Graphite Completed::Graphite_Yield',
#                                                   'AMS Submission Results Complete::Quality Flag',
#                                                   'Samples::Pretreatment by Submitter', 'Samples::Sample Date Start',
#                                                   'Samples::Sample Time Start', 'Samples::Sample Date End',
#                                                   'Samples::Sample Time End', 'Samples::Sample Days Exposed',
#                                                   'Samples::Latitude', 'Samples::Longitude', 'Samples::Location',
#                                                   'Samples::Sampling Height'], axis=1)
#
# extraction_dates = extraction_dates.rename(columns={"NZA": "NZ"})
# # With this line, the baring head data is now merged with that of the extraction dates.
# baringhead = baringhead.merge(extraction_dates, how='outer')
# # This line creates a new DataFrame that includes only data that has an extraction date. This
# # is an easier way to dump the data into an excel file for viewing.
# baringhead_plus_extract = baringhead.dropna(subset='Extraction of CO2 from Air Date')
#
# """
# There is more data in the "extraction date" column than the other column after this merge because
# There is excess data without NZ numbers in the original file.
# Right now I'm only taking data that has a unique NZ number.
# """
#
# baringhead_plus_extract = baringhead_plus_extract.dropna(subset='DELTA14C')
# baringhead_plus_extract = baringhead_plus_extract.reset_index(drop=True)
#
# # now I need to grab the extraction dates and convert them to decimals to compare with DEC_DECAY_CORR.
# extract_date = baringhead_plus_extract['Extraction of CO2 from Air Date']
# extract_date = long_date_to_decimal_date(extract_date)
# baringhead_plus_extract['DateExtracted_Decimal'] = extract_date  # add the new column of decimal data onto DataFrame
# # find the difference between collection and extraction in time.
# baringhead_plus_extract['Differences'] = baringhead_plus_extract['DateExtracted_Decimal'] \
#                                          - baringhead_plus_extract['DEC_DECAY_CORR']
#
# # re-extract all data after 2012 from the original Baring Head data-file so we can create a new smooth curve
# # to compare against (the next three lines contain the data I'll use to create the new smooth fit).
# baringhead_timetest = baringhead.loc[(baringhead['DEC_DECAY_CORR'] > 2012)]
# x_timetest = baringhead_timetest['DEC_DECAY_CORR'].reset_index(drop=True)
# y_timetest = baringhead_timetest['DELTA14C'].reset_index(drop=True)
#
# # these are the data we want to test
# x_extracts = baringhead_plus_extract['DEC_DECAY_CORR'].reset_index(drop=True)
# y_extracts = baringhead_plus_extract['DELTA14C'].reset_index(drop=True)
# time_extracts = baringhead_plus_extract['Differences'].reset_index(drop=True)
#
# time_test = ccgFilter(x_timetest, y_timetest, cutoff).getTrendValue(x_extracts)
# delta = y_extracts - time_test
#
# """
# Now I want to plot: the time waiting in the flask VS deviation in the measured value from the smoothed fit.
# """
#
#
# """
# LOOKS LIKE NO TREND, JUST SCATTER, using both getTREND and getSMOOTH values.
# """
#
# """
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# Answering the Question "What about the monthly means?"
# We should at least do this simple analysis at the very minimum to say that we did it this way.
#
# First, I'll grab the monthly means of both datasets (Full BHD and Heidelberg),
# and then snip the BHD data to only be as large as heidelberg,
# and then do a paired t-test to see where they're different.
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# """
#
# # TODO fix this code so it chops off the decimals or something and makes all the months the same (
# test = monthly_averages(xtot_bhd, ytot_bhd, ztot_bhd)
#
# test_x = test[0]
# test_y = test[1]
# test_z = test[2]
# df_test = pd.DataFrame({'x': test_x, 'y_bhd': test_y, 'z_bhd': test_z})
#
# test2 = monthly_averages(xtot_heid, ytot_heid, ztot_heid)
# test2_x = test2[0]
# test2_y = test2[1]
# test2_z = test2[2]
# df_test2 = pd.DataFrame({'x': test2_x, 'y_heid': test2_y, 'z_heid': test2_z})  # putting both into a dataframe so I can merge on the similar dates
#
# df_test3 = df_test.merge(df_test2, how='outer')
# df_test3.to_excel('testing2.xlsx')
# df_test3 = df_test3.dropna(subset='y_heid')
# df_test3 = df_test3.dropna(subset='y_bhd')
# df_test3 = df_test3.reset_index(drop=True)
# # print(df_test3)
#
#
# df_test3.to_excel('testing2.xlsx')
# test3_x = df_test3['x']
# test3_y_bhd = df_test3['y_bhd']
# test3_y_heid = df_test3['y_heid']
# test3_z_bhd = df_test3['z_bhd']
# test3_z_heid = df_test3['z_heid']
# """
# There is 194 cases in which we have the monthly averages for both BHD and Heid in the same month.
# The lines above where I dropna on both datasets is to find only the months where they are the same.
#
# Now I can do a quick paired t-test, lets see if they are the same...
# """
#
# # plt.scatter(test3_x, test3_y_bhd)
# # plt.scatter(test3_x, test3_y_heid)
# # # plt.show()
#
# #  order to do a two-tail paired t-test, I need to propogate the uncertainties in the monthly averages function...
# print('Here is the result of the paired t-test between BHD and CGO Monthly means for all instances where data overlaps', file=f)
# two_tail_paired_t_test(test3_y_bhd, test3_z_bhd, test3_y_heid, test3_z_heid)
#
#
# f.close()
#
# """
# Monthly averages two-tailed t-test also finds a difference.
# """
#
# """
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# MAIN FIGURES FOR THE PAPER
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
# #######################################################################################################################
#
#
#
#
# # REMEMBER WHEN PLOTTING, THE FOLLOWING SETS OF DATA GO TOGETHER:
#
# PRE - CCGCRV FIT:
#
# x1_bhd -> y1_bhd (the raw data)
# my_x_1986_1991 -> y - output from the CCGCRV curve smoother.
#
# """
#
# # """ FIGURE 1: OVERVIEW OF DATA WE'RE INTERESTED IN """
# # general plot parameters
# colors = sns.color_palette("rocket", 6)
# colors2 = sns.color_palette("mako", 6)
# mpl.rcParams['pdf.fonttype'] = 42
# mpl.rcParams['font.size'] = 10
# size1 = 5
# """
# Figure 1. All the data together
# """
# fig = plt.figure(1)
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size1)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size1)
# plt.legend()
# plt.title('All available data after 1980')
# plt.xlim([1980, 2020])
# plt.ylim([0, 300])
# plt.xlabel('Date', fontsize=14)
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figure1.png',
#             dpi=300, bbox_inches="tight")
# plt.close()
#
# """
# Figure 2. Visual Example of the randomization and smoothing process.
# """
# fig = plt.figure(2)
#
# plt.title('Visualization of Monte Carlo and CCGCRV Process: 1987-1991 BHD')
# plt.errorbar(xtot_bhd, ytot_bhd, label='CGO Data' , yerr=ztot_bhd, fmt='o', color='black', ecolor='black', elinewidth=1, capsize=2)
# plt.scatter(x1_bhd, data1, color = colors[0], label = 'Monte Carlo Iteration 1', alpha = 0.35, marker = 'x')
# plt.scatter(x1_bhd, data2, color = colors[1],  label = 'Monte Carlo Iteration 2', alpha = 0.35, marker = '^')
# plt.scatter(x1_bhd, data3, color = colors[2],  label = 'Monte Carlo Iteration 3', alpha = 0.35, marker = 's')
# plt.plot(xs, curve1, color = colors[0], alpha = 0.35, linestyle = 'dotted')
# plt.plot(xs, curve2, color = colors[1], alpha = 0.35, linestyle = 'dashed')
# plt.plot(xs, curve3, color = colors[2], alpha = 0.35, linestyle = 'dashdot')
# plt.plot(xs, means, color = 'red',  label = 'CCGCRV Smooth Values', alpha = 1, linestyle = 'solid')
# plt.plot(xs, means2, color = 'blue',  label = 'CCGCRV Trend Values', alpha = 1, linestyle = 'solid')
# plt.xlim([1989, 1991])
# plt.ylim([140, 170])
# plt.legend()
# plt.xlabel('Date', fontsize=14)
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figure2.png',
#             dpi=300, bbox_inches="tight")
# # plt.show()
# plt.close()
#
# """
# Figure 3. A breakdown of the 4 period of time that we test for the intercomparison,
# and how the smooth and trend data compare for each.
# """
# size2 = 15
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.1)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.1)
# plt.plot(np.array(my_x_1986_1991), bhd_1986_1991_mean_smooth, color=colors[3], label = 'BHD CCGCRV Smooth Fit')
# plt.plot(np.array(my_x_1986_1991), bhd_1986_1991_mean_trend, color=colors[3], label = 'BHD CCGCRV Trend Fit', linestyle = 'dashed')
# plt.plot(np.array(my_x_1986_1991), heidelberg_1986_1991_mean_smooth, color=colors2[3], label = 'CGO CCGCRV Smooth Fit')
# plt.plot(np.array(my_x_1986_1991), heidelberg_1986_1991_mean_trend, color=colors2[3], label = 'CGO CCGCRV Trend Fit', linestyle = 'dashed')
# plt.plot(np.array(my_x_1991_1994), bhd_1991_1994_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_1991_1994), bhd_1991_1994_mean_trend, color=colors[3], linestyle = 'dashed')
# plt.plot(np.array(my_x_1991_1994), heidelberg_1991_1994_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_1991_1994), heidelberg_1991_1994_mean_trend, color=colors2[3], linestyle = 'dashed')
# plt.plot(np.array(my_x_2006_2009_trimmed), bhd_2006_2009_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_2006_2009_trimmed), bhd_2006_2009_mean_trend, color=colors[3], linestyle = 'dashed')
# plt.plot(np.array(my_x_2006_2009_trimmed), heidelberg_2006_2009_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_2006_2009_trimmed), heidelberg_2006_2009_mean_trend, color=colors2[3], linestyle = 'dashed')
# plt.plot(np.array(my_x_2012_2016_trimmed), bhd_2012_2016_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_2012_2016_trimmed), bhd_2012_2016_mean_trend, color=colors[3], linestyle = 'dashed')
# plt.plot(np.array(my_x_2012_2016_trimmed), heidelberg_2012_2016_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_2012_2016_trimmed), heidelberg_2012_2016_mean_trend, color=colors2[3], linestyle = 'dashed')
# plt.axvline(x = 1987, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.axvline(x = 1991, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.axvline(x = 1994, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.axvline(x = 2006, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.axvline(x = 2009, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.axvline(x = 2012, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.axvline(x = 2016, color = 'black', alpha = 0.2, linestyle = 'solid')
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
# # plt.arrow(1994, 50, -6, 0,  fc="k", ec="k",head_width=0.05, head_length=0.1 )
# plt.xlabel('Date', fontsize=14)  # label the y axis
# plt.ylim([0, 200])
# plt.xlim([1986, 2020])
# plt.legend()
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_Figuretest.png',
#             dpi=300, bbox_inches="tight")
# # plt.show()
# plt.close()
#
# fig = plt.figure(4, figsize=(10 ,3))
# gs = gridspec.GridSpec(1, 8)
# gs.update(wspace=1, hspace=0.1)
# # Generate first panel
# # remember, the grid spec is rows, then columns
#
# # print(type(my_x_1986_1991))
# # print(type(np.array(my_x_1986_1991)))
# # print(type(bhd_1986_1991_mean_smooth))
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 0:2])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# plt.plot(np.array(my_x_1986_1991), bhd_1986_1991_mean_smooth, color=colors[3])
# # plt.plot(np.array(my_x_1986_1991), bhd_1986_1991_mean_trend, color=colors[3])
# plt.plot(np.array(my_x_1986_1991), heidelberg_1986_1991_mean_smooth, color=colors2[3])
# # plt.plot(np.array(my_x_1986_1991), heidelberg_1986_1991_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_1986_1991)), max(np.array(my_x_1986_1991))])
# plt.ylim([min(bhd_1986_1991_mean_smooth), max(bhd_1986_1991_mean_smooth)])
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 2:4])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# plt.plot(np.array(my_x_1991_1994), bhd_1991_1994_mean_smooth, color=colors[3])
# # plt.plot(np.array(my_x_1991_1994), bhd_1991_1994_mean_trend, color=colors[3])
# plt.plot(np.array(my_x_1991_1994), heidelberg_1991_1994_mean_smooth, color=colors2[3])
# # plt.plot(np.array(my_x_1991_1994), heidelberg_1991_1994_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_1991_1994)), max(np.array(my_x_1991_1994))])
# plt.ylim([min(bhd_1991_1994_mean_smooth), max(bhd_1991_1994_mean_smooth)])
#
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 4:6])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# plt.plot(np.array(my_x_2006_2009_trimmed), bhd_2006_2009_mean_smooth, color=colors[3])
# # plt.plot(np.array(my_x_2006_2009_trimmed), bhd_2006_2009_mean_trend, color=colors[3])
# plt.plot(np.array(my_x_2006_2009_trimmed), heidelberg_2006_2009_mean_smooth, color=colors2[3])
# # plt.plot(np.array(my_x_2006_2009_trimmed), heidelberg_2006_2009_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_2006_2009_trimmed)), max(np.array(my_x_2006_2009_trimmed))])
# plt.ylim([min(bhd_2006_2009_mean_smooth), max(bhd_2006_2009_mean_smooth)])
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 6:8])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# plt.plot(np.array(my_x_2012_2016_trimmed), bhd_2012_2016_mean_smooth, color=colors[3], label='Baring Head CCGCRV Fit')
# # plt.plot(np.array(my_x_2012_2016_trimmed), bhd_2012_2016_mean_trend, color=colors[3])
# plt.plot(np.array(my_x_2012_2016_trimmed), heidelberg_2012_2016_mean_smooth, color=colors2[3], label='Cape Grim CCGCRV Fit')
# # plt.plot(np.array(my_x_2012_2016_trimmed), heidelberg_2012_2016_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_2012_2016_trimmed)), max(np.array(my_x_2012_2016_trimmed))])
# plt.ylim([min(bhd_2012_2016_mean_smooth), max(bhd_2012_2016_mean_smooth)])
# plt.legend(loc=(1.04,0.5))
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figure3a.png',
#             dpi=300, bbox_inches="tight")
# # plt.show()
# plt.close()
#
#
# fig = plt.figure(4, figsize=(10 ,3))
# gs = gridspec.GridSpec(1, 8)
# gs.update(wspace=1, hspace=0.1)
# # Generate first panel
# # remember, the grid spec is rows, then columns
#
# # print(type(my_x_1986_1991))
# # print(type(np.array(my_x_1986_1991)))
# # print(type(bhd_1986_1991_mean_smooth))
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 0:2])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# # plt.plot(np.array(my_x_1986_1991), bhd_1986_1991_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_1986_1991), bhd_1986_1991_mean_trend, color=colors[3])
# # plt.plot(np.array(my_x_1986_1991), heidelberg_1986_1991_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_1986_1991), heidelberg_1986_1991_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_1986_1991)), max(np.array(my_x_1986_1991))])
# plt.ylim([min(bhd_1986_1991_mean_smooth), max(bhd_1986_1991_mean_smooth)])
#
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 2:4])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# # plt.plot(np.array(my_x_1991_1994), bhd_1991_1994_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_1991_1994), bhd_1991_1994_mean_trend, color=colors[3])
# # plt.plot(np.array(my_x_1991_1994), heidelberg_1991_1994_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_1991_1994), heidelberg_1991_1994_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_1991_1994)), max(np.array(my_x_1991_1994))])
# plt.ylim([min(bhd_1991_1994_mean_smooth), max(bhd_1991_1994_mean_smooth)])
#
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 4:6])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# # plt.plot(np.array(my_x_2006_2009_trimmed), bhd_2006_2009_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_2006_2009_trimmed), bhd_2006_2009_mean_trend, color=colors[3])
# # plt.plot(np.array(my_x_2006_2009_trimmed), heidelberg_2006_2009_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_2006_2009_trimmed), heidelberg_2006_2009_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_2006_2009_trimmed)), max(np.array(my_x_2006_2009_trimmed))])
# plt.ylim([min(bhd_2006_2009_mean_smooth), max(bhd_2006_2009_mean_smooth)])
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 6:8])
# # plot data for left panel
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color=colors[3], s=size2, alpha = 0.3)
# plt.scatter(xtot_heid, ytot_heid, marker='x', label='Heidelberg Cape Grim Record (CGO)', color=colors2[3], s=size2, alpha = 0.3)
# # plt.plot(np.array(my_x_2012_2016_trimmed), bhd_2012_2016_mean_smooth, color=colors[3])
# plt.plot(np.array(my_x_2012_2016_trimmed), bhd_2012_2016_mean_trend, color=colors[3])
# # plt.plot(np.array(my_x_2012_2016_trimmed), heidelberg_2012_2016_mean_smooth, color=colors2[3])
# plt.plot(np.array(my_x_2012_2016_trimmed), heidelberg_2012_2016_mean_trend, color=colors2[3])
# plt.xlim([min(np.array(my_x_2012_2016_trimmed)), max(np.array(my_x_2012_2016_trimmed))])
# plt.ylim([min(bhd_2012_2016_mean_smooth), max(bhd_2012_2016_mean_smooth)])
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figure3b.png',
#             dpi=300, bbox_inches="tight")
# # plt.show()
# plt.close()
#
#
# """
# Figure S1. Visual Example of the randomization and smoothing process, broken into 4 panels.
# """
# fig = plt.figure(4, figsize=(10,3))
# gs = gridspec.GridSpec(1, 8)
# gs.update(wspace=1, hspace=0.1)
# # Generate first panel
# # remember, the grid spec is rows, then columns
# size2 = 15
# xtr_subsplot = fig.add_subplot(gs[0:1, 0:2])
# # plot data for left panel
# plt.text(1990.75, 167.5, "A", fontsize=12)
# plt.errorbar(xtot_bhd, ytot_bhd, label='CGO Data' , yerr=ztot_bhd, fmt='none', color='black', ecolor='black', elinewidth=1, capsize=2)
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color='black', s=size2)
# plt.scatter(x1_bhd, data1, color = colors[0], label = 'Monte Carlo Iteration 1', alpha = 0.35, marker = 'x', s = size2)
# plt.scatter(x1_bhd, data2, color = colors[1],  label = 'Monte Carlo Iteration 2', alpha = 0.35, marker = '^', s = size2)
# plt.scatter(x1_bhd, data3, color = colors[2],  label = 'Monte Carlo Iteration 3', alpha = 0.35, marker = 's', s = size2)
# # plt.plot(xs, curve1, color = colors[0], alpha = 0.35, linestyle = 'dotted')
# # plt.plot(xs, curve2, color = colors[1], alpha = 0.35, linestyle = 'dashed')
# # plt.plot(xs, curve3, color = colors[2], alpha = 0.35, linestyle = 'dashdot')
# # plt.plot(xs, means, color = 'red',  label = 'CCGCRV Smooth Values', alpha = 1, linestyle = 'solid')
# # plt.plot(xs, means2, color = 'blue',  label = 'CCGCRV Trend Values', alpha = 1, linestyle = 'solid')
# plt.xlim([1989, 1991])
# plt.ylim([140, 170])
#
# plt.ylabel('\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 2:4])
# # plot data for left panel
# plt.text(1990.75, 167.5, "B", fontsize=12)
# plt.errorbar(xtot_bhd, ytot_bhd, label='CGO Data' , yerr=ztot_bhd, fmt='none', color='black', ecolor='black', elinewidth=1, capsize=2)
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color='black', s=size2)
# plt.scatter(x1_bhd, data1, color = colors[0], label = 'Monte Carlo Iteration 1', alpha = 0.35, marker = 'x', s = size2)
# plt.scatter(x1_bhd, data2, color = colors[1],  label = 'Monte Carlo Iteration 2', alpha = 0.35, marker = '^', s = size2)
# plt.scatter(x1_bhd, data3, color = colors[2],  label = 'Monte Carlo Iteration 3', alpha = 0.35, marker = 's', s = size2)
# plt.plot(xs, curve1, color = colors[0], alpha = 0.35, linestyle = 'dotted')
# plt.plot(xs, curve2, color = colors[1], alpha = 0.35, linestyle = 'dashed')
# plt.plot(xs, curve3, color = colors[2], alpha = 0.35, linestyle = 'dashdot')
# # plt.plot(xs, means, color = 'red',  label = 'CCGCRV Smooth Values', alpha = 1, linestyle = 'solid')
# # plt.plot(xs, means2, color = 'blue',  label = 'CCGCRV Trend Values', alpha = 1, linestyle = 'solid')
# plt.xlim([1989, 1991])
# plt.ylim([140, 170])
# plt.text(1991.5,135,'Date')
# xtr_subsplot.set_yticklabels([])
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 4:6])
# # plot data for left panel
# plt.text(1990.75, 167.5, "C", fontsize=12)
# plt.errorbar(xtot_bhd, ytot_bhd, label='CGO Data' , yerr=ztot_bhd, fmt='none', color='black', ecolor='black', elinewidth=1, capsize=2)
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color='black', s=size2)
# plt.scatter(x1_bhd, data1, color = colors[0], label = 'Monte Carlo Iteration 1', alpha = 0.35, marker = 'x', s = size2)
# plt.scatter(x1_bhd, data2, color = colors[1],  label = 'Monte Carlo Iteration 2', alpha = 0.35, marker = '^', s = size2)
# plt.scatter(x1_bhd, data3, color = colors[2],  label = 'Monte Carlo Iteration 3', alpha = 0.35, marker = 's', s = size2)
# plt.plot(xs, curve1, color = colors[0], alpha = 0.35, linestyle = 'dotted')
# plt.plot(xs, curve2, color = colors[1], alpha = 0.35, linestyle = 'dashed')
# plt.plot(xs, curve3, color = colors[2], alpha = 0.35, linestyle = 'dashdot')
# plt.plot(xs, means, color = 'red',  label = 'CCGCRV Smooth Values', alpha = 1, linestyle = 'solid')
# # plt.plot(xs, means2, color = 'blue',  label = 'CCGCRV Trend Values', alpha = 1, linestyle = 'solid')
# plt.xlim([1989, 1991])
# plt.ylim([140, 170])
# xtr_subsplot.set_yticklabels([])
#
# xtr_subsplot = fig.add_subplot(gs[0:1, 6:8])
# # plot data for left panel
# plt.text(1990.75, 167.5, "D", fontsize=12)
# plt.errorbar(xtot_bhd, ytot_bhd, label='CGO Data' , yerr=ztot_bhd, fmt='none', color='black', ecolor='black', elinewidth=1, capsize=2)
# plt.scatter(xtot_bhd, ytot_bhd, marker='o', label='Rafter Baring Head Record (BHD)', color='black', s=size2)
# plt.scatter(x1_bhd, data1, color = colors[0], label = 'Monte Carlo Iteration 1', alpha = 0.35, marker = 'x', s = size2)
# plt.scatter(x1_bhd, data2, color = colors[1],  label = 'Monte Carlo Iteration 2', alpha = 0.35, marker = '^', s = size2)
# plt.scatter(x1_bhd, data3, color = colors[2],  label = 'Monte Carlo Iteration 3', alpha = 0.35, marker = 's', s = size2)
# plt.plot(xs, curve1, color = colors[0], alpha = 0.35, linestyle = 'dotted')
# plt.plot(xs, curve2, color = colors[1], alpha = 0.35, linestyle = 'dashed')
# plt.plot(xs, curve3, color = colors[2], alpha = 0.35, linestyle = 'dashdot')
# plt.plot(xs, means, color = 'red',  label = 'CCGCRV Smooth Values', alpha = 1, linestyle = 'solid')
# plt.plot(xs, means2, color = 'blue',  label = 'CCGCRV Trend Values', alpha = 1, linestyle = 'solid')
# plt.xlim([1989, 1991])
# plt.ylim([140, 170])
# plt.legend(loc=(1.04,0.5))
# xtr_subsplot.set_yticklabels([])
#
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figureS1.png',
#             dpi=300, bbox_inches="tight")
# # plt.show()
# plt.close()
#
# """
# Figure S2. Does the time CO2 sits in flask between collection and extraction impact 14C value?
# """
# fig = plt.figure(1)
# plt.scatter(time_extracts, delta, marker='o', label='Rafter Baring Head Record (BHD)', color=colors2[3], s=20)
# plt.legend()
# plt.title('Does the time CO2 sits in flask between collection and extraction impact 14C value? ')
# plt.xlabel('Decimal interval (Extraction - Collection)', fontsize=14)
# plt.ylabel('\u0394\u0394$^1$$^4$CO$_2$ (\u2030)', fontsize=14)  # label the y axis
# plt.savefig('C:/Users/clewis/IdeaProjects/GNS/radiocarbon_intercomparison/interlab_comparison/plots/FirstDraft_figureS2.png',
#             dpi=300, bbox_inches="tight")
# plt.close()