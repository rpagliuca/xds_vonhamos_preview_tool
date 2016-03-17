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
from gaussian_fit import *
from profiler import *
import timeit

class PlotWindow(tk.Toplevel):

    def __init__(self, plot_type='', master=None, parameters=dict(), data=list(), figure_number=None, application=None, *args, **kwargs):

        # Class parameters
        self.master = master
        self.parameters = parameters
        self.application = application
        self.data = data
        self.normalization_flag = False
        self.normalization_single_flag = False
        self.normalization_value = 1
        self.new_normalization_value = 1
        self.base_value = 0
        self.new_base_value = 0
        self.right_profile = None
        self.bottom_profile = None
        self.plot_type = plot_type
        self.widgets = dict() # To be used by class descendants
        self.picker_tolerance = 5.0
        self.selected_artist = None
        self.profiler = Profiler()
        self.figure_number = figure_number

        # Init window
        tk.Toplevel.__init__(self, master=self.master)

        # Set window title
        if figure_number is not None:
            self.title('Figure %.0f - %s - %s' % (figure_number, plot_type, (self.application.filename))) 
        else:
            self.title('Clipboard') 

        self.protocol("WM_DELETE_WINDOW", self.action_close)
        self.fig = Figure()

        self.main_axes = self.fig.add_subplot(111)

        self.config_plot()
        self.add_default_widgets()

        # This functions loops every 10 seconds
        self.after(0, self.timer())

    def artist_label_prefix(self):
        return 'Fig. ' + str(self.figure_number)

    def onpick(self, event):

        xy = [ event.mouseevent.x, event.mouseevent.y ]
        xydata = [event.mouseevent.xdata, event.mouseevent.ydata]

        # Reset previous selected artist
        if self.selected_artist is not None:
            if xy == self.selected_artist['xy'] and xydata == self.selected_artist['xydata']:
                return # Make sure that only one artist is selected by a single mouseclick
            self.selected_artist['artist'].set_color(self.selected_artist['color'])  
            self.selected_artist['artist'].set_linewidth(self.selected_artist['width'])

        if self.selected_artist is not None and self.selected_artist['artist'] is event.artist:
            self.selected_artist = None # Clear selection if clicking twice on the same object
        else:
            # Store current selected artist
            self.selected_artist = {
                'artist': event.artist,
                'color': event.artist.get_color(),
                'width': event.artist.get_linewidth(),
                'xy': xy,
                'xydata': xydata
            }
            # Change some attributes to show the user that the artist is currently selected
            event.artist.set_color('purple')
            event.artist.set_linewidth(3)
            self.log('* Selected plot object: ' + event.artist.get_label())

        # Redraw changes
        self.fig.canvas.draw()

    def add_profiles_and_colorbar(self):

        # Right axes sharing Y axis
        divider = make_axes_locatable(self.main_axes)
        self.right_axes = divider.append_axes("right", size=1, pad=0.2, sharey=self.main_axes)

        # Colorbar axes
        self.colorbar_axes = divider.append_axes("right", size="5%", pad=0.2)

        # Bottom axes sharing X axis 
        self.bottom_axes = divider.append_axes("bottom", size=1, pad=0.2, sharex=self.main_axes)

    def add_default_widgets(self):

        ##########################
        # Top frame
        ##########################

        # New container for buttons
        self.widgets['frame_widgets'] = ttk.Frame(self)

        # Normalization button
        self.widgets['btn_normalization'] = ttk.Button(self.widgets['frame_widgets'], text='Normalize')
        self.widgets['btn_normalization']["command"] = self.action_btn_normalization
        self.widgets['btn_normalization'].pack(side=tk.LEFT, padx=10, pady=5)

        # Export button
        self.widgets['btn_export'] = ttk.Button(self.widgets['frame_widgets'], text='Export data')
        self.widgets['btn_export']["command"] = self.action_btn_export
        self.widgets['btn_export'].pack(side=tk.LEFT, padx=10, pady=5)

        # Sum plots checkbox
        #self.widgets['cb_auto_refresh'] = Checkbox(self.widgets['frame_widgets'], text='Auto refresh')
        #self.widgets['cb_auto_refresh'].pack(side=tk.LEFT, padx=10, pady=10)

        # Pack buttons frame
        self.widgets['frame_widgets'].grid(row=0, column=0)

        ##########################
        # Selection artist widgets
        ##########################

        # New container for buttons
        self.widgets['frame_artist_widgets'] = ttk.Frame(self)

        # Pack buttons frame
        self.widgets['frame_artist_widgets'].grid(row=1, column=0)

        # Copy to desktop plot
        self.widgets['btn_copy'] = ttk.Button(self.widgets['frame_artist_widgets'], text='Copy to clipboard')
        self.widgets['btn_copy']["command"] = self.action_btn_copy
        self.widgets['btn_copy'].pack(side=tk.LEFT, padx=10, pady=5)

        ##########################
        # Bottom frame
        ##########################

        self.widgets['bottom_frame'] = ttk.Frame(self)
        #self.widgets['btn_test'] = ttk.Button(self.widgets['bottom_frame'], text='Teste')
        #self.widgets['btn_test'].grid(row=0, column=0, sticky='nsew')
        self.widgets['log_listbox'] = ScrollableListbox(self.widgets['bottom_frame'], height=4)
        self.widgets['log_listbox'].grid(row=0, column=0, sticky='nsew')
        self.widgets['bottom_frame'].grid(row=3, column=0, sticky="nsew", pady=10, padx=10)

        # Elastic columns
        tk.Grid.columnconfigure(self.widgets['bottom_frame'], 0, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)
        tk.Grid.rowconfigure(self, 2, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=0)

    def log(self, text):
        self.widgets['log_listbox'].append(text)
        self.widgets['log_listbox'].see(tk.END)

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

    def action_btn_copy(self, *args, **kwargs):
        if self.application is not None and self.selected_artist is not None:
            if self.application.clipboard_plot is None:
                self.application.clipboard_plot = ClipboardPlot(master = self.application.master, application = self.application)
            self.application.clipboard_plot.main_axes.plot(self.selected_artist['artist'].get_xdata(), self.selected_artist['artist'].get_ydata(), picker=self.picker_tolerance, label=self.selected_artist['artist'].get_label())
            self.application.clipboard_plot.fig.canvas.draw()

    def action_cb_transferred_click(self, *args, **kwargs):
        self.refresh_plot()

    # This functions loops every 10 seconds
    def timer(self):
        #auto_refresh = self.widgets['cb_auto_refresh'].var.get()
        auto_refresh = False
        if auto_refresh:
            self.application.update_current_selected_data()
            self.data = self.application.current_selected_data
            self.parameters = self.application.current_parameters
            self.refresh_plot()
        self.after(10000, self.timer)

    def show(self):
        # Show plot
        self.widgets['canvas_frame'] = ttk.Frame(self)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.widgets['canvas_frame'])
        self.canvas.show()
        self.canvas.get_tk_widget().pack()
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.widgets['canvas_frame'])
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('pick_event', self.onpick)
        self.widgets['canvas_frame'].grid(row=2, column=0, sticky="nsew", pady=10, padx=10)

    def config_plot(self):
        self.default_config()
        # Try to execute custom config from children, if exists
        try:
            self.config_plot_custom()
        except AttributeError: # If method does not exist
            pass

    def plot_redraw(self):
        self.config_plot()
        self.fig.canvas.draw()

    def columns_names_parse_as_int(self, columns_names):
        return_list = list()
        for name in columns_names:
            return_list.append(int(re.findall('([0-9]+)', str(name))[0]))
        return return_list

    def columns_names_parse_as_float(self, columns_names):
        return_list = list()
        for name in columns_names:
            return_list.append(float(re.findall('([0-9]+)', str(name))[0]))
        return np.array(return_list)

    def action_close(self):
        # Custom code when closing plot window
        try:
            self.action_close_custom()
        except AttributeError: # If method does not exist
            pass
        plt.close(self.fig) 
        self.destroy()

    def roi_axis(self):
        ' Used on plots which have ROI as x axis '
        p = self.parameters
        rois_numbers = self.columns_names_parse_as_float(p['intensity_names'])
        if p['use_calibration'] and p['calibration_data']:
            try:
                self.bottom_axes.set_xlabel('Energy (keV)')
                self.main_axes.set_xlabel('')
            except:
                self.main_axes.set_xlabel('Energy (keV)')
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
        self.log('* Energy calibration coefficients: ' + str(equation_parameters))

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
        self.widgets['btn_calibration'] = ttk.Button(self.widgets['frame_widgets'], text='Calibrate energy')
        self.widgets['btn_calibration']["command"] = self.action_btn_calibration
        self.widgets['btn_calibration'].pack(side=tk.LEFT, padx=10, pady=5)

        # Transferred energy RXES checkbox
        self.widgets['cb_transferred'] = Checkbox(self.widgets['frame_widgets'], text='Energy transfer')
        self.widgets['cb_transferred'].pack(side=tk.LEFT, padx=10, pady=10)
        self.widgets['cb_transferred'].add_click_action(self.action_cb_transferred_click)

        # Profile checkbox
        self.widgets['btn_profile'] = ttk.Button(self.widgets['frame_widgets'], text='Profile center')
        self.widgets['btn_profile']["command"] = self.action_btn_profile
        self.widgets['btn_profile'].pack(side=tk.LEFT, padx=10, pady=5)

        # Pack buttons frame
        self.widgets['frame_widgets'].grid(row=0, column=0)

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
        Z = counts.astype(float)

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
        cs = self.main_axes.contourf(X, Y, Z, 100, stride=1, picker=self.picker_tolerance)

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

        # Gaussian fit for right axes
        ylim = self.right_axes.get_ylim()
        y_index_min = self.find_closest_in_array(Ymesh[:, y_index_mesh], ylim[0])
        y_index_max = self.find_closest_in_array(Ymesh[:, y_index_mesh], ylim[1])
        y_index_min, y_index_max = sorted([y_index_min, y_index_max]) # Sort lower and higher indices
        fit = GaussianFit(np.nan_to_num(Ymesh[y_index_min:y_index_max+1, y_index_mesh]), np.nan_to_num(Zmesh[y_index_min:y_index_max+1, y_index_mesh]))
        self.log('* Right axes Gaussian fit FWHM: ' + str(fit.get_fwhm()))

        # Profile at right axes
        if self.right_profile is None:
            self.right_profile = self.right_axes.plot(Zmesh[:, y_index_mesh], Ymesh[:, y_index_mesh], picker=self.picker_tolerance)[0] # Line plot
            self.right_profile_scatter = self.right_axes.plot(Zmesh[:, y_index_mesh], Ymesh[:, y_index_mesh], 'o', markerfacecolor='black', markeredgecolor=None, markeredgewidth=0, markersize=2.0)[0] # Scatter plot
            self.right_profile_fit = self.right_axes.plot(fit.get_fit_y_data(), Ymesh[y_index_min:y_index_max+1, y_index_mesh], '--', color='red', linewidth=2.0, picker=self.picker_tolerance)[0] # Fit plot
        else:
            self.right_profile.set_xdata(Zmesh[:, y_index_mesh])
            self.right_profile.set_ydata(Ymesh[:, y_index_mesh])
            self.right_profile_scatter.set_xdata(Zmesh[:, y_index_mesh])
            self.right_profile_scatter.set_ydata(Ymesh[:, y_index_mesh])
            self.right_profile_fit.set_xdata(fit.get_fit_y_data())
            self.right_profile_fit.set_ydata(Ymesh[y_index_min:y_index_max+1, y_index_mesh])

        # Gaussian fit for bottom axes
        xlim = self.bottom_axes.get_xlim()
        x_index_min = self.find_closest_in_array(X[x_index, :], xlim[0])
        x_index_max = self.find_closest_in_array(X[x_index, :], xlim[1])
        x_index_min, x_index_max = sorted([x_index_min, x_index_max]) # Sort lower and higher indices
        fit = GaussianFit(X[x_index, x_index_min:x_index_max+1], Z[x_index, x_index_min:x_index_max+1])
        self.log('* Bottom axes Gaussian fit FWHM: ' + str(fit.get_fwhm()))

        # Profile at bottom axes
        if self.bottom_profile is None:
            self.bottom_profile = self.bottom_axes.plot(X[x_index, :], Z[x_index, :], picker=self.picker_tolerance)[0]
            self.bottom_profile_scatter = self.bottom_axes.plot(X[x_index, :], Z[x_index, :], 'o', markerfacecolor='black', markeredgecolor=None, markeredgewidth=0, markersize=2.0)[0] # Scatter plot
            self.bottom_profile_fit = self.bottom_axes.plot(X[x_index, x_index_min:x_index_max+1], fit.get_fit_y_data(), '--', color='red', linewidth=2.0, picker=self.picker_tolerance)[0] # Fit plot
        else:
            self.bottom_profile.set_xdata(X[x_index, :])
            self.bottom_profile.set_ydata(Z[x_index, :])
            self.bottom_profile_scatter.set_xdata(X[x_index, :])
            self.bottom_profile_scatter.set_ydata(Z[x_index, :])
            self.bottom_profile_fit.set_xdata(X[x_index, x_index_min:x_index_max+1])
            self.bottom_profile_fit.set_ydata(fit.get_fit_y_data())

        label = '<Fig. ' + str(self.figure_number) + '; Profile at x=' + str(X[0, y_index_mesh]) + '>'
        self.right_profile.set_label(label)
        label = '<Fig. ' + str(self.figure_number) + '; Gaussian fit at x=' + str(X[0, y_index_mesh]) + '; FWHM = ' + str(fit.get_fwhm()) + '>'
        self.right_profile_fit.set_label(label)
        label = '<Fig. ' + str(self.figure_number) + '; Profile at y=' + str(Y[x_index, 0]) + '>'
        self.bottom_profile.set_label(label)
        label = '<Fig. ' + str(self.figure_number) + '; Gaussian fit at y=' + str(Y[x_index, 0]) + '; FWHM = ' + str(fit.get_fwhm()) + '>'
        self.bottom_profile_fit.set_label(label)

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
        self.widgets['cb_sum'] = Checkbox(self.widgets['frame_widgets'], text='Sum')
        self.widgets['cb_sum'].pack(side=tk.LEFT, padx=10, pady=10)
        self.widgets['cb_sum'].add_click_action(self.action_cb_sum_click)

        # Pack buttons frame
        self.widgets['frame_widgets'].grid(row=0, column=0)

    def plot_multiple(self):
        p = self.parameters
        self.main_axes.clear()

        normalized_data = np.divide(self.data[:, p['intensity_columns']], self.normalization_value) - self.base_value/self.normalization_value
        for roi_index in range(len(p['intensity_columns'])):
            label = '<Fig. ' + str(self.figure_number) + '; ROI = ' + p['intensity_names'][roi_index] + '>'
            self.main_axes.plot(self.data[:, p['energy_column']], normalized_data[:, roi_index], picker=self.picker_tolerance, label=label)

        self.plot_redraw()

    def plot_sum(self):
        p = self.parameters
        self.main_axes.clear()

        normalized_data = np.sum(np.divide(self.data[:, p['intensity_columns']], self.normalization_value), axis=1) - self.base_value/self.normalization_value

        # Add plot line of the sum
        label = '<Fig. ' + str(self.figure_number) + '; Sum>'
        self.main_axes.plot(self.data[:, p['energy_column']], normalized_data, picker=self.picker_tolerance, label=label)
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
        self.widgets['cb_sum'] = Checkbox(self.widgets['frame_widgets'], text='Sum')
        self.widgets['cb_sum'].pack(side=tk.LEFT)
        self.widgets['cb_sum'].add_click_action(self.action_cb_sum_click)

        # Pack buttons frame
        self.widgets['frame_widgets'].grid(row=0, column=0)

    def plot_multiple(self):
        p = self.parameters
        self.main_axes.clear()

        # Generate plot lines
        rows, columns = self.data.shape
        roi_axis = self.roi_axis()

        normalized_data = np.divide(self.data[:, min(p['intensity_columns']):max(p['intensity_columns'])+1], self.normalization_value) - self.base_value/self.normalization_value
        for row_index in range(len(normalized_data)):
            label = '<Fig. ' + str(self.figure_number) + '; Row = ' + str(self.data[row_index, p['row_number_column']]) + '; Energy = ' + str(self.data[row_index, p['energy_column']]) + '>'

            self.main_axes.plot(roi_axis, normalized_data[row_index, :], picker=self.picker_tolerance, label=label)

        self.plot_redraw()

    def plot_sum(self):
        p = self.parameters
        self.main_axes.clear()

        # Generate plot lines
        rows, columns = self.data.shape
        roi_axis = self.roi_axis()

        normalized_data = np.sum(np.divide(self.data[0:rows, min(p['intensity_columns']):max(p['intensity_columns'])+1], self.normalization_value), axis=0) - self.base_value/self.normalization_value
        # Add plot line
        label = '<Fig. ' + str(self.figure_number) + '; Sum>'
        self.main_axes.plot(roi_axis, normalized_data, picker=self.picker_tolerance, label=label)
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

class ClipboardPlot(PlotWindow):

    def __init__(self, *args, **kwargs):

        # Inheritance
        PlotWindow.__init__(self, plot_type='Clipboard', *args, **kwargs)
        
        # Init
        self.add_widgets()
        self.show()

    def add_widgets(self):

        # Remove button
        self.widgets['btn_delete'] = ttk.Button(self.widgets['frame_artist_widgets'], text='Remove plot')
        self.widgets['btn_delete']["command"] = self.action_btn_delete
        self.widgets['btn_delete'].pack(side=tk.LEFT, padx=10, pady=5)

        # Swap X,Y button
        self.widgets['btn_swap_xy'] = ttk.Button(self.widgets['frame_artist_widgets'], text='Swap X-Y')
        self.widgets['btn_swap_xy']["command"] = self.action_btn_swap_xy
        self.widgets['btn_swap_xy'].pack(side=tk.LEFT, padx=10, pady=5)

        # Normalization button
        self.widgets['btn_normalization_single'] = ttk.Button(self.widgets['frame_artist_widgets'], text='Normalize plot')
        self.widgets['btn_normalization_single']["command"] = self.action_btn_normalization_single
        self.widgets['btn_normalization_single'].pack(side=tk.LEFT, padx=10, pady=5)

        # Pack buttons frame
        self.widgets['frame_widgets'].grid(row=0, column=0)

    def action_btn_normalization_single(self, *args, **kwargs):
        if not self.normalization_single_flag:
            self.normalization_single_flag = True
            self.widgets['btn_normalization_single']['text'] = 'Please double-click on y=0...'
            self.normalization_single_connection = self.canvas.mpl_connect('button_press_event', self.action_normalization_single_firstclick)
        else:
            self.widgets['btn_normalization_single']['text'] = 'Normalize plot'
            self.normalization_single_flag = False
            self.canvas.mpl_disconnect(self.normalization_single_connection)

    def action_normalization_single_firstclick(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.main_axes:
            y = event.ydata
            if self.selected_artist is not None:
                self.selected_artist['artist'].set_ydata(self.selected_artist['artist'].get_ydata()-y)
                self.fig.canvas.draw()
            self.canvas.mpl_disconnect(self.normalization_single_connection)
            self.normalization_single_connection = self.canvas.mpl_connect('button_press_event', self.action_normalization_single_secondclick)
            self.widgets['btn_normalization_single']['text'] = 'Please double-click on y=1...'

    def action_normalization_single_secondclick(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.main_axes:
            y = event.ydata
            if self.selected_artist is not None:
                self.selected_artist['artist'].set_ydata(np.divide(self.selected_artist['artist'].get_ydata(),y))
                self.fig.canvas.draw()
            self.action_btn_normalization_single()

    def action_btn_delete(self, *args, **kwargs):
        if self.selected_artist is not None:
            self.main_axes.lines.remove(self.selected_artist['artist'])
            self.selected_artist = None
            self.fig.canvas.draw()

    def action_btn_swap_xy(self, *args, **kwargs):
        if self.selected_artist is not None:
            a = self.selected_artist['artist']
            x = a.get_xdata()
            y = a.get_ydata() 
            a.set_xdata(y)
            a.set_ydata(x)
            self.fig.canvas.draw()

    def action_close_custom(self):
        # Remove reference from deleted clipboard plot
        self.application.clipboard_plot = None

    def config_plot_custom(self):
        pass
