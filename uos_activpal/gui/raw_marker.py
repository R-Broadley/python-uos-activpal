#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A GUI application to view the raw activPAL accelerometer data.

Created on 21 Jun 2017

@author: R-Broadley
"""

import sys
import os
import numpy as np
import matplotlib.dates as mdates
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QFileDialog, QWidget, QPushButton, QLabel, QSlider,
                             QAction, QHBoxLayout, qApp)
from scipy.signal import argrelmax
from .base import BaseQuestionDialog, SpacerWidget
from .raw_viewer import UIFilePlot
from .raw_viewer import MainWindow as BasePlotWindow


# This is a subclass of raw_viewer.MainWindow (imported as BasePlotWindow)
class MainWindow(BasePlotWindow):
    """
    A raw_viewer.MainWindow subclass which adds the ability to mark points.

    """

    def __init__(self, parent=None, request_confidence=True):
        """
        Create an instance of a MainWindow.

        Parameters
        ----------
        parent : object
            The parent object.
        request_confidence : bool
            Sets whether a dialog will appear, when the save button is pressed,\
                which requests the confidence the correct point has been marked.

        """
        super(MainWindow, self).__init__(parent)
        self.request_confidence = request_confidence

    def _setup_toolbar(self):
        """Add Save button, plot controls and Mark button to toolbar."""
        saveAct = QAction('Save', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.save_button_action)
        self.toolbar.addAction(saveAct)
        self.toolbar.addWidget(SpacerWidget())
        self._add_plot_controls()
        self.toolbar.addWidget(SpacerWidget())
        self.markbtn = QPushButton('Mark')
        self.markbtn.setCheckable(True)
        self.markbtn.clicked[bool].connect(self.toggle_plot_marking)
        self.toolbar.addWidget(self.markbtn)

    def toggle_plot_marking(self):
        """Activate / Deactivate the plot marking feature."""
        if self.markbtn.isChecked():
            self.FilePlot.mark_active = True
            self.statusBar().showMessage('Marker Active')
        else:
            self.FilePlot.mark_active = False
            self.statusBar().showMessage('Ready')

    def _setup_window(self):
        """Setup window and plot canvas."""
        self.FilePlot = UIFileMarkingPlot(parent=self)
        self.setWindowTitle("Raw activPAL Data Marker")
        self.setCentralWidget(self.FilePlot)

    # @QtCore.pyqtSlot()
    def save_button_action(self):
        """Run pre-save actions then save."""
        # TODO check point has been marked
        if self.request_confidence:
            confidence_dialog = ConfidenceDialog(parent=self)
            confidence_dialog.exec_()
            # import ipdb; ipdb.set_trace()
            if confidence_dialog.result() == 1:
                self.confidence = confidence_dialog.get_confidence()
            else:
                return
        self.save()
        another_point_dialog = AnotherPointDialog(parent=self)
        another_point_dialog.exec_()
        if another_point_dialog.result() == 1:
            self.clear_markers()
        else:
            another_file_dialog = AnotherFileDialog(parent=self)
            another_file_dialog.exec_()
            if another_file_dialog.result() == 1:
                self.load_new()
            else:
                self.close()

    # @QtCore.pyqtSlot()
    def clear_markers(self):
        """Clear all placed markers."""
        self.FilePlot.clear_markers()

    # @QtCore.pyqtSlot()
    def load_new(self):
        """Fetch new file, load the data and plot."""
        self.clear_markers()
        self.select_file()
        self.run_main()

    # @QtCore.pyqtSlot()
    def save(self):
        """Save marked points sample number, datetime, (and confidence) to csv file."""
        file_dir = os.path.expanduser('~')
        save_file_path, _ = QFileDialog.getSaveFileName(
                                self, "Select Save File",
                                '/'.join([file_dir, 'activpal-markers.csv']),
                                "mark record (*.csv)",
                                options=QFileDialog.DontConfirmOverwrite)

        if not os.path.isfile(save_file_path):
            with open(save_file_path, 'w') as f:
                f.write('File,Sample,DateTime,Confidence\n')

        with open(save_file_path, 'a') as f:
            try:
                f.write(self.file_path)
            except AttributeError:
                f.write('Unknown File')
            f.write(',')
            try:
                f.write(str(self.FilePlot.marked_sample))
            except AttributeError:
                f.write('Could not get sample number')
            f.write(',')
            try:
                f.write(str(self.FilePlot.marked_datetime))
            except AttributeError:
                f.write('Could not get datetime')
            f.write(',')
            try:
                f.write(str(self.confidence))
            except AttributeError:
                f.write('NaN')
            f.write('\n')


class UIFileMarkingPlot(UIFilePlot):
    """
    A QWidget which displays, and allow marking of, activPAL raw data (x, y, z and rss).

    """

    def __init__(self, parent=None, file_path=None, center=None, width=None):
        """
        Creates a UIFileMarkingPlot widget.

        Parameters
        ----------
        parent : object
            The parent object.
        file_path : str
            The path of the file to plot.
        center : float
            The point the plot should be horizontally centered around.
        width : float | int
            The width of the plot (range of the x axis) in days.

        """
        super(UIFileMarkingPlot, self).__init__(parent, file_path)
        # Interaction
        self.canvas.mpl_connect('button_press_event', self._on_click)

    def _on_click(self, event):
        """."""
        try:
            self.mark_active
        except AttributeError:
            return
        if event.inaxes is None or not self.mark_active:
            return
        xdata = event.xdata
        xdata_datetime = mdates.num2date(xdata).replace(tzinfo=None)
        if event.button == 1:
            datetime_index = self.data.signals.index
            sn = (np.abs(datetime_index - xdata_datetime)).argmin()
            self.marked_sample = self.get_nearest_peak(
                self.data.rss.values, sn)
            self.marked_datetime = datetime_index[self.marked_sample]
            try:
                self.marker = self.update_marker(
                    self.marker, self.marked_datetime)
            except AttributeError:
                self.marker = self.create_marker(self.marked_datetime)
            self.canvas.draw()

    def create_marker(self, xdata, linecolor='k'):
        """
        Create a marker line on the plot.

        Parameters
        ----------
        xdata :
            The point (x axis) where the marker should be.
        linecolor : str
            The code for the desired line color.

        """
        marker = []
        lineproperties = {'color': linecolor, 'alpha': 1, 'linestyle': ':'}
        for i in range(3):
            ydata = self.axes[i].get_ylim()
            marker.append(self.axes[i].plot(
                [xdata, xdata], ydata, **lineproperties)[0])
            self._set_xticks()
        return marker

    def update_marker(self, marker, xdata):
        """
        Update the location of the given marker.

        Parameters
        ----------
        marker :
            The marker which should be updated.
        xdata :
            The point (x axis) where the marker should be.

        Returns
        -------
        marker:
            The marker (set of lines) which has been updated.

        """
        if not marker == []:
            for m in marker:
                m.set_xdata([xdata, xdata])
            return marker
        else:
            raise AttributeError  # Marker does not exist

    def clear_markers(self):
        """Clear all stored markers."""
        if hasattr(self, 'marker'):
            for i in range(len(self.marker)):
                self.marker.pop(0).remove()
        self.marked_datetime = None
        self.marked_sample = None
        self.canvas.draw()

    def get_nearest_peak(self, input_array, sample_number):
        """
        Find the peak in the given array nearest the given samle number.

        Parameters
        ----------
        input_array : numpy.ndarray
            The array which should be searched for the nearest peak.
        sample_number : int
            The index of the point from which the nearest peak should be found.

        Returns
        -------
        sample_number:
            The sample number of the nearest peak.

        """
        zone_width = 1200
        zone_start = sample_number - zone_width
        if zone_start < 0:
            zone_start = 0
        zone_end = sample_number + zone_width
        if zone_end > len(input_array):
            zone_end = len(input_array)
        test_zone = input_array[zone_start: zone_end]
        peaks = argrelmax(test_zone, order=3)[0] + zone_start
        if len(peaks) is not 0 and np.ptp(test_zone) > 0.25:
            diff = np.abs(peaks - sample_number)
            min_diff_loc = np.argmin(diff)
            return peaks[min_diff_loc]
        else:
            return sample_number


class ConfidenceDialog(BaseQuestionDialog):
    """
    A BaseQuestionDialog to request a confidence rating from the user.

    See Also
    --------
    uos_activpal.gui.base.BaseDialog : A QDialog subclass which includes
        additional setup, mainly styling.
    uos_activpal.gui.base.BaseMessageDialog : A BaseDialog subclass desiged
        for displaying messages.
    uos_activpal.gui.base.BaseQuestionDialog : A BaseDialog subclass desiged
        for asking binary (yes | no) questions.

    """

    def __init__(self, parent=None):
        """
        Create an instance of a ConfidenceDialog.

        Parameters
        ----------
        parent : object
            The parent object.

        """
        super(ConfidenceDialog, self).__init__(parent)
        self.setWindowTitle("Set Confidence")
        self.buttonleft.setText('Return')
        self.buttonright.setText('Submit')
        self.set_question('How confident are you that the point\n'
                          'which you marked is correct?')
        self.confidence_slider = ConfidenceSlider()
        self.main_space_addWidget(self.confidence_slider)

    def get_confidence(self):
        """Get the current confidence rating."""
        return self.confidence_slider.get_slider_value()


class AnotherPointDialog(BaseQuestionDialog):
    """
    A BaseQuestionDialog to ask if the user wants to mark another point in this file.

    See Also
    --------
    uos_activpal.gui.base.BaseDialog : A QDialog subclass which includes
        additional setup, mainly styling.
    uos_activpal.gui.base.BaseMessageDialog : A BaseDialog subclass desiged
        for displaying messages.
    uos_activpal.gui.base.BaseQuestionDialog : A BaseDialog subclass desiged
        for asking binary (yes | no) questions.

    """

    def __init__(self, parent=None):
        """
        Create an instance of a AnotherPointDialog.

        Parameters
        ----------
        parent : object
            The parent object.

        """
        super(AnotherPointDialog, self).__init__(parent)
        self.setWindowTitle("Mark Another Point?")
        self.set_question('Do you want to mark another point in this file?')


class AnotherFileDialog(BaseQuestionDialog):
    """
    A BaseQuestionDialog to ask if the user wants to mark another point in another file.

    See Also
    --------
    uos_activpal.gui.base.BaseDialog : A QDialog subclass which includes
        additional setup, mainly styling.
    uos_activpal.gui.base.BaseMessageDialog : A BaseDialog subclass desiged
        for displaying messages.
    uos_activpal.gui.base.BaseQuestionDialog : A BaseDialog subclass desiged
        for asking binary (yes | no) questions.

    """

    def __init__(self, parent=None):
        """
        Create an instance of a AnotherPointDialog.

        Parameters
        ----------
        parent : object
            The parent object.

        """
        super(AnotherFileDialog, self).__init__(parent)
        self.setWindowTitle("Mark Another File?")
        self.set_question('Do you want to mark a point in another file?')


class ConfidenceSlider(QWidget):
    """
    A Qwidget which contains a 1 to 10 slider and the label 'Confidence:'.

    """

    def __init__(self, parent=None):
        """Create a ConfidenceSlider widget."""
        super(ConfidenceSlider, self).__init__(parent)
        # Slider Widget
        self.slider = QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(10)
        self.slider.setValue(1)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(QSlider.TicksAbove)
        self.slider.setMaximumWidth(250)
        # Slider Value Label
        self.confidencelabel = QLabel('1 / 10')
        self.confidencelabel.setAlignment(QtCore.Qt.AlignRight)
        self.confidencelabel.setMinimumWidth(20)
        self._slider_move()
        self.slider.valueChanged.connect(self._slider_move)
        # Layout
        self.setMaximumWidth(400)
        self.setMaximumHeight(200)
        self_layout = QHBoxLayout()
        self_layout.setContentsMargins(50, 25, 50, 25)
        self_layout.addWidget(QLabel('Confidence:'))
        self_layout.addWidget(self.confidencelabel)
        self_layout.addWidget(QLabel('/ 10'))
        self_layout.addWidget(self.slider)
        self.setLayout(self_layout)

    def _slider_move(self):
        """Function called when the slider is moved (Updates the value label)."""
        self.confidence = self.slider.value()
        self.confidencelabel.setText(str(self.confidence))

    def get_slider_value(self):
        """Returns the current value of the slider."""
        return self.slider.value()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
