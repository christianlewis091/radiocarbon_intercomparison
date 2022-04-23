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

"""
Because I’ll need a harmonized dataset as a reference to understand the
tree-rings, I’m going to create a python file to do dataset harmonization.
I know we may change the corrections for the later half of the available
data; however, I can at least get the code ready so we can quickly
run it later and get the answer.
"""

# What are the current offsets (these are subject to change!)
# 1986 - 1991: Add 1.80 +- 0.18 to Heidelberg Data
# 1991 - 1994: Add 1.88 +- 0.16 to Heidelberg Data
# 1994 - 2006: No offset applied
# 2006 - 2009: Add 0.49 +- 0.07 to Heidelberg
# 2009 - 2012: Apply NO offset
# 2012 - 2016: Subtract 0.52 +- 0.06 to Heidelberg.

# steps to harmonize the dataset
# 1. Check what Rachel did. (see her page 203. It seems she just applied
# the offsets that she calculated and combined the datasets.

# 2. Load up all the data.

# 3. Index them according to the times above, and apply the offsets.

# 4. Merge the datasets into one.

# 5. Create a template of x-values to output

# (in the future, users can just add their samples x-values to this template and
# get the output they need to do subtraction)

# 6. Re-smooth the data using CCGCRV getTrendValues, with specific x's in mind
# (what x-values do I want to return that will be most useful?

"""
#######################################################################
#######################################################################
#######################################################################
#######################################################################
EXECUTE THE ABOVE STEPS
#######################################################################
#######################################################################
#######################################################################
#######################################################################
"""
""" STEP 1: LOAD UP AND TIDY THE DATA"""
heidelberg = pd.read_excel(r'G:\My Drive\Work\GNS Radiocarbon Scientist\The Science\Datasets'
                           r'\heidelberg_cape_grim.xlsx', skiprows=40)
# Baring Head data excel file
baringhead = pd.read_excel(r'G:\My Drive\Work\GNS Radiocarbon Scientist\The Science\Datasets'
                           r'\BHD_14CO2_datasets_20211013.xlsx')

# tidy up the data
# add decimal dates to DataFrame if not there already
x_init_heid = heidelberg['Average pf Start-date and enddate']  # x-values from heidelberg dataset
x_init_heid = long_date_to_decimal_date(x_init_heid)
heidelberg['Decimal_date'] = x_init_heid  # add these decimal dates onto the dataframe

# drop NaN's in the column I'm most interested in
heidelberg = heidelberg.dropna(subset=['D14C'])
heidelberg = heidelberg.loc[(heidelberg['D14C'] > 10)]
baringhead = baringhead.dropna(subset=['DELTA14C'])

# snip out 1995 - 2005, and 2009 - 2012
snip = baringhead.loc[(baringhead['DEC_DECAY_CORR'] < 1994)]
snip2 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] > 2006) & (baringhead['DEC_DECAY_CORR'] < 2009)]
snip3 = baringhead.loc[(baringhead['DEC_DECAY_CORR'] > 2012)]
snip = pd.merge(snip, snip2, how='outer')
snip = pd.merge(snip, snip3, how='outer')
baringhead = snip.reset_index(drop=True)
# plt.scatter(baringhead['DEC_DECAY_CORR'], baringhead['DELTA14C'])
# plt.show()

""" STEP 2: INDEX THE DATA ACCORDING TO TIMES LISTED ABOVE"""
# Baring head data does not need indexing because we will not apply corrections to it
# What are the current offsets (these are subject to change!)

# 1986 - 1991: Add 1.80 +- 0.18 to Heidelberg Data
# 1991 - 1994: Add 1.88 +- 0.16 to Heidelberg Data
# 1994 - 2006: No offset applied
# 2006 - 2009: Add 0.49 +- 0.07 to Heidelberg
# 2009 - 2012: Apply NO offset
# 2012 - 2016: Subtract 0.52 +- 0.06 to Heidelberg.

h1 = heidelberg.loc[(heidelberg['Decimal_date'] < 1991)].reset_index()
h2 = heidelberg.loc[(heidelberg['Decimal_date'] > 1991) & (heidelberg['Decimal_date'] < 1994)].reset_index()
h3 = heidelberg.loc[(heidelberg['Decimal_date'] > 1994) & (heidelberg['Decimal_date'] < 2006)].reset_index()
h4 = heidelberg.loc[(heidelberg['Decimal_date'] > 2006) & (heidelberg['Decimal_date'] < 2009)].reset_index()
h5 = heidelberg.loc[(heidelberg['Decimal_date'] > 2009) & (heidelberg['Decimal_date'] < 2012)].reset_index()
h6 = heidelberg.loc[(heidelberg['Decimal_date'] > 2012) & (heidelberg['Decimal_date'] < 2016)].reset_index()
"""
In order to apply the offsets, I'm going to add a new column with the new value, rather than try 
to change to original value
"""
offset1 = 1.80
offset2 = 1.88
offset3 = 0
offset4 = 0.49
offset5 = 0
offset6 = -.52
error1 = .18
error2 = .16
error3 = 0
error4 = 0.07
error5 = 0
error6 = 0.06

h1['D14C_corrected'] = h1['D14C'] + offset1
h2['D14C_corrected'] = h2['D14C'] + offset2
h3['D14C_corrected'] = h3['D14C'] + offset3
h4['D14C_corrected'] = h4['D14C'] + offset4
h5['D14C_corrected'] = h5['D14C'] + offset5
h6['D14C_corrected'] = h6['D14C'] + offset6
h1['D14C_corr_err'] = np.sqrt(h1['weightedstderr_D14C']**2 + error1**2)
h2['D14C_corr_err'] = np.sqrt(h2['weightedstderr_D14C']**2 + error2**2)
h3['D14C_corr_err'] = np.sqrt(h3['weightedstderr_D14C']**2 + error3**2)
h4['D14C_corr_err'] = np.sqrt(h4['weightedstderr_D14C']**2 + error4**2)
h5['D14C_corr_err'] = np.sqrt(h5['weightedstderr_D14C']**2 + error5**2)
h6['D14C_corr_err'] = np.sqrt(h6['weightedstderr_D14C']**2 + error6**2)
# print(heidelberg.columns)


""" STEP 4: MERGE ALL THE DATA! """

# TODO: need to change all the column names to be the same!
# You can't merge Baring Head and Heidelberg together that easy
# because all the column names are different!

# df1.merge(df2, left_on='lkey', right_on='rkey')
#
#
#
# harmonized = pd.merge(baringhead, h1)
# # harmonized = pd.merge(harmonized, h2, how='outer')
# # harmonized = pd.merge(harmonized, h3, how='outer')
# # harmonized = pd.merge(harmonized, h4, how='outer')
# # harmonized = pd.merge(harmonized, h5, how='outer')
# # harmonized = pd.merge(harmonized, h6, how='outer')