# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Date created: 2015-12-02
# Modified 2015-12-11
# Modified 2016-02-23/24

import Tkinter as tk
import tkFileDialog as fd
import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.figure import Figure
from matplotlib.mlab import griddata
import matplotlib.pyplot as plt
import matplotlib
import re
import numpy as np
# Custom classes
from tools import *
from custom_widgets import *
import timeit

class PlotWindow(tk.Toplevel):

    def __init__(self, plot_type='', master=None, parameters=dict(), data=list(), figure_number=None, application=None, *args, **kwargs):

        # Class parameters
        self.master = master
        self.parameters = parameters
        self.application = application
        self.data = data
        self.normalization_flag = False
        self.normalization_value = 1
        self.new_normalization_value = 1
        self.base_value = 0
        self.new_base_value = 0
        self.right_profile = None
        self.bottom_profile = None
        self.plot_type = plot_type
        self.widgets = dict() # To be used by class descendants

        # Init window
        tk.Toplevel.__init__(self, master=self.master)

        # Set window title
        self.title('Figure %.0f - %s - %s' % (figure_number, plot_type, (self.application.filename))) 

        self.protocol("WM_DELETE_WINDOW", self.action_close)
        self.fig = Figure()

        self.main_axes = self.fig.add_subplot(111)

        self.config_plot()
        self.add_default_widgets()

        # This functions loops every 10 seconds
        self.after(0, self.timer())

    def add_profiles_and_colorbar(self):

        # Right axes sharing Y axis
        divider = make_axes_locatable(self.main_axes)
        self.right_axes = divider.append_axes("right", size=1, pad=0.2, sharey=self.main_axes)

        # Colorbar axes
        self.colorbar_axes = divider.append_axes("right", size="5%", pad=0.2)

        # Bottom axes sharing X axis 
        self.bottom_axes = divider.append_axes("bottom", size=1, pad=0.2, sharex=self.main_axes)

    def add_default_widgets(self):

        # New container for buttons
        self.widgets['frame'] = ttk.Frame(self)

        # Normalization button
        self.widgets['btn_normalization'] = ttk.Button(self.widgets['frame'], text='Normalize')
        self.widgets['btn_normalization']["command"] = self.action_btn_normalization
        self.widgets['btn_normalization'].pack(side=tk.LEFT, padx=10, pady=5)

        # Export button
        self.widgets['btn_export'] = ttk.Button(self.widgets['frame'], text='Export data')
        self.widgets['btn_export']["command"] = self.action_btn_export
        self.widgets['btn_export'].pack(side=tk.LEFT, padx=10, pady=5)

        # Sum plots checkbox
        self.widgets['cb_auto_refresh'] = Checkbox(self.widgets['frame'], text='Auto refresh')
        self.widgets['cb_auto_refresh'].pack(side=tk.LEFT, padx=10, pady=10)

    def default_config(self):
        self.main_axes.get_xaxis().get_major_formatter().set_useOffset(False)
        self.main_axes.get_yaxis().get_major_formatter().set_useOffset(False)
        self.fig.set_tight_layout(True)

    def action_btn_export(self, *args, **kwargs):
        file_path = fd.asksaveasfilename()
        if file_path:
            line_num = 0
            for line in self.main_axes.get_lines():
                line_num += 1
                path = file_path + '_' + self.plot_type + '_' + str(line_num) + '.txt'
                np.savetxt(path, np.column_stack([line.get_xdata(), line.get_ydata()]))

    def action_cb_transferred_click(self, *args, **kwargs):
        self.refresh_plot()

    # This functions loops every 10 seconds
    def timer(self):
        auto_refresh = self.widgets['cb_auto_refresh'].var.get()
        if auto_refresh:
            self.application.update_current_selected_data()
            self.data = self.application.current_selected_data
            self.parameters = self.application.current_parameters
            self.refresh_plot()
        self.after(10000, self.timer)

    def show(self):
        # Show plot
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().pack()
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def config_plot(self):
        self.default_config()
        # Try to execute custom config from children, if exists
        try:
            self.config_plot_custom()
        except:
            pass

    def plot_redraw(self):
        self.config_plot()
        self.fig.canvas.draw()

    def columns_names_parse_as_int(self, columns_names):
        return_list = list()
        for name in columns_names:
            return_list.append(int(re.findall('([0-9]+)', str(name))[0]))
        return return_list

    def action_close(self):
        # Custom code when closing plot window
        plt.close(self.fig) 
        self.destroy()

    def roi_axis(self):
        ' Used on plots which have ROI as x axis '
        p = self.parameters
        rois_numbers = self.columns_names_parse_as_int(p['intensity_names'])
        if p['use_calibration'] and p['calibration_data']:
            try:
                self.bottom_axes.set_xlabel('Emitted energy (keV)')
                self.main_axes.set_xlabel('')
            except:
                self.main_axes.set_xlabel('Emitted energy (keV)')
            return self.rois_to_energies()
        else:
            try:
                self.bottom_axes.set_xlabel('ROI')
                self.main_axes.set_xlabel('')
            except:
                self.main_axes.set_xlabel('ROI')
            return rois_numbers

    def rois_to_energies(self):
        ' Used on plots which have ROI as x axis '
        p = self.parameters
        rois_numbers = self.columns_names_parse_as_int(p['intensity_names'])

        # Fitting
        calib = Tools.list_to_numpy(p['calibration_data']) 
        equation_parameters = np.polyfit(calib[:, 1], calib[:, 0], min(3, calib.shape[0]-1))
        self.application.log(str(equation_parameters))

        # Apply fitting equation to ROIs numbers
        energies = np.polyval(equation_parameters, rois_numbers)

        return energies

    def action_btn_normalization(self, *args, **kwargs):
        if not self.normalization_flag:
            self.normalization_flag = True
            self.widgets['btn_normalization']['text'] = 'Please double-click on y=0...'
            self.normalization_connection = self.canvas.mpl_connect('button_press_event', self.action_normalization_firstclick)
        else:
            self.widgets['btn_normalization']['text'] = 'Normalize'
            self.normalization_flag = False
            self.canvas.mpl_disconnect(self.normalization_connection)

    def action_normalization_firstclick(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.main_axes:
            y = event.ydata
            self.new_base_value = self.base_value + y * self.normalization_value
            self.canvas.mpl_disconnect(self.normalization_connection)
            self.normalization_connection = self.canvas.mpl_connect('button_press_event', self.action_normalization_secondclick)
            self.widgets['btn_normalization']['text'] = 'Please double-click on y=1...'

    def action_normalization_secondclick(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.main_axes:
            y = event.ydata
            self.normalization_value = (self.normalization_value * y + self.base_value - self.new_base_value)
            self.base_value = self.new_base_value
            self.action_btn_normalization()
            self.refresh_plot()

class RXESPlot(PlotWindow):

    def __init__(self, *args, **kwargs):

        # Inheritance
        PlotWindow.__init__(self, plot_type='RXES', *args, **kwargs)
        
        # Object properties
        self.calibration_flag = False
        self.profile_flag = False

        self.add_profiles_and_colorbar()

        # Init
        self.add_widgets()
        self.show()
        self.plot_emitted()

    def add_widgets(self):

        # Normalization button
        self.widgets['btn_calibration'] = ttk.Button(self.widgets['frame'], text='Calibrate energy')
        self.widgets['btn_calibration']["command"] = self.action_btn_calibration
        self.widgets['btn_calibration'].pack(side=tk.LEFT, padx=10, pady=5)

        # Transferred energy RXES checkbox
        self.widgets['cb_transferred'] = Checkbox(self.widgets['frame'], text='Energy transfer')
        self.widgets['cb_transferred'].pack(side=tk.LEFT, padx=10, pady=10)
        self.widgets['cb_transferred'].add_click_action(self.action_cb_transferred_click)

        # Profile checkbox
        self.widgets['btn_profile'] = ttk.Button(self.widgets['frame'], text='Profile center')
        self.widgets['btn_profile']["command"] = self.action_btn_profile
        self.widgets['btn_profile'].pack(side=tk.LEFT, padx=10, pady=5)

        # Pack buttons frame
        self.widgets['frame'].pack()

    def action_btn_calibration(self, *args, **kwargs):
        if not self.calibration_flag:
            self.calibration_flag = True
            if self.application:
                self.application.widgets['calib_tree'].clear()
            self.widgets['btn_calibration']['text'] = 'Please double-click on at least 2 elastically scattered peaks...'
            self.calibration_connection = self.canvas.mpl_connect('button_press_event', self.action_calibration_click)
        else:
            self.widgets['btn_calibration']['text'] = 'Calibrate energy'
            self.calibration_flag = False
            self.canvas.mpl_disconnect(self.calibration_connection)

    def action_btn_profile(self, *args, **kwargs):
        if not self.profile_flag:
            self.profile_flag = True
            self.widgets['btn_profile']['text'] = 'Please double-click at the new center...'
            self.profile_connection = self.canvas.mpl_connect('button_press_event', self.action_profile_click)
        else:
            self.widgets['btn_profile']['text'] = 'Profile center'
            self.profile_flag = False
            self.canvas.mpl_disconnect(self.profile_connection)

    def action_calibration_click(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.main_axes:
            x = event.xdata
            y = event.ydata
            if self.application:
                w = self.application.widgets['calib_tree']
                item_id = w.append(["%.1f" % x, "%.4f" % y], {'roi': x, 'energy': y})
                w.see(item_id)
                self.application.widgets['cb_calib'].var.set(True)

    def action_profile_click(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.main_axes:
            x = event.xdata
            y = event.ydata
            X, Y, Z, Xmesh, Ymesh, Zmesh = self.plot_data 
            self.plot_profiles(X, Y, Z, Xmesh, Ymesh, Zmesh, event.xdata, event.ydata)
            self.widgets['btn_profile']['text'] = 'Profile center'
            self.profile_flag = False
            self.canvas.mpl_disconnect(self.profile_connection)

    def set_profile_axes_limits(self, X, Y, Z, Xmesh, Ymesh, Zmesh):
        padding_factor = 0.1
        padding = (np.amax(Zmesh[:, :])-0)*padding_factor
        self.right_axes.axis([0-padding, np.amax(Zmesh[:, :])+padding, np.amin(Ymesh[:, :]), np.amax(Ymesh[:, :])])
        padding = (np.amax(Z[:, :])-0)*padding_factor
        self.bottom_axes.axis([np.amin(X[:, :]), np.amax(X[:, :]), 0-padding, np.amax(Z[:, :])+padding])
        # Profile axis steps configuration
        self.right_axes.get_xaxis().set_major_locator(matplotlib.ticker.FixedLocator([0, 0.5, 1]))
        self.bottom_axes.get_yaxis().set_major_locator(matplotlib.ticker.FixedLocator([0, 0.5, 1]))
        plt.setp(self.right_axes.get_yticklabels(), visible=False)

    def plot_transferred(self):

        # Plot Data
        self.update_plot_data('transferred') 
        X, Y, Z, Xmesh, Ymesh, Zmesh = self.plot_data

        # Show colormap scatter grid
        # self.main_axes.plot(Xmesh, Ymesh, 'o', markerfacecolor='black', markeredgecolor=None, markeredgewidth=0, markersize=2.0)

        # Colormap
        cs = self.main_axes.contourf(X, Y, Z, 100, stride=1)

        # Profiles
        self.plot_profiles(X, Y, Z, Xmesh, Ymesh, Zmesh)
        self.set_profile_axes_limits(X, Y, Z, Xmesh, Ymesh, Zmesh)

        # BUG ALERT! 2016-02-23 - When I tried using pyplot.colorbar instead of self.fig, TkInterTable stopped working with weird errors "wrong screen size" etc 
        self.fig.colorbar(cs, orientation="vertical", label="Intensity (a.u.)", ticks=np.linspace(0,1,11), cax=self.colorbar_axes)
        self.plot_redraw()

    def update_plot_data(self, plot_type):

        p = self.parameters
        # Intensities
        counts = self.data[:, p['intensity_columns']]
        # Normalize
        counts = np.divide(counts, np.amax(counts))
        # Axis
        roi_axis = self.roi_axis()
        energies_values = self.data[:, p['energy_column']].tolist()

        X = roi_axis
        Y = energies_values
        Z = counts

        if np.array(X).shape != Z.shape:
            X = np.transpose(np.tile(np.array(X)[:, np.newaxis], Z.shape[0]))
        if np.array(Y).shape != Z.shape:
            Y = np.tile(np.array(Y)[:, np.newaxis], Z.shape[1])

        if plot_type == 'emitted':

            self.plot_data = [X, Y, Z, X, Y, Z]

        elif plot_type == 'transferred':

            # Matrix of energy transfer
            X_transferred = Y - X

            # Some useful values
            min_x = float(np.amin(X))
            max_x = float(np.amax(X))
            x_average_step = (max_x-min_x)/(X.shape[0]-1)
            min_y = float(np.amin(Y))
            max_y = float(np.amax(Y))
            y_average_step = (max_y-min_y)/(Y.shape[1]-1)
            min_x_transferred = np.amin(X_transferred)
            max_x_transferred = np.amax(X_transferred)

            Xmesh, Ymesh = np.meshgrid(np.arange(min_x_transferred, max_x_transferred, x_average_step), np.arange(min_y, max_y, y_average_step))
            Zmesh = griddata(np.reshape(X_transferred,-1), np.reshape(Y,-1), np.reshape(counts,-1), Xmesh, Ymesh, interp='linear')

            self.plot_data = [X_transferred, Y, Z, Xmesh, Ymesh, Zmesh]

    def plot_emitted(self):

        # Plot Data
        self.update_plot_data('emitted') 
        X, Y, Z, Xmesh, Ymesh, Zmesh = self.plot_data

        # Colormap
        cs = self.main_axes.contourf(X, Y, Z, 100, stride=1)

        # Profiles
        self.plot_profiles(X, Y, Z, Xmesh, Ymesh, Zmesh)
        self.set_profile_axes_limits(X, Y, Z, Xmesh, Ymesh, Zmesh)
        
        # BUG ALERT! When I tried using pyplot.colorbar instead of self.fig.colorbar below, TkInterTable stopped working with weird errors ("wrong screen size", etc.)
        self.fig.colorbar(cs, orientation="vertical", label="Intensity (a.u.)", ticks=np.linspace(0,1,11), cax=self.colorbar_axes)
        self.plot_redraw()

    def find_closest_in_array(self, X, x0):
            # Find x position in array X
            x_pos = 0
            x_index = -1
            for x in X:
                if x_pos > 0:
                    if abs(x-x0) >= last_diff:
                        x_index = x_pos-1
                        break
                last_diff = abs(x-x0) 
                x_pos += 1
            # It max be the last item of the array
            if x_index == -1:
                x_index = x_pos-1
            return x_index

    def plot_profiles(self, X, Y, Z, Xmesh=None, Ymesh=None, Zmesh=None, profile_x=None, profile_y=None):

        # Getting profile center position
        if profile_x is None or profile_y is None: 
            # If profile_x and profile_y not defined, use max intensity as center
            x_index, y_index = np.unravel_index(Z.argmax(), Z.shape)
            x_index_mesh, y_index_mesh = np.unravel_index(Zmesh.argmax(), Zmesh.shape)
        else:
            # Find the closest positions (x, y) to the ones clicked by the user
            x_index = self.find_closest_in_array(Y[:, 0], profile_y)
            y_index = self.find_closest_in_array(X[x_index, :], profile_x)
            x_index_mesh = self.find_closest_in_array(Ymesh[:, 0], profile_y)
            y_index_mesh = self.find_closest_in_array(Xmesh[x_index_mesh, :], profile_x)

        # Try to remove horizontal and vertical line, if they already exist
        try:
            self.hline.remove()
            self.vline.remove()
        except:
            pass

        # Print crossbar on profile position
        self.hline = self.main_axes.hlines(Y[x_index, y_index], np.amin(X), np.amax(X), linewidth=2, color='fuchsia', linestyles='dashed') 
        self.vline = self.main_axes.vlines(X[x_index, y_index], np.amin(Y), np.amax(Y), linewidth=2, color='fuchsia', linestyles='dashed') 

        # Profile at right axes
        if self.right_profile is None:
            self.right_profile = self.right_axes.plot(Zmesh[:, y_index_mesh], Ymesh[:, y_index_mesh])[0] # Line plot
            self.right_profile_scatter = self.right_axes.plot(Zmesh[:, y_index_mesh], Ymesh[:, y_index_mesh], 'o', markerfacecolor='black', markeredgecolor=None, markeredgewidth=0, markersize=2.0)[0] # Scatter plot
        else:
            self.right_profile.set_xdata(Zmesh[:, y_index_mesh])
            self.right_profile.set_ydata(Ymesh[:, y_index_mesh])
            self.right_profile_scatter.set_xdata(Zmesh[:, y_index_mesh])
            self.right_profile_scatter.set_ydata(Ymesh[:, y_index_mesh])

        # Profile at bottom axes
        if self.bottom_profile is None:
            self.bottom_profile = self.bottom_axes.plot(X[x_index, :], Z[x_index, :])[0]
            self.bottom_profile_scatter = self.bottom_axes.plot(X[x_index, :], Z[x_index, :], 'o', markerfacecolor='black', markeredgecolor=None, markeredgewidth=0, markersize=2.0)[0] # Scatter plot
        else:
            self.bottom_profile.set_xdata(Xmesh[x_index_mesh, :])
            self.bottom_profile.set_ydata(Zmesh[x_index_mesh, :])
            self.bottom_profile_scatter.set_xdata(Xmesh[x_index_mesh, :])
            self.bottom_profile_scatter.set_ydata(Zmesh[x_index_mesh, :])

        # Redraw changes
        self.fig.canvas.draw()

    def config_plot_custom(self):
        self.main_axes.set_ylabel('Incoming energy (keV)')
        # Hide main axes bottom label
        plt.setp(self.main_axes.get_xticklabels(), visible=False)
        self.main_axes.set_xlabel('')

    def refresh_plot(self):
        self.main_axes.clear()
        self.right_axes.clear()
        self.bottom_axes.clear()
        self.colorbar_axes.clear()
        plot_transferred = self.widgets['cb_transferred'].value()
        self.right_profile = None
        self.bottom_profile = None
        if plot_transferred:
            self.plot_transferred()
        else:
            self.plot_emitted()
        self.fig.canvas.draw()

class HERFDPlot(PlotWindow):

    def __init__(self, *args, **kwargs):
        PlotWindow.__init__(self, plot_type='HERFD', *args, **kwargs)
        self.add_widgets()
        self.show()
        self.plot_multiple()

    def add_widgets(self):

        # Sum plots checkbox
        self.widgets['cb_sum'] = Checkbox(self.widgets['frame'], text='Sum')
        self.widgets['cb_sum'].pack(side=tk.LEFT, padx=10, pady=10)
        self.widgets['cb_sum'].add_click_action(self.action_cb_sum_click)

        # Pack buttons frame
        self.widgets['frame'].pack()

    def plot_multiple(self):
        p = self.parameters
        self.main_axes.clear()

        normalized_data = np.divide(self.data[:, p['intensity_columns']], self.normalization_value) - self.base_value/self.normalization_value
        energies_data = np.repeat(self.data[:, p['energy_column']][:, np.newaxis], normalized_data.shape[1], axis=1)
        self.main_axes.plot(energies_data, normalized_data)
        self.plot_redraw()

    def plot_sum(self):
        p = self.parameters
        self.main_axes.clear()

        normalized_data = np.sum(np.divide(self.data[:, p['intensity_columns']], self.normalization_value), axis=1) - self.base_value/self.normalization_value

        # Add plot line of the sum
        self.main_axes.plot(self.data[:, p['energy_column']], normalized_data)
        self.plot_redraw()

    def config_plot_custom(self):
        self.main_axes.set_xlabel('Incoming energy (keV)')
        self.main_axes.set_ylabel('Intensity')

    def action_cb_sum_click(self, *args, **kwargs):
        self.refresh_plot()

    def refresh_plot(self):
        plot_sum = self.widgets['cb_sum'].value()
        if plot_sum:
            self.plot_sum()
        else:
            self.plot_multiple()

class XESPlot(PlotWindow):

    def __init__(self, *args, **kwargs):
        PlotWindow.__init__(self, plot_type='XES', *args, **kwargs)
        self.add_widgets()
        self.show()
        self.plot_multiple()

    def add_widgets(self):

        # Sum plots checkbox
        self.widgets['cb_sum'] = Checkbox(self.widgets['frame'], text='Sum')
        self.widgets['cb_sum'].pack(side=tk.LEFT)
        self.widgets['cb_sum'].add_click_action(self.action_cb_sum_click)

        # Pack buttons frame
        self.widgets['frame'].pack()

    def plot_multiple(self):
        p = self.parameters
        self.main_axes.clear()

        # Generate plot lines
        rows, columns = self.data.shape
        roi_axis = self.roi_axis()

        normalized_data = np.divide(self.data[:, min(p['intensity_columns']):max(p['intensity_columns'])+1], self.normalization_value) - self.base_value/self.normalization_value
        rois_data = np.repeat(np.asarray(roi_axis)[:, np.newaxis], normalized_data.shape[0], axis=1)
        self.main_axes.plot(rois_data, np.transpose(normalized_data))
        self.plot_redraw()

    def plot_sum(self):
        p = self.parameters
        self.main_axes.clear()

        # Generate plot lines
        rows, columns = self.data.shape
        roi_axis = self.roi_axis()

        normalized_data = np.sum(np.divide(self.data[0:rows, min(p['intensity_columns']):max(p['intensity_columns'])+1], self.normalization_value), axis=0) - self.base_value/self.normalization_value
        # Add plot line
        self.main_axes.plot(roi_axis, normalized_data)
        self.plot_redraw()

    def config_plot_custom(self):
        self.main_axes.set_ylabel('Intensity')

    def action_cb_sum_click(self, *args, **kwargs):
        self.refresh_plot()

    def refresh_plot(self):
        plot_sum = self.widgets['cb_sum'].value()
        if plot_sum:
            self.plot_sum()
        else:
            self.plot_multiple()
