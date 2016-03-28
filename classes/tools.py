# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Date created: 2015-12-02
# Modified: 2015-12-11

import pandas
import numpy as np

class Tools:

    @staticmethod
    def list_to_numpy(data):
        # Process list of dicts (data)
        df = pandas.DataFrame(data, dtype='float') # use Pandas to convert to dataframe
        nparray = df.as_matrix() # convert from Pandas to Numpy
        return nparray

    @staticmethod
    def mixed_array_to_float(data):
        # I could not find any nice way of doing this: converting
        # a mixed string/float numpy array to a dataframe, so I have to (1) convert to lists,
        # then (2) convert to panda, and then finally (3) convert back to numpy
        lists = data.tolist()
        df = pandas.DataFrame(lists, dtype='float') # use Pandas to convert to dataframe
        nparray = df.as_matrix() # convert from Pandas to Numpy
        return nparray
