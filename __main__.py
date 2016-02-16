# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline of LNLS
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Created: 2015-12-02

# ===== DONE =====

# Modified: 2016-02-15
# * Replaced Treeview for tkintertable for displaying of scan data

# Modified: 2015-12-5 - 2015-12-11
# * Checkbox to show multiple plots or sum (integral)
# * Field option for denominator (divide by I0)
# * Allow normalization (choose between max intensity or another arbitrary value to define as 1)
# * Allow export plot data as CSV file
# * Allow calibration: allow double-click over elastic scattered beam peaks on RXES maps
# * Application icon
# * Manual calibration
# * Normalize XES

# ===== TO DO =====
# * Plot together two plots of the same type
# * Choose colormap and vmin on RXES
# * Add option to normalize plots individually instead of one normalization per axes
# * Plot energy transfer RXES
# * Integration with Pilatus image viewer
# * Allow selecting and plotting multiple scans
# * Allow exporting data from RXES colormaps

import os
import Tkinter as tk
import ttk
import tkFileDialog as fd
import re
import pandas
import sys
import matplotlib.pyplot as plt
import numpy as np
import ConfigParser
import random, string
# Custom classes
from classes.spec_parser import *
from classes.custom_widgets import *
from classes.plots import *
from classes.tools import *
# Third party local libraries
import lib.tkintertable
import lib.tkintertable.TableModels
import lib.tkintertable.Tables

class Application(ttk.Frame):

    def createWidgets(self):
        ''' Create the visual objects (widgets): buttons, text entries, etc. '''

        self.widgets = dict()

        # Button Open
        self.widgets['btn_open'] = ttk.Button(self)
        self.widgets['btn_open']["text"] = "Open SPEC file"
        self.widgets['btn_open']["command"] = self.action_select_file
        self.widgets['btn_open'].grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        # Entry Pilatus Columns
        self.widgets['entry_pilatus_columns'] = LabeledEntry(self, 'Signal Cols.: ', 'pl0-pl486')
        self.widgets['entry_pilatus_columns'].grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Entry Background1 Columns
        self.widgets['entry_pilatus_bg1_columns'] = LabeledEntry(self, 'Background 1 Cols.: ', 'pl487-pl973')
        self.widgets['entry_pilatus_bg1_columns'].grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        ## Entry Background2 Columns
        self.widgets['entry_pilatus_bg2_columns'] = LabeledEntry(self, 'Background 2 Cols.: ', 'pl974-pl1460')
        self.widgets['entry_pilatus_bg2_columns'].grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        # Entry Energy Column
        self.widgets['entry_energy_column'] = LabeledEntry(self, 'Energy Col.: ', 'dcm_energy')
        self.widgets['entry_energy_column'].grid(row=4, column=0, sticky="nsew", pady=(0, 10))

        # Entry Denominator (I0) Column
        self.widgets['entry_i0_column'] = LabeledEntry(self, 'I0 Col.: ', 'I0')
        self.widgets['entry_i0_column'].grid(row=5, column=0, sticky="nsew", pady=(0, 10))

        # Button XES
        self.widgets['btn_xes'] = ttk.Button(self)
        self.widgets['btn_xes']["text"] = "XES"
        self.widgets['btn_xes']["command"] = self.action_xes
        self.widgets['btn_xes'].grid(row=6, column=0, sticky="nsew", pady=(0, 2))

        # Button HERFD
        self.widgets['btn_herfd'] = ttk.Button(self)
        self.widgets['btn_herfd']["text"] = "HERFD"
        self.widgets['btn_herfd']["command"] = self.action_herfd
        self.widgets['btn_herfd'].grid(row=7, column=0, sticky="nsew", pady=(0, 2))

        # Button RXES
        self.widgets['btn_rxes'] = ttk.Button(self)
        self.widgets['btn_rxes']["text"] = "RXES"
        self.widgets['btn_rxes']["command"] = self.action_rxes
        self.widgets['btn_rxes'].grid(row=8, column=0, sticky="nsew", pady=(0, 2))

        # Scans listbox
        self.widgets['scans_listbox'] = ScrollableListbox(self)
        self.widgets['scans_listbox'].grid(row=9, column=0, rowspan=3, sticky="nsew")
        self.widgets['scans_listbox'].bind('<<ListboxSelect>>', self.action_scans_listbox_select)

        # Calibration Label
        self.widgets['cb_calib'] = Checkbox(self, text='Use calibration')
        self.widgets['cb_calib'].grid(row=12, column=0, rowspan=1, sticky="nsew", pady=(10, 0))

        # Calibration listbox
        self.widgets['calib_tree'] = ScrollableTreeview(self, height=4)
        col_names = ['ROI', 'Energy']
        self.widgets['calib_tree']['columns'] = col_names
        for col_name in col_names:
            self.widgets['calib_tree'].heading(col_name, text=col_name)
            self.widgets['calib_tree'].column(col_name, width=20)
        # Hide first empty column
        self.widgets['calib_tree']['show']= 'headings'
        self.widgets['calib_tree'].grid(row=13, column=0, sticky="nsew")

        # Data points listbox
        self.widgets['data_frame'] = ttk.Frame(self)
        self.widgets['data_frame'].grid(row=0, column=1, rowspan=10, sticky="nsew", padx=(10, 0))

        # Headers label
        self.widgets['label_headers'] = ttk.Label(self, text='Scan header:')
        self.widgets['label_headers'].grid(row=10, column=1, rowspan=1, sticky="nsew", pady=(10, 0), padx=(10, 0))

        # Headers listbox
        self.widgets['tree_headers'] = ScrollableTreeview(self, height=4)
        col_names = ['Motor', 'Position']
        self.widgets['tree_headers']['columns'] = col_names
        for col_name in col_names:
            self.widgets['tree_headers'].heading(col_name, text=col_name)
            self.widgets['tree_headers'].column(col_name, width=20)
        # Hide first empty column
        self.widgets['tree_headers']['show']= 'headings'
        self.widgets['tree_headers'].grid(row=11, column=1, sticky="nsew", padx=(10, 0))

        # Log Label
        self.widgets['log_label'] = ttk.Label(self, text='Log:')
        self.widgets['log_label'].grid(row=12, column=1, rowspan=1, sticky="nsew", pady=(10, 0), padx=(10, 0))

        # Log listbox
        self.widgets['log_listbox'] = ScrollableListbox(self, height=4)
        self.widgets['log_listbox'].grid(row=13, column=1, sticky="nsew", padx=(10, 0))

        # Do not resize buttons column
        tk.Grid.columnconfigure(self, 0, weight=0)
        tk.Grid.rowconfigure(self, 0, weight=0)
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 9, weight=1)

    def set_window_icon(self, window=None):
        # Set the icon for the graphical window
        # Source: http://stackoverflow.com/a/11180300/1501575
        try:
            root_dir = self.root_dir
            icon_32  = tk.PhotoImage(file=os.path.join(root_dir, 'icons', "logo_xds_vhpt_32x32.gif"))
            icon_64  = tk.PhotoImage(file=os.path.join(root_dir, 'icons', "logo_xds_vhpt_64x64.gif"))
            icon_128 = tk.PhotoImage(file=os.path.join(root_dir, 'icons', "logo_xds_vhpt_128x128.gif"))
            root.tk.call('wm', 'iconphoto', window._w, '-default', icon_32, icon_64, icon_128)
        except:
            self.debug_log('Error loading application icon')

    def __init__(self, master=None):

        self.root_dir = sys.path[0]
        self.default_open_dir = self.root_dir
        self.load_config_ini()
        ttk.Frame.__init__(self, master)
        self.set_window_icon(window=self.master)
        self.grid(row=0, column=0, sticky='nsew', padx=(20, 20), pady=(20, 20))
        tk.Grid.columnconfigure(self.master, 0, weight=1)
        tk.Grid.rowconfigure(self.master, 0, weight=1)
        self.createWidgets()
        self.default_title = 'XDS Von Hamos Preview Tool'
        self.master.title(self.default_title)
        self.scans_list = list()
        self.figure_number = 0
        self.file_path = ''
        self.filename = ''

    def maximize_window(self):
        w, h = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        self.master.geometry("%dx%d+0+0" % (w, h))

    def load_spec_file(self):
        self.widgets['scans_listbox'].clear()
        specfile = SpecParser(self.file_path)
        self.spec_scans = specfile.get_scans()
        for scan_id, scan_data in self.spec_scans.iteritems():
            self.widgets['scans_listbox'].append(scan_data['command'], scan_data['id'])
        self.load_first_scan()
    
    def load_first_scan(self):
        self.widgets['scans_listbox'].select_first()
        self.action_scans_listbox_select()

    def list_scan_data(self, scan_num):
        scan_data = self.spec_scans[scan_num]
        self.list_scan_headers(scan_num)
        # Populate table with scan data
        model = lib.tkintertable.TableModels.TableModel()
        model.importDict(scan_data['data_dict_indexed'])
        selection_color = '#CDE4F7'
        self.widgets['data_table'] = lib.tkintertable.Tables.TableCanvas(self.widgets['data_frame'], model,
                            cellwidth=60, thefont=('',10),rowheight=18, rowheaderwidth=50, 
                            multipleselectioncolor=selection_color, rowselectedcolor=selection_color, selectedcolor=selection_color, editable=False)
        self.widgets['data_table'].createTableFrame()
        self.widgets['data_table'].select_All()
        return

    def list_scan_headers(self, scan_num):
        scan_data = self.spec_scans[scan_num]
        self.widgets['tree_headers'].clear()
        for key, value in OrderedDict(sorted(zip(scan_data['motors_names'], scan_data['motors_positions']))).iteritems():
            self.widgets['tree_headers'].append([key, value])

    def action_scans_listbox_select(self, *args, **kwargs):
        index = int(self.widgets['scans_listbox'].curselection()[0])
        scan_num = self.widgets['scans_listbox'].get_data(index)
        self.list_scan_data(scan_num)

    def load_config_ini(self):
        self.config_ini = ConfigParser.ConfigParser()
        self.config_ini_file = os.path.join(self.root_dir, 'settings.ini')
        try:
            self.config_ini.read(self.config_ini_file)
            self.default_open_dir = self.config_ini.get('global', 'default_open_dir') 
        except:
            self.debug_log('Error reading ' + self.config_ini_file)

    def store_default_open_dir(self, file_path):
        file_dir = os.path.dirname(file_path)
        self.default_open_dir = file_dir
        if not self.config_ini.has_section('global'):
            self.config_ini.add_section('global')
        self.config_ini.set('global', 'default_open_dir', file_dir)
        try:
            with open(self.config_ini_file, 'w') as configfile:
                self.config_ini.write(configfile)
        except:
            self.debug_log('Error writing ' + self.config_ini_file)

    def action_select_file(self):
        file_path = fd.askopenfilename(initialdir=self.default_open_dir)
        if file_path:
            self.file_path = file_path
            self.store_default_open_dir(self.file_path)
            self.filename = os.path.basename(self.file_path)
            self.log('======== OPEN =========')
            self.log('* Loaded path ' + self.file_path)
            self.log('* File: ' + self.filename)
            self.master.title(self.default_title + ' - ' + self.filename )
            self.load_spec_file()

    def log(self, text):
        self.widgets['log_listbox'].append(text)
        self.widgets['log_listbox'].see(tk.END)

    def debug_log(self, text):
        print text

    def get_selected_data(self):
        indices = self.widgets['data_table'].get_selectedRecordNames()
        data = self.widgets['data_table'].getModel().data
        selected_data = [data[k] for k in indices if k in data]
        return selected_data

    def action_xes(self):
        self.plot_xes(self.get_selected_data())

    def action_rxes(self):
        self.plot_rxes(self.get_selected_data())

    def action_herfd(self):
        self.plot_herfd(self.get_selected_data())

    def plot_xes(self, data):

        self.log('======== XES ==========')
        self.figure_number += 1
        self.log('* Figure %.0f - XES - %s' % (self.figure_number, os.path.basename(self.file_path))) 

        # Prepare numpy array
        nparray = Tools.dict_to_numpy(data)

        # Create a new plot window
        parameters = self.get_plot_parameters_and_validate(data)
        plot = XESPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def plot_herfd(self, data):

        self.log('======= HERFD =========')
        self.figure_number += 1
        self.log('* Figure %.0f' % self.figure_number) 

        # Prepare numpy array
        nparray = Tools.dict_to_numpy(data)

        # Create a new plot window
        parameters = self.get_plot_parameters_and_validate(data)
        plot = HERFDPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def plot_rxes(self, data):

        self.log('======== RXES =========')
        self.figure_number += 1
        self.log('* Figure %.0f' % self.figure_number) 

        # Prepare data
        nparray = Tools.dict_to_numpy(data)

        # Create new plot window
        parameters = self.get_plot_parameters_and_validate(data)
        plot = RXESPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def get_plot_parameters_and_validate(self, data):
        parameters = self.get_plot_parameters(data)
        self.validate_plot_parameters(parameters)
        return parameters

    def validate_plot_parameters(self, parameters):
        if len(parameters['rois_columns']) == 0:
            self.log('* No ROI column was selected')
        elif len(parameters['rois_columns']) >= 1:
            self.log('* Number of ROI columns: ' + str(len(parameters['rois_columns'])))
        if isinstance(parameters['energy_column'], (bool)) and not parameters['energy_column']:
            self.log('* No energy column was selected')
        if isinstance(parameters['i0_column'], (bool)) and not parameters['i0_column']:
            self.log('* No I0 column was selected')
        if parameters['use_calibration']:
            self.log('* Using energy calibration')

    def get_plot_parameters(self, data):

        rois_columns = self.get_columns_indices(data[0].keys(), self.widgets['entry_pilatus_columns'].stringvar.get())
        rois_names = np.asarray(data[0].keys())[rois_columns]

        energy_column_list = self.get_columns_indices(data[0].keys(), self.widgets['entry_energy_column'].stringvar.get())
        if energy_column_list:
            energy_column = energy_column_list[0]
        else:
            energy_column = False

        i0_column_list = self.get_columns_indices(data[0].keys(), self.widgets['entry_i0_column'].stringvar.get())
        if i0_column_list:
            i0_column = i0_column_list[0]
        else:
            i0_column = False

        use_calibration = self.widgets['cb_calib'].var.get()
        calibration_data = self.widgets['calib_tree'].get_data()

        parameters = {
            'rois_columns': rois_columns,
            'energy_column': energy_column,
            'i0_column': i0_column,
            'rois_names': rois_names,
            'use_calibration': use_calibration,
            'calibration_data': calibration_data
        }
        return parameters
    
    def columns_names_parse_as_int(self, columns_names):
        return_list = list()
        for name in columns_names:
            return_list.append(int(re.findall('([0-9]+)', name)[0]))
        return return_list

    def get_columns_indices(self, columns_list, pattern=''):
        # Remove spaces
        pattern = pattern.replace(' ', '')
        # Split into commas 
        groups = pattern.split(',')
        range_list = list()
        pattern_list = list()
        for group in groups:
            # First check if group is a range
            group_limits = group.split('-') 
            if len(group_limits) == 2:
                range_list.append({'begin': group_limits[0], 'end': group_limits[1], 'status': False})
            elif len(group_limits) == 1 and group_limits[0].find('*') == -1:
                range_list.append({'begin': group_limits[0], 'end': group_limits[0], 'status': False})
            elif len(group_limits) == 1 and group_limits[0].find('*') > -1:
                escaped_pattern = re.escape(group_limits[0])
                escaped_pattern = '^' + escaped_pattern.replace('\*', '.+') + '$'
                pattern_list.append(escaped_pattern)
        
        return_list = list()
        index = 0
        for column_name in columns_list:
            inside_range = False
            # Range start
            for group_limit in range_list:
                if group_limit['status'] == True:
                    inside_range = True
                if column_name == group_limit['begin']:
                    group_limit['status'] = True
                    inside_range = True

            for regex_pattern in pattern_list:
                if re.search(regex_pattern, column_name):
                    inside_range = True

            # Inside range logic
            if inside_range:
                return_list.append(index)

            # Range end
            for group_limit in range_list:
                if column_name == group_limit['end']:
                    group_limit['status'] = False
            index += 1
        return return_list

# Init TK Master
root = tk.Tk()
s = ttk.Style()
s.theme_use('default')
root.geometry("1000x700+30+30") # width x height + padding_x + padding_y

# Init Application
app = Application(master=root)
app.mainloop()
