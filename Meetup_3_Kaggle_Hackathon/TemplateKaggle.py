
# imports 
import pandas as pd
import numpy as np
from sklearn import tree

# Read in Data
df = pd.read_csv('train.csv')

# Inspect the Data
df.head()

# Investigate the Data# Inves 
df.info()

# If you want to clean up any data do so here.
# Is the data good quality? Good we clean it up? are there null values? Are there weird values?

# If you want to engineer any features do so here
# For example there is a lot of information that could be gained from the ticket number if you do some research

# Train a model here
train_X = df.loc[:, df.columns != 'Survived']
train_Y = df['Survived']

# apply a model here
test = pd.read_csv('test.csv')

# function which assumes all women survived.
def genderToLabel(gender):
    if(gender == 'female'):
        return 1
    else:
        return 0

test['Survived'] = test.Sex.apply(genderToLabel)
test.head()

# write your submission .csv
def convertDataForSubmission(data):
    data[['PassengerId','Survived']].to_csv("submission.csv", index=False)
    
convertDataForSubmission(test)