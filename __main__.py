# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline of LNLS
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Created: 2015-12-02

# ===== DONE =====

# Modified: 2016-02-24

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
#import ConfigParser
import random, string
import itertools
import copy
import time
import codecs
# Custom classes
from classes.spec_parser import *
from classes.custom_widgets import *
from classes.plots import *
from classes.tools import *
from classes.profiler import *
# Third party local libraries
import lib.tkintertable
import lib.tkintertable.TableModels
import lib.tkintertable.Tables
import lib.configparser

class Application(ttk.Frame):

    def createWidgets(self):
        ''' Create the visual objects (widgets): buttons, text entries, etc. '''

        self.widgets = dict()

        # Button Open
        row = 0 # Helper for grid layout
        rowspan = 1

        # Subframe
        self.widgets['open_file_frame'] = ttk.Frame(self)

        self.widgets['btn_open'] = ttk.Button(self.widgets['open_file_frame'])
        self.widgets['btn_open']["text"] = "Open SPEC file"
        self.widgets['btn_open']["command"] = self.action_select_file
        self.widgets['btn_open'].grid(row=row, column=0, sticky="nsew", pady=(0, 0))

        self.widgets['cb_auto_refresh'] = Checkbox(self.widgets['open_file_frame'], text='Auto refresh')
        self.widgets['cb_auto_refresh'].grid(row=row, column=1, rowspan=rowspan, sticky="nsew", pady=(0, 0))

        tk.Grid.columnconfigure(self.widgets['open_file_frame'], 0, weight=1)
        tk.Grid.rowconfigure(self.widgets['open_file_frame'], 0, weight=1)
        self.widgets['open_file_frame'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        # Entry Pilatus Columns
        row += rowspan
        rowspan = 1
        self.widgets['entry_pilatus_signal_columns'] = LabeledEntry(self, 'Signal (S): ', 'pl0-pl486')
        self.widgets['entry_pilatus_signal_columns'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        # Entry Background1 Columns
        row += rowspan
        rowspan = 1
        self.widgets['entry_pilatus_bg1_columns'] = LabeledEntry(self, 'Background 1 (BG1): ', 'pl487-pl973')
        self.widgets['entry_pilatus_bg1_columns'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        # Entry Background2 Columns
        row += rowspan
        rowspan = 1
        self.widgets['entry_pilatus_bg2_columns'] = LabeledEntry(self, 'Background 2 (BG2): ', 'pl974-pl1460')
        self.widgets['entry_pilatus_bg2_columns'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        # Entry Denominator (I0) Column
        row += rowspan
        rowspan = 1
        self.widgets['entry_i0_column'] = LabeledEntry(self, 'Monitor (I0): ', 'I0')
        self.widgets['entry_i0_column'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        # Entry Energy Column
        row += rowspan
        rowspan = 1
        self.widgets['entry_energy_column'] = LabeledEntry(self, 'Incoming energy: ', 'energy')
        self.widgets['entry_energy_column'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        ## Intensity Formula
        row += rowspan
        rowspan = 1
        self.widgets['entry_pilatus_formula'] = LabeledEntry(self, 'Intensity formula: ', '(S-(BG1+BG2)/2)/I0')
        self.widgets['entry_pilatus_formula'].grid(row=row, column=0, sticky="nsew", pady=(0, 10))

        # Button XES
        row += rowspan
        rowspan = 1
        self.widgets['btn_xes'] = ttk.Button(self)
        self.widgets['btn_xes']["text"] = "XES"
        self.widgets['btn_xes']["command"] = self.action_xes
        self.widgets['btn_xes'].grid(row=row, column=0, sticky="nsew", pady=(0, 2))

        # Button HERFD
        row += rowspan
        rowspan = 1
        self.widgets['btn_herfd'] = ttk.Button(self)
        self.widgets['btn_herfd']["text"] = "HERFD"
        self.widgets['btn_herfd']["command"] = self.action_herfd
        self.widgets['btn_herfd'].grid(row=row, column=0, sticky="nsew", pady=(0, 2))

        # Button RXES
        row += rowspan
        rowspan = 1
        self.widgets['btn_rxes'] = ttk.Button(self)
        self.widgets['btn_rxes']["text"] = "RXES"
        self.widgets['btn_rxes']["command"] = self.action_rxes
        self.widgets['btn_rxes'].grid(row=row, column=0, sticky="nsew", pady=(0, 2))

        # Scans listbox
        row += rowspan
        rowspan = 3
        row_expandable = row # Store number of expandable row
        self.widgets['scans_listbox'] = ScrollableListbox(self)
        self.widgets['scans_listbox'].grid(row=row, column=0, rowspan=rowspan, sticky="nsew")
        self.widgets['scans_listbox'].bind('<<ListboxSelect>>', self.action_scans_listbox_select)

        # Calibration Checkbox
        row += rowspan
        rowspan = 1
        self.widgets['calib_frame'] = ttk.Frame(self)
        self.widgets['cb_calib'] = Checkbox(self.widgets['calib_frame'], text='Use calibration')
        self.widgets['cb_calib'].pack(side=tk.LEFT, padx=0, pady=0)

        # Calibration Preview BUtton
        self.widgets['btn_calib_preview'] = ttk.Button(self.widgets['calib_frame'])
        self.widgets['btn_calib_preview']["text"] = "Plot calib. fit"
        self.widgets['btn_calib_preview']["command"] = self.action_calib_preview
        self.widgets['btn_calib_preview'].pack(side=tk.LEFT, padx=10, pady=0)
        self.widgets['calib_frame'].grid(row=row, column=0, rowspan=rowspan, sticky="nsew", pady=(2, 2))

        # Calibration listbox
        row += rowspan
        rowspan = 1
        self.widgets['calib_tree'] = ScrollableTreeview(self, height=4)
        col_names = ['ROI', 'Energy']
        self.widgets['calib_tree']['columns'] = col_names
        for col_name in col_names:
            self.widgets['calib_tree'].heading(col_name, text=col_name)
            self.widgets['calib_tree'].column(col_name, width=20)
        # Hide first empty column
        self.widgets['calib_tree']['show']= 'headings'
        self.widgets['calib_tree'].grid(row=row, column=0, sticky="nsew")

        # Data points listbox
        # New column
        column = 1
        row = 0
        rowspan = row_expandable+1
        colspan = 2
        self.widgets['data_frame'] = ttk.Frame(self)
        self.widgets['data_frame'].grid(row=row, column=column, rowspan=rowspan, columnspan=colspan, sticky="nsew", padx=(10, 0))

        # Empty initial data table
        self.scan_data_model = lib.tkintertable.TableModels.TableModel()
        self.scan_data_model.importDict({'0': {'': ''}})
        selection_color = '#CDE4F7'
        self.widgets['data_table'] = lib.tkintertable.Tables.TableCanvas(self.widgets['data_frame'], self.scan_data_model,
                            cellwidth=60, thefont=('',10),rowheight=18, rowheaderwidth=50, 
                            multipleselectioncolor=selection_color, rowselectedcolor=selection_color, selectedcolor=selection_color, editable=False)
        self.widgets['data_table'].createTableFrame()
        self.widgets['data_table'].select_All()

        # Headers label
        row += rowspan
        row_scan_header = row
        rowspan = 1
        self.widgets['label_headers'] = ttk.Label(self, text='Scan header:')
        self.widgets['label_headers'].grid(row=row, column=column, rowspan=rowspan, sticky="nsew", pady=(10, 0), padx=(10, 0))

        # Headers listbox
        row += rowspan
        rowspan = 1
        self.widgets['tree_headers'] = ScrollableTreeview(self, height=4)
        col_names = ['Motor', 'Position']
        self.widgets['tree_headers']['columns'] = col_names
        for col_name in col_names:
            self.widgets['tree_headers'].heading(col_name, text=col_name)
            self.widgets['tree_headers'].column(col_name, width=20)
        # Hide first empty column
        self.widgets['tree_headers']['show']= 'headings'
        self.widgets['tree_headers'].grid(row=row, column=column, sticky="nsew", padx=(10, 0))

        # Log Label
        row += rowspan
        rowspan = 1
        colspan = 2
        self.widgets['log_label'] = ttk.Label(self, text='Log:')
        self.widgets['log_label'].grid(row=row, column=column, rowspan=rowspan, columnspan=colspan, sticky="nsew", pady=(10, 0), padx=(10, 0))

        # Log listbox
        row += rowspan
        rowspan = 1
        self.widgets['log_listbox'] = ScrollableListbox(self, height=4)
        colspan = 2
        self.widgets['log_listbox'].grid(row=row, column=column, columnspan=colspan, sticky="nsew", padx=(10, 0))

        # Notes label
        row = row_scan_header
        column = 2
        self.widgets['label_notes'] = ttk.Label(self, text='Annotations:')
        self.widgets['label_notes'].grid(row=row, column=column, rowspan=rowspan, sticky="nsew", pady=(10, 0), padx=(10, 0))

        # Notes text field
        row += rowspan
        rowspan = 1
        self.widgets['text_notes'] = tk.Text(self, width=40, height=4)
        self.widgets['text_notes'].grid(row=row, column=column, sticky="nsew", padx=(10, 0))

        # Do not resize buttons column
        tk.Grid.columnconfigure(self, 0, weight=0)
        tk.Grid.rowconfigure(self, 0, weight=0)
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, row_expandable, weight=1)

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
        self.profiler = Profiler()
        self.default_open_dir = self.root_dir
        self.default_open_file = None
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
        # Create a new plot window
        self.clipboard_plot = None

        self.configs = { 's': 'entry_pilatus_signal_columns',
                    'bg1': 'entry_pilatus_bg1_columns',
                    'bg2': 'entry_pilatus_bg2_columns',
                    'i0': 'entry_i0_column',
                    'energy': 'entry_energy_column',
                    'formula': 'entry_pilatus_formula',
                    'annotations': 'text_notes'
                  }

    def maximize_window(self):
        w, h = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        self.master.geometry("%dx%d+0+0" % (w, h))

    def load_spec_file(self, refresh = False):

        # Quit if file path does not exist
        if not self.file_path:
            return

        self.widgets['scans_listbox'].clear()

        self.specfile = SpecParser(self.file_path)

        self.spec_scans = self.specfile.get_scans()

        for scan_id, scan_data in self.spec_scans.iteritems():
            self.widgets['scans_listbox'].append(scan_data['command'] + ' (' + scan_data['date'] + ')', scan_data['id'])

        if refresh:
            self.list_scan_data(self.current_scan) # For auto refresh mode
        else:
            self.load_first_scan() # For regular file opening
    
    def load_first_scan(self):
        self.widgets['scans_listbox'].select_first()
        self.action_scans_listbox_select()

    def list_scan_data(self, scan_num):
        self.list_scan_headers(scan_num)
        # Populate table with scan data
        self.current_scan = scan_num
        self.scan_data_model = lib.tkintertable.TableModels.TableModel()

        num_cols = len(self.spec_scans[scan_num]['data_values_indexed'][0])

        column_count = 0
        for column in self.spec_scans[scan_num]['columns_names']:
            if column_count == num_cols:
                break
            self.scan_data_model.addColumn(column)
            column_count += 1 
        
        self.scan_data_model.data.update(self.spec_scans[scan_num]['data_values_indexed'])
        self.scan_data_model.reclist = self.scan_data_model.data.keys()

        self.widgets['data_table'].setModel(self.scan_data_model)
        self.widgets['data_table'].createTableFrame()
        self.widgets['data_table'].select_All()
        return

    def list_scan_headers(self, scan_num):
        self.widgets['tree_headers'].clear()
        for key, value in OrderedDict(sorted(zip(self.spec_scans[scan_num]['motors_names'], self.spec_scans[scan_num]['motors_positions']))).iteritems():
            self.widgets['tree_headers'].append([key, value])

    def action_scans_listbox_select(self, *args, **kwargs):
        index = int(self.widgets['scans_listbox'].curselection()[0])
        scan_num = self.widgets['scans_listbox'].get_data(index)
        self.list_scan_data(scan_num)

    def load_config_ini(self):
        self.config_ini = lib.configparser.ConfigParser()
        self.config_ini_file = os.path.join(os.path.expanduser('~'), 'xds-vonhamos-preview-tool-settings.ini')
        try:
            self.config_ini.readfp(codecs.open(self.config_ini_file, 'r', 'utf8'))
            self.default_open_dir = self.config_ini.get('global', 'default_open_dir') 
            self.default_open_file = self.config_ini.get('global', 'default_open_file') 
        except:
            self.debug_log('Error reading ' + self.config_ini_file)

    def store_default_open_dir(self, file_path):
        file_dir = os.path.dirname(file_path)
        open_file = os.path.basename(file_path)
        self.default_open_file = open_file
        self.default_open_dir = file_dir
        if not self.config_ini.has_section('global'):
            self.config_ini.add_section('global')
        self.config_ini.set('global', 'default_open_dir', file_dir)
        self.config_ini.set('global', 'default_open_file', open_file)
        try:
            with codecs.open(self.config_ini_file, 'w', 'utf8') as configfile:
                self.config_ini.write(configfile)
        except:
            self.debug_log('Error writing ' + self.config_ini_file)

    def action_select_file(self):
        file_path = fd.askopenfilename(initialdir=self.default_open_dir, initialfile=self.default_open_file)
        self.open_file(file_path)

    def open_file(self, file_path):

        if file_path:

            file_path = file_path.replace('_xds-vhpt.ini', '') # Open data file even when clicking on project config file
            self.file_path = file_path
            self.store_default_open_dir(self.file_path)
            self.filename = os.path.basename(self.file_path)

            # Try to load file custom config
            self.file_config_ini = lib.configparser.ConfigParser()
            self.file_config_ini_file = self.file_path + '_xds-vhpt.ini'

            # Clear calibration box, to avoid confusion for the user
            self.widgets['calib_tree'].clear()
            self.widgets['cb_calib'].var.set(False)

            try:
                self.file_config_ini.readfp(codecs.open(self.file_config_ini_file, 'r', 'utf8'))
            except:
                self.debug_log('Error reading ' + self.file_config_ini_file)

            for config in self.configs:
                # Entry widgets
                try:
                    self.widgets[self.configs[config]].stringvar.set(self.file_config_ini.get('project', config))
                except:
                    pass

                # Text widgets
                try:
                    self.widgets[self.configs[config]].delete('1.0', 'end')
                    self.widgets[self.configs[config]].insert('1.0', self.file_config_ini.get('project', config))
                except:
                    pass

            try:
                w = self.widgets['calib_tree']
                calib_list = self.file_config_ini.get('project', 'Calibration').split(';') 
                for calib_pair in calib_list:
                    pair = calib_pair.split(',')
                    item_id = w.append(["%.1f" % float(pair[0]), "%.4f" % float(pair[1])], {'roi': float(pair[0]), 'energy': float(pair[1])})
                    w.see(item_id)
                    self.widgets['cb_calib'].var.set(True)
            except:
                self.debug_log('Error reading config "Calibration"')
                
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
        # At first I was using deepcopy to avoid messing up with the original data,
        # but it was too slow, and I don't think it is needed anymore
        # data = copy.deepcopy(self.widgets['data_table'].getModel().data)
        p = self.get_plot_parameters_and_validate(data)
        error = False

        fields = {  'S': 'rois_signal_columns',
                    'BG1': 'rois_bg1_columns',
                    'BG2': 'rois_bg2_columns',
                    'I0': 'i0_column'
                 }

        formula_contains_S = self.formula_contains_variable('S')
        formula_contains_BG1 = self.formula_contains_variable('BG1')
        formula_contains_BG2 = self.formula_contains_variable('BG2')
        formula_contains_I0 = self.formula_contains_variable('I0')


        for key in fields:
            # Fields with False or [] contents should throw errors if on formula
            if (self.formula_contains_variable(key)
               and ((isinstance(p[fields[key]], (bool)) and not p[fields[key]])
               or (not isinstance(p[fields[key]], (bool, int)) and len(p[fields[key]]) == 0))):
                error = '* Error: Formula contains ' + key + ', but no column matched the user-defined filter'

        if (formula_contains_S and formula_contains_BG1 and len(p['rois_signal_columns']) != len(p['rois_bg1_columns'])):
            error = '* Error: Formula contains both S and BG1, but the number of columns differ'
            
        if (formula_contains_S and formula_contains_BG2 and len(p['rois_signal_columns']) != len(p['rois_bg2_columns'])):
            error = '* Error: Formula contains both S and BG2, but the number of columns differ'

        if (formula_contains_BG1 and formula_contains_BG2 and len(p['rois_bg1_columns']) != len(p['rois_bg2_columns'])):
            error = '* Error: Formula contains both BG1 and BG2, but the number of columns differ'

        if error:
            self.log(error)
            raise ValueError(error)

        selected_data = list()
        
        rois_signal_cols = []
        rois_bg1_cols = []
        rois_bg2_cols = []

        if formula_contains_S:
            rois_signal_cols = p['rois_signal_columns']

        if formula_contains_BG1:
            rois_bg1_cols = p['rois_bg1_columns']
        
        if formula_contains_BG2:
            rois_bg2_cols = p['rois_bg2_columns']

        for row in indices:
            if row in data:
                selected_data.append(data[row])
        selected_data = np.array(selected_data)

        formula = p['rois_formula'] 
        if formula_contains_S:
            formula = formula.replace('S', 'selected_data[:, [' + ', '.join(map(str, rois_signal_cols))  + ']].astype("float")')
        if formula_contains_BG1:
            formula = formula.replace('BG1', 'selected_data[:, [' + ', '.join(map(str, rois_bg1_cols))  + ']].astype("float")')
        if formula_contains_BG2:
            formula = formula.replace('BG2', 'selected_data[:, [' + ', '.join(map(str, rois_bg2_cols))  + ']].astype("float")')
        if formula_contains_I0:
            formula = formula.replace('I0', 'selected_data[:, ' + str(p['i0_column']) + '].reshape(' + str(len(selected_data)) + ', 1).astype("float")')

        intensity_values = eval(formula).astype('string')
        selected_data = np.column_stack((selected_data, intensity_values))

        return selected_data

    def formula_contains_variable(self, variable):
        rois_formula = self.widgets['entry_pilatus_formula'].stringvar.get()
        # A white space is preppended to the formula to simplify the regex
        formula = ' ' + rois_formula + ' '
        if re.search('[^a-zA-Z0-9]' + re.escape(variable) + '[^a-zA-Z0-9]', formula) is not None:
            return True
        else:
            return False

    def save_project_config(self):
        if not self.file_config_ini.has_section('project'):
            self.file_config_ini.add_section('project')

        for config in self.configs:
            # Entry widgets
            try:
                self.file_config_ini.set('project', config, self.widgets[self.configs[config]].stringvar.get())
            except:
                pass
            # Text widgets
            try:
                self.file_config_ini.set('project', config, self.widgets[self.configs[config]].get('1.0', 'end'))
            except:
                pass

        calibration_data = self.widgets['calib_tree'].get_data()
        calib_string = ''
        for calib_pair in calibration_data:
            calib_string += str(calib_pair['roi']) + ',' + str(calib_pair['energy']) + ';'
        calib_string = calib_string[0:-1]
        self.file_config_ini.set('project', 'calibration', calib_string)
            
        #try:
        with codecs.open(self.file_config_ini_file, 'w', 'utf8') as configfile:
            self.file_config_ini.write(configfile)
        #except:
            #self.debug_log('Error writing ' + self.file_config_ini_file)

    def action_xes(self):
        self.save_project_config()
        self.plot_xes(self.get_selected_data())

    def action_rxes(self):
        self.save_project_config()
        self.plot_rxes(self.get_selected_data())

    def action_herfd(self):
        self.save_project_config()
        self.plot_herfd(self.get_selected_data())

    def plot_xes(self, data):

        self.log('======== XES ==========')
        self.figure_number += 1
        self.log('* Figure %.0f - XES - %s' % (self.figure_number, os.path.basename(self.file_path))) 

        # Prepare numpy array
        parameters = self.get_plot_parameters_and_validate(data)
        nparray = Tools.mixed_array_to_float(data)

        # Create a new plot window
        plot = XESPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def plot_herfd(self, data):

        self.log('======= HERFD =========')
        self.figure_number += 1
        self.log('* Figure %.0f' % self.figure_number) 

        # Prepare numpy array
        nparray = Tools.mixed_array_to_float(data)

        # Create a new plot window
        parameters = self.get_plot_parameters_and_validate(data)
        plot = HERFDPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def update_current_selected_data(self):
        # Prepare data
        data = self.get_selected_data()
        nparray = Tools.mixed_array_to_float(data)
        # Create new plot window
        parameters = self.get_plot_parameters_and_validate(data)
        self.current_selected_data = nparray 
        self.current_parameters = parameters

    def action_calib_preview(self, *args, **kwargs):
        # Prepare data
        data = self.get_selected_data()
        nparray = Tools.mixed_array_to_float(data)
        parameters = self.get_plot_parameters_and_validate(data)
        # Create new plot window
        plot = CalibrationPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def plot_rxes(self, data):

        self.log('======== RXES =========')
        self.figure_number += 1
        self.log('* Figure %.0f' % self.figure_number) 

        # Prepare data
        nparray = Tools.mixed_array_to_float(data)
        parameters = self.get_plot_parameters_and_validate(data)

        # Create new plot window
        plot = RXESPlot(master = self.master, parameters = parameters, data = nparray, application = self, figure_number = self.figure_number)

    def get_plot_parameters_and_validate(self, data):
        parameters = self.get_plot_parameters(data)
        self.validate_plot_parameters(parameters)
        return parameters

    def validate_plot_parameters(self, parameters):
        if len(parameters['rois_signal_columns']) == 0:
            self.log('* No ROI column was selected')
        elif len(parameters['rois_signal_columns']) >= 1:
            self.log('* Number of ROI columns: ' + str(len(parameters['rois_signal_columns'])))
        if isinstance(parameters['energy_column'], (bool)) and not parameters['energy_column']:
            self.log('* No energy column was selected')
        #if isinstance(parameters['i0_column'], (bool)) and not parameters['i0_column']:
        #    self.log('* No I0 column was selected')
        if parameters['use_calibration']:
            self.log('* Using energy calibration')

    def get_plot_parameters(self, data):

        columnNames = self.scan_data_model.columnNames
    
        rois_signal_columns = self.get_columns_indices(columnNames, self.widgets['entry_pilatus_signal_columns'].stringvar.get())
        rois_signal_names = np.asarray(columnNames)[rois_signal_columns]

        rois_bg1_columns = self.get_columns_indices(columnNames, self.widgets['entry_pilatus_bg1_columns'].stringvar.get())
        rois_bg1_names = np.asarray(columnNames)[rois_bg1_columns]

        rois_bg2_columns = self.get_columns_indices(columnNames, self.widgets['entry_pilatus_bg2_columns'].stringvar.get())
        rois_bg2_names = np.asarray(columnNames)[rois_bg2_columns]

        # This is automatically populated elsewhere according to Intensity Formula
        #intensity_columns = self.get_columns_indices(columnNames, '__intensity_*')
        intensity_columns = range(len(columnNames), len(columnNames)+len(rois_signal_columns))
        intensity_names = rois_signal_names

        energy_column_list = self.get_columns_indices(columnNames, self.widgets['entry_energy_column'].stringvar.get())
        if energy_column_list:
            energy_column = energy_column_list[0]
        else:
            energy_column = False

        i0_column_list = self.get_columns_indices(columnNames, self.widgets['entry_i0_column'].stringvar.get())
        if i0_column_list:
            i0_column = i0_column_list[0]
            i0_name = np.asarray(columnNames)[i0_column]
        else:
            i0_column = False
            i0_name = ''

        rois_formula = self.widgets['entry_pilatus_formula'].stringvar.get()
        use_calibration = self.widgets['cb_calib'].var.get()
        calibration_data = self.widgets['calib_tree'].get_data()

        parameters = {
            'rois_signal_columns': rois_signal_columns,
            'rois_bg1_columns': rois_bg1_columns,
            'rois_bg2_columns': rois_bg2_columns,
            'energy_column': energy_column,
            'i0_column': i0_column,
            'i0_name': i0_name,
            'rois_signal_names': rois_signal_names,
            'rois_bg1_names': rois_bg1_names,
            'rois_bg2_names': rois_bg2_names,
            'rois_formula': rois_formula,
            'use_calibration': use_calibration,
            'calibration_data': calibration_data,
            'intensity_columns': intensity_columns,
            'intensity_names': intensity_names,
            'row_number_column': 0,
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

    # This functions loops every 10 seconds
    def timer(self):
        auto_refresh = self.widgets['cb_auto_refresh'].var.get()
        if auto_refresh:
            self.load_spec_file(refresh=True)
        self.after(10000, self.timer)


# Init TK Master
root = tk.Tk()
root.geometry("1000x700+30+30") # width x height + padding_x + padding_y

# Init Application
app = Application(master=root)
app.after(0, app.timer)
app.mainloop()
