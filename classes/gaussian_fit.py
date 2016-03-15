# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Date created: 2016-03-14

import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize

class GaussianFit():

    def __init__(self, x_data, y_data, initial_guess=None, *args, **kwargs):
        self.x_data = x_data
        self.y_data = y_data
        
        if initial_guess is None:
            peak_pos =  np.argmax(y_data)
            peak_y = y_data[peak_pos]
            peak_x = x_data[peak_pos]

            # Find x where intensity is peak_y/2
            sigma_pos = -1
            i = 1
            while True:
                if peak_pos+i > len(y_data)-1:
                    break
                if y_data[peak_pos+i]/y_data[peak_pos]  <= 0.5:
                    sigma_pos = peak_pos+i
                    break
                i+=1 

            if sigma_pos == -1:
                i = 1
                while True:
                    if peak_pos-i < 0:
                        break
                    if y_data[peak_pos-i]/y_data[peak_pos]  <= 0.5:
                        sigma_pos = peak_pos-i
                        break
                    i+=1 

            if sigma_pos == -1:
                sigma_guess =  (max(x_data)-min(x_data))/2.0
            else:
                sigma_guess = abs(x_data[sigma_pos]-x_data[peak_pos])

            self.initial_guess = [peak_y, peak_x, sigma_guess, min(y_data)]
        else:
            self.initial_guess = initial_guess
        self.fit()

    def fit(self):
        # Gaussian fit -- http://stackoverflow.com/a/11507723/1501575
        # p0 is the initial guess for the fitting coefficients (A, mu and sigma above)
        coeff = []
        try:
            coeff, var_matrix = scipy.optimize.curve_fit(self.gauss_func, self.x_data, self.y_data, p0=self.initial_guess)
        except Exception as e:
            print 'Error finding parameters for Gaussian fit. Check library scipy or fitted data.'
            print e.message
        self.coeff = coeff

    def get_fit_params(self):
        return self.coeff

    def get_initial_guess(self):
        return self.initial_guess

    def get_fit_y_data(self):
        if self.coeff == []:
            return 0.0*self.x_data
        else:
            return self.gauss_func(self.x_data, *self.coeff)

    # Gaussian fit -- http://stackoverflow.com/a/11507723/1501575
    # p0 is the initial guess for the fitting coefficients (A, mu and sigma above)
    def gauss_func(self, x, *p):
        A, mu, sigma, B = p
        return A*np.exp(-(x-mu)**2/(2.*sigma**2)) + B

    def print_summary(self):
        if self.coeff == []:
            print 'Error fitting'
        else:
            print 'Fitted mean = ' + str(self.coeff[1])
            print 'Fitted standard deviation = ' + str(abs(self.coeff[2]))
            print 'Fitted FWHM = ' + str(self.get_fwhm())

    def get_fwhm(self):
        if self.coeff == []:
           return -1 
        else:
            return 2*np.sqrt(2*np.log(2))*abs(self.coeff[2]) # http://stackoverflow.com/a/10605108/1501575
