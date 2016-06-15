# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Date created: 2015-12-02
# Modified 2015-12-11
# Modified 2016-02-24: Added padding to checkbox label

import Tkinter as tk
import ttk

class EditableCell:

    # Based on script by @dakov
    # http://stackoverflow.com/questions/18562123/how-to-make-ttk-treeviews-rows-editable

    def __init__(self, *args, **kwargs):
        # bind doubleclick
        self.bind("<Double-Button-1>", self.onDoubleClick)
        self.editable = True
        self.entryPopup = None

    def onDoubleClick(self, event):

        if not self.editable:
            return

        ''' Executed, when a row is double-clicked. Opens 
        read-only EntryPopup above the item's column, so it is possible
        to select text '''

        # close previous popups
        self.destroyPopups()

        # what row and column was clicked on
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)

        # get column position info
        x,y,width,height = self.bbox(rowid, column)

        # y-axis offset
        pady = height // 2

        # Convert from string to number, e.g. #1 to 1
        column_number = int(column.replace('#', ''))-1

        # place Entry popup properly         
        value = self.item(rowid)['values'][column_number]
        self.entryPopup = EntryPopup(self, text=value, x=x, y=y, width=width, height=height, row=rowid, column=column_number)

    def destroyPopups(self):
        if self.entryPopup:
            self.entryPopup.remove()

class EntryPopup(tk.Entry):

    # Based on script by @dakov
    # http://stackoverflow.com/questions/18562123/how-to-make-ttk-treeviews-rows-editable
    
    def __init__(self, parent, text, x, y, width, height, row, column, *args, **kwargs):

        self.frame = ttk.Frame(parent, width=width, height=height)
        self.frame.grid(row=0, column=1)
        self.frame.grid_propagate(False)
        self.frame.place(x=x, y=y)
        self.parent = parent
        self.row = row
        self.column = column

        tk.Entry.__init__(self, self.frame, *args, **kwargs)
        self.grid(sticky='nswe')

        self.insert(0, text) 
        self['readonlybackground'] = 'white'
        self['selectbackground'] = '#1BA1E2'
        self['exportselection'] = False

        self.bind("<Control-a>", self.selectAll)
        self.bind("<Escape>", lambda _: self.remove())
        self.bind("<Return>", lambda _: self.save())
        self.bind("<KP_Enter>", lambda _: self.save())

        self.selectAll()
        self.focus_force()

    def save(self, *args, **kwargs):
        self.parent.update_cell(self.row, self.column, self.get().replace(',', '.'))
        self.remove()

    def remove(self):
        self.frame.destroy()

    def selectAll(self, *ignore):
        ''' Set selection on the whole text '''
        self.selection_range(0, 'end')

        # returns 'break' to interrupt default key-bindings
        return 'break'

class ScrollableWidget():

    'Widget with scrollbars attached'

    def __init__(self, master=None, *args, **kwargs):
        self.widgets = dict()
        self.widgets['frame'] = ttk.Frame(master)
        self.widgets['scrollbar_y'] = ttk.Scrollbar(self.widgets['frame'], orient=tk.VERTICAL)
        self.widgets['scrollbar_x'] = ttk.Scrollbar(self.widgets['frame'], orient=tk.HORIZONTAL)

    def attach_scrollbars(self):
        self.widgets['scrollbar_y'].config(command=self.yview)
        self.widgets['scrollbar_y'].pack(side=tk.RIGHT, fill=tk.Y)
        self.widgets['scrollbar_x'].config(command=self.xview)
        self.widgets['scrollbar_x'].pack(side=tk.BOTTOM, fill=tk.X)
        self.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def grid(self, *args, **kwargs):
        self.widgets['frame'].grid(*args, **kwargs)

class DataWidget():

    def get_data(self, indices = False):
        # If indices === False (type and value), return all data
        if isinstance(indices, bool) and not indices:
            return self.data 
        else:
            try:
                # First try to use indices as a list
                return [self.data[int(i)] for i in indices]
            except:
                # If ducktyping as list did not work, use it as a scalar
                return self.data[int(indices)]

    def update_cell(self, row, column, new_value):
        old_values = self.item(row, 'values')
        old_values = list(old_values)
        new_values = old_values
        new_values[column] = new_value
        self.item(row, values=new_values)
        index = 0
        for key, value in self.get_data(row)[0].iteritems():
            if index == column:
                self.data[int(row)][key] = new_value
                break
            index += 1

class ScrollableListbox(ScrollableWidget, tk.Listbox, DataWidget):

    def __init__(self, master=None, *args, **kwargs):
        ScrollableWidget.__init__(self, master=master, *args, **kwargs)
        tk.Listbox.__init__(self, self.widgets['frame'], yscrollcommand=self.widgets['scrollbar_y'].set, xscrollcommand=self.widgets['scrollbar_x'].set, *args, **kwargs)
        self.attach_scrollbars()
        self.data = list()

    def append(self, text, data = ''):
        self.data.append(data)
        self.insert(tk.END, text)

    def clear(self):
        self.data = list()
        self.delete(0, tk.END) 

    def select_first(self):
        self.selection_clear(0, tk.END)
        self.selection_set(0)

    def select_all(self):
        self.selection_clear(0, tk.END)
        self.selection_set(0, tk.END)

class ScrollableTreeview(ScrollableWidget, ttk.Treeview, DataWidget, EditableCell):

    def __init__(self, master=None, *args, **kwargs):
        ScrollableWidget.__init__(self, master=master, *args, **kwargs)
        ttk.Treeview.__init__(self, self.widgets['frame'], yscrollcommand=self.widgets['scrollbar_y'].set, xscrollcommand=self.widgets['scrollbar_x'].set, *args, **kwargs)
        EditableCell.__init__(self, *args, **kwargs)
        self.bind("<KeyPress>", self.action_keypress)
        self.attach_scrollbars()
        self.data = list()
        self.current_index = 0

    def append(self, colvalues, data = ''):
        self.data.append(data)
        item_id = self.insert('', tk.END, str(self.current_index), values=colvalues)
        self.current_index += 1 
        return item_id

    def clear(self):
        children = self.get_children('')
        for child in children:
            self.delete(child)
        self.data = list()
        self.current_index = 0

    def select_first(self):
        self.selection_set(0)

    def select_all(self):
        children = self.get_children('')
        for child in children:
            self.selection_add(child)
    
    def action_keypress(self, e):
        toHex = lambda x:"".join([hex(ord(c))[2:].zfill(2) for c in x])
        if toHex(e.char) == '01': # CTRL + A
            self.select_all()
    
class LabeledEntry(ttk.Frame):
    def __init__(self, master=None, label_text='', default_value='', width=20):
        # Entry Pilatus Columns
        ttk.Frame.__init__(self, master=master)
        self.label = ttk.Label(self, text=label_text)
        self.stringvar = tk.StringVar()
        self.stringvar.set(default_value)
        self.input = ttk.Entry(self, textvariable=self.stringvar, width=width)
        self.label.pack(side='left')
        self.input.pack(side='left')

class Checkbox(tk.Checkbutton):

    def __init__(self, master=None, text='', *args, **kwargs):
        self.master = master
        self.var = tk.IntVar()
        self.click_actions = list()
        text = ' ' + text # Add padding to label text
        tk.Checkbutton.__init__(self, master=self.master, var=self.var, command=self.action_change, text=text, *args, **kwargs)

    def add_click_action(self, function):
        self.click_actions.append(function)

    def action_change(self, *args, **kwargs):
        for function in self.click_actions:
            function(*args, **kwargs)

    def value(self):
        return self.var.get() 
