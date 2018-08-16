#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A GUI application to view the raw activPAL accelerometer data."""

# Created on 21 Jun 2017
#
# @author: R-Broadley

import sys
import os
from datetime import datetime
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QFileDialog, QWidget, QVBoxLayout, QLabel,
                             QAction, qApp)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
from .base import BaseMainWindow, SpacerWidget
from ..io.raw import ActivpalData


class MainWindow(BaseMainWindow):
    """A BaseMainWindow subclass which displays a plot of raw activPAL data."""

    def __init__(self, parent=None):
        """
        Create an instance of a MainWindow.

        Parameters
        ----------
        parent : object
            The parent object.

        """
        super(MainWindow, self).__init__(parent)
        self.file_path = None
        self.show()
        self._setup_window()
        self._setup_toolbar()
        self.statusBar().showMessage('Requesting File ...')
        qApp.processEvents()
        self.select_file()
        self.statusBar().showMessage('Plotting File ...')
        self.run_main()
        qApp.processEvents()
        self.statusBar().showMessage('Ready')

    def _add_plot_controls(self):
        """Add pan and zoom controls to main toolbar."""
        zoomlabel = QLabel('Zoom')
        zoominAct = QAction('+', self)
        # import ipdb; ipdb.set_trace()
        zoominAct.triggered.connect(
            lambda: self.FilePlot.basic_zoom(scale_factor=0.5))
        zoomoutAct = QAction('–', self)
        zoomoutAct.triggered.connect(
            lambda: self.FilePlot.basic_zoom(scale_factor=2))
        self.toolbar.addAction(zoominAct)
        self.toolbar.addWidget(zoomlabel)
        self.toolbar.addAction(zoomoutAct)
        self.toolbar.addSeparator()
        panlabel = QLabel('Pan')
        panlAct = QAction('←', self)
        panlAct.triggered.connect(
            lambda: self.FilePlot.basic_pan(move_factor=-0.1))
        panrAct = QAction('→', self)
        panrAct.triggered.connect(
            lambda: self.FilePlot.basic_pan(move_factor=0.1))
        self.toolbar.addAction(panlAct)
        self.toolbar.addWidget(panlabel)
        self.toolbar.addAction(panrAct)

    def _setup_toolbar(self):
        """Set up toolbar with plot controls (zoom and pan)."""
        self.toolbar.addWidget(SpacerWidget())
        self._add_plot_controls()
        self.toolbar.addWidget(SpacerWidget())

    # @QtCore.pyqtSlot()
    def select_file(self):
        """Bring up a file dialog to pick a file."""
        file_dir = os.path.expanduser('~')
        self.file_path, _ = QFileDialog.getOpenFileName(
                                self, "Select Files", file_dir,
                                "activpal data (*.dat, *.datx)")

    def _setup_window(self):
        """Set up window and plot canvas."""
        self.FilePlot = UIFilePlot(parent=self)
        self.setWindowTitle("Raw activPAL Data Viewer")
        self.setCentralWidget(self.FilePlot)

    def run_main(self):
        """Fetch a data file and plot it."""
        self.FilePlot.load_data(self.file_path)
        self.FilePlot.new_plot()


class UIFilePlot(QWidget):
    """A QWidget which displays activPAL raw data (x, y, z and rss)."""

    def __init__(self, parent=None, file_path=None, center=None, width=None):
        """Create a UIFilePlot widget."""
        super(UIFilePlot, self).__init__(parent)
        self.file_path = file_path

        main_layout = QVBoxLayout()
        self._create_canvas()
        main_layout.addWidget(self.canvas)
        self.canvas.mpl_connect('key_press_event', self._key_press)
        self.setLayout(main_layout)
        self.setMinimumHeight(500)
        self.setMinimumWidth(500)
        if self.file_path is not None:
            self.load_data()

    def _create_canvas(self):
        """Create the plot canvas."""
        self.fig = Figure(dpi=100, facecolor='none', frameon=False)
        self.canvas = FigureCanvas(self.fig)
        gs = GridSpec(3, 1, height_ratios=[3.5, 6, 0.5],
                      hspace=0, left=0.1, top=0.95, right=0.95)
        self.axes = [self.fig.add_subplot(gs[0])]
        for i in range(1, 3):
            self.axes.append(self.fig.add_subplot(gs[i], sharex=self.axes[0]))
        self.axes[1].set_prop_cycle('color', ['r', 'g', 'b'])
        self.axes[0].yaxis.grid(True)
        self.axes[1].yaxis.grid(True)
        self.axes[0].axes.get_xaxis().set_visible(False)
        self.axes[1].axes.get_xaxis().set_visible(False)
        self.axes[0].set_ylim([0, 3.5])
        self.axes[1].set_ylim([-2, 2])
        self.axes[2].set_ylim([0, 1])
        self.axes[0].set_yticks([0.5, 1, 1.5, 2, 2.5, 3, 3.5])
        self.axes[2].axes.get_yaxis().set_visible(False)
        self.axes[0].set_ylabel('RSS Acceleration (g)')
        self.axes[1].set_ylabel('3D Acceleration (g)')
        self.canvas.setFocusPolicy(QtCore.Qt.WheelFocus)
        self.canvas.setFocus()
        self.canvas.draw()

    def load_data(self, file_path=None):
        """
        Load the given data file.

        Parameters
        ----------
        file_path : str
            The path to a raw activPAL data file.

        """
        if file_path is not None:
            self.file_path = file_path
        self.data = ActivpalData(self.file_path)

    def new_plot(self, center=None, width=None):
        """
        Create a fresh plot from the loaded file.

        Parameters
        ----------
        center : float
            The point the plot should be horizontally centered around.
        width : float
            The width of the plot (range of the x axis).

        """
        self.clear_plot()
        if center is None and width is not None:
            # Set center
            start_datetime = mdates.date2num(self.data.signals.index[0])
            center = start_datetime + (width / 2)
        if width is not None:
            # Set X lim (zoom)
            if isinstance(center, datetime):
                center = mdates.date2num(center)
            half_win = width / 2
            new_xlim = (center - half_win, center + half_win)
        else:
            new_xlim = (mdates.date2num(self.data.signals.index[0]),
                        mdates.date2num(self.data.signals.index[-1]))
        self.axes[0].set_xlim(new_xlim)
        self.axes[0].set_title(os.path.basename(self.file_path))
        self.axes[0].plot(self.data.signals.index, self.data.rss,
                          color='tab:blue')
        self.axes[1].plot(self.data.signals.index,
                          self.data.signals[['x', 'y', 'z']], alpha=0.6)
        self._set_xticks()
        self.canvas.draw()

    def _set_xticks(self):
        """Set the format and location of the plots xticks."""
        loc = mdates.AutoDateLocator(minticks=3, maxticks=7)
        datetimefmt = mdates.AutoDateFormatter(loc)
        self.axes[0].xaxis.set_major_formatter(datetimefmt)
        self.axes[0].xaxis.set_major_locator(loc)

    def clear_plot(self):
        """Clear lines from the plot."""
        for i in range(len(self.axes)):
            lines = self.axes[i].get_lines()
            for j in range(len(lines)):
                lines.pop(0).remove()
        self.canvas.draw()

    def _key_press(self, event):
        """Respond to key presses."""
        zoom_keys = {'up', 'down', 'shift+up', 'shift+down'}
        pan_keys = {'left', 'right', 'shift+left', 'shift+right'}
        if event.key in zoom_keys:
            self._keyboard_zoom(event)
        elif event.key in pan_keys:
            self._keyboard_pan(event)
        # else:
        #     # Debug code
        #     print(event.key)

    def basic_zoom(self, scale_factor=2, xhold=None):
        """
        Zoom in on the plot (horizontally).

        Parameters
        ----------
        scale_factor : int
            The path to a raw activPAL data file.
        xhold :
            The x axis value to hold static.

        """
        ax = self.axes[0]
        cur_xlim = ax.get_xlim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0])
        # set new limits
        new_xrange = cur_xrange * scale_factor
        if xhold is None:  # Make xhold the (x)center of the plot
            xhold = cur_xlim[0] + (cur_xrange / 2)
        # Set minimum xrange as the time between samples / data points
        try:
            min_xrange = 1 / (86400 * self.data.metadata.hz)
        except AttributeError:
            min_xrange = 1 / 86400

        if new_xrange > min_xrange:
            cur_left_proportion = (xhold - cur_xlim[0]) / cur_xrange
            new_left_distance = cur_left_proportion * new_xrange
            new_right_distance = new_xrange - new_left_distance
            new_xlim = (xhold - new_left_distance,
                        xhold + new_right_distance)
            ax.set_xlim(new_xlim)
            self._set_xticks()
            self.canvas.draw()

    def _keyboard_zoom(self, event):
        """Control zoom using keyboard up and down arrow keys."""
        if event.inaxes is not None:
            xdata = event.xdata
        else:
            # basic_zoom will hold center of the xaxis if xhold/xdata is None
            xdata = None
        base_scale = 2
        if event.key == 'up':
            # deal with zoom in
            scale_factor = 1/base_scale
        elif event.key == 'down':
            # deal with zoom out
            scale_factor = base_scale
        elif event.key == 'shift+up':
            # deal with zoom in
            scale_factor = 1 - ((1/base_scale) * 0.1)
        elif event.key == 'shift+down':
            # deal with zoom out
            scale_factor = 1 + ((base_scale - 1) * 0.1)
        else:
            # deal with something that should never happen
            scale_factor = 1
        self.basic_zoom(scale_factor=scale_factor, xhold=xdata)

    def basic_pan(self, move_factor=0):
        """
        Pan the plot (horizontally).

        Parameters
        ----------
        move_factor : float
            Decimal fraction which controls how far to jump left (-) or right (+).

        """
        ax = self.axes[0]
        cur_xlim = ax.get_xlim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0])
        mv_amount = cur_xrange * move_factor
        new_xlim = (cur_xlim[0] + mv_amount, cur_xlim[1] + mv_amount)
        # Not trying to scroll too far left
        cond1 = new_xlim[1] > mdates.date2num(self.data.signals.index[0])
        # Not trying to scroll too far right
        cond2 = new_xlim[0] < mdates.date2num(self.data.signals.index[-1])
        if cond1 and cond2:
            ax.set_xlim(new_xlim)
            self._set_xticks()
            self.canvas.draw()

    def _keyboard_pan(self, event):
        """Control pan using keyboard left and right arrow keys."""
        base_scale = 0.5
        if event.key == 'left':
            # deal with zoom in
            move_factor = 0 - base_scale
        elif event.key == 'right':
            # deal with zoom out
            move_factor = base_scale
        elif event.key == 'shift+left':
            # deal with zoom in
            move_factor = 0 - (base_scale * 0.1)
        elif event.key == 'shift+right':
            # deal with zoom out
            move_factor = base_scale * 0.1
        self.basic_pan(move_factor=move_factor)


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
