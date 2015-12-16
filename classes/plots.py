# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Date created: 2015-12-02
# Date modified: 2015-12-11

import Tkinter as tk
import tkFileDialog as fd
import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
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
        self.plot_type = plot_type
        self.widgets = dict() # To be used by class descendants

        # Init window
        tk.Toplevel.__init__(self, master=self.master)

        # Set window title
        self.title('Figure %.0f - %s - %s' % (figure_number, plot_type, (self.application.filename))) 

        self.protocol("WM_DELETE_WINDOW", self.action_close)
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        self.config_plot()
        self.add_default_widgets()

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

    def default_config(self):
        self.axes.get_xaxis().get_major_formatter().set_useOffset(False)
        self.axes.get_yaxis().get_major_formatter().set_useOffset(False)
        self.fig.set_tight_layout(True)

    def action_btn_export(self, *args, **kwargs):
        file_path = fd.asksaveasfilename()
        if file_path:
            line_num = 0
            for line in self.axes.get_lines():
                line_num += 1
                path = file_path + '_' + self.plot_type + '_' + str(line_num) + '.txt'
                np.savetxt(path, np.column_stack([line.get_xdata(), line.get_ydata()]))

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
            return_list.append(int(re.findall('([0-9]+)', name)[0]))
        return return_list

    def action_close(self):
        # Custom code when closing plot window
        self.destroy()

    def roi_axis(self):
        ' Used on plots which have ROI as x axis '
        p = self.parameters
        rois_numbers = self.columns_names_parse_as_int(p['rois_names'])
        if p['use_calibration'] and p['calibration_data']:
            self.axes.set_xlabel('Emitted energy (keV)')
            return self.rois_to_energies()
        else:
            self.axes.set_xlabel('ROI')
            return rois_numbers

    def rois_to_energies(self):
        ' Used on plots which have ROI as x axis '
        p = self.parameters
        rois_numbers = self.columns_names_parse_as_int(p['rois_names'])

        # Fitting
        calib = Tools.dict_to_numpy(p['calibration_data']) 
        equation_parameters = np.polyfit(calib[:, 0], calib[:, 1], min(3, calib.shape[0]-1))

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
        if event.dblclick and event.inaxes == self.axes:
            y = event.ydata
            self.new_base_value = self.base_value + y * self.normalization_value
            self.canvas.mpl_disconnect(self.normalization_connection)
            self.normalization_connection = self.canvas.mpl_connect('button_press_event', self.action_normalization_secondclick)
            self.widgets['btn_normalization']['text'] = 'Please double-click on y=1...'

    def action_normalization_secondclick(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.axes:
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

        # Init
        self.add_widgets()
        self.show()
        self.plot()

    def add_widgets(self):

        # Normalization button
        self.widgets['btn_calibration'] = ttk.Button(self.widgets['frame'], text='Calibrate energy')
        self.widgets['btn_calibration']["command"] = self.action_btn_calibration
        self.widgets['btn_calibration'].pack(side=tk.LEFT, padx=10, pady=5)

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

    def action_calibration_click(self, event, *args, **kwargs):
        if event.dblclick and event.inaxes == self.axes:
            x = event.xdata
            y = event.ydata
            if self.application:
                w = self.application.widgets['calib_tree']
                item_id = w.append(["%.1f" % x, "%.4f" % y], {'roi': x, 'energy': y})
                w.see(item_id)
                self.application.widgets['cb_calib'].var.set(True)

    def plot(self):
        p = self.parameters
        # Generate colormap
        counts = self.data[:, p['rois_columns']]
        if p['i0_column']:
            # Normalize
            counts = np.divide(counts, self.data[:, p['i0_column']][:, np.newaxis])
        cs = self.axes.contourf(self.roi_axis(), self.data[:, p['energy_column']].tolist(), counts, 100, stride=1)

    def config_plot_custom(self):
        self.axes.set_ylabel('Incoming energy (keV)')

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
        self.axes.clear()

        # Divide by I0
        if p['i0_column']:
            i0_values = self.data[:, p['i0_column']][:, np.newaxis]
        else:
            i0_values = 1

        normalized_data = np.divide(self.data[:, p['rois_columns']], self.normalization_value*i0_values) - self.base_value/self.normalization_value
        energies_data = np.repeat(self.data[:, p['energy_column']][:, np.newaxis], normalized_data.shape[1], axis=1)
        self.axes.plot(energies_data, normalized_data)
        self.plot_redraw()

    def plot_sum(self):
        p = self.parameters
        self.axes.clear()

        # Divide by I0
        if p['i0_column']:
            i0_values = self.data[:, p['i0_column']][:, np.newaxis]
        else:
            i0_values = 1

        normalized_data = np.sum(np.divide(self.data[:, p['rois_columns']], self.normalization_value*i0_values), axis=1) - self.base_value/self.normalization_value

        # Add plot line of the sum
        self.axes.plot(self.data[:, p['energy_column']], normalized_data)
        self.plot_redraw()

    def config_plot_custom(self):
        self.axes.set_xlabel('Incoming energy (keV)')
        self.axes.set_ylabel('Intensity')

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
        self.axes.clear()

        # Generate plot lines
        rows, columns = self.data.shape
        roi_axis = self.roi_axis()

        # Divide by I0
        if p['i0_column']:
            i0_values = self.data[:, p['i0_column']][:, np.newaxis]
        else:
            i0_values = 1

        normalized_data = np.divide(self.data[:, min(p['rois_columns']):max(p['rois_columns'])+1], i0_values*self.normalization_value) - self.base_value/self.normalization_value
        rois_data = np.repeat(np.asarray(roi_axis)[:, np.newaxis], normalized_data.shape[0], axis=1)
        self.axes.plot(rois_data, np.transpose(normalized_data))
        self.plot_redraw()

    def plot_sum(self):
        p = self.parameters
        self.axes.clear()

        # Generate plot lines
        rows, columns = self.data.shape
        roi_axis = self.roi_axis()

        # Divide by I0
        if p['i0_column']:
            i0_values = self.data[0:rows, p['i0_column']][:, np.newaxis]
        else:
            i0_values = 1

        normalized_data = np.sum(np.divide(self.data[0:rows, min(p['rois_columns']):max(p['rois_columns'])+1], i0_values*self.normalization_value), axis=0) - self.base_value/self.normalization_value
        # Add plot line
        self.axes.plot(roi_axis, normalized_data)
        self.plot_redraw()

    def config_plot_custom(self):
        self.axes.set_ylabel('Intensity')

    def action_cb_sum_click(self, *args, **kwargs):
        self.refresh_plot()

    def refresh_plot(self):
        plot_sum = self.widgets['cb_sum'].value()
        if plot_sum:
            self.plot_sum()
        else:
            self.plot_multiple()
