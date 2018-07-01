#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A GUI application to view the raw activPAL accelerometer data.

Created on Thu Jun 21 2017

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
    def __init__(self, parent=None, request_confidence=True):
        super(MainWindow, self).__init__(parent)
        self.request_confidence = request_confidence

    def setup_toolbar(self):
        saveAct = QAction('Save', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.save_button_action)
        self.toolbar.addAction(saveAct)
        self.toolbar.addWidget(SpacerWidget())
        self.add_plot_controls()
        self.toolbar.addWidget(SpacerWidget())
        self.markbtn = QPushButton('Mark')
        self.markbtn.setCheckable(True)
        self.markbtn.clicked[bool].connect(self.toggle_fall_marking)
        self.toolbar.addWidget(self.markbtn)

    def toggle_fall_marking(self):
        if self.markbtn.isChecked():
            self.FilePlot.mark_active = True
            self.statusBar().showMessage('Marker Active')
        else:
            self.FilePlot.mark_active = False
            self.statusBar().showMessage('Ready')

    def setup_window(self):
        self.FilePlot = UIFileMarkingPlot(parent=self)
        self.setWindowTitle("Raw activPAL Data Marker")
        self.setCentralWidget(self.FilePlot)

    @QtCore.pyqtSlot()
    def save_button_action(self):
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

    @QtCore.pyqtSlot()
    def clear_markers(self):
        self.FilePlot.clear_markers()

    @QtCore.pyqtSlot()
    def load_new(self):
        self.clear_markers()
        self.select_file()
        self.run_main()

    @QtCore.pyqtSlot()
    def save(self):
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
    def __init__(self, parent=None, file_path=None, center=None, width=None):
        """center is point (datetime) to center in the plot
            width is the number of days which should be shown"""
        super(UIFileMarkingPlot, self).__init__(parent, file_path)
        # Interaction
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def on_click(self, event):
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
        marker = []
        lineproperties = {'color': linecolor, 'alpha': 1, 'linestyle': ':'}
        for i in range(3):
            ydata = self.axes[i].get_ylim()
            marker.append(self.axes[i].plot(
                [xdata, xdata], ydata, **lineproperties)[0])
            self.set_xticks()
        return marker

    def update_marker(self, marker, xdata):
        if not marker == []:
            for m in marker:
                m.set_xdata([xdata, xdata])
            return marker
        else:
            raise AttributeError  # Marker does not exist

    def clear_markers(self):
        if hasattr(self, 'marker'):
            for i in range(len(self.marker)):
                self.marker.pop(0).remove()
        self.marked_datetime = None
        self.marked_sample = None
        self.canvas.draw()

    def get_nearest_peak(self, input_array, sample_number):
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
    def __init__(self, parent=None):
        super(ConfidenceDialog, self).__init__(parent)
        self.setWindowTitle("Set Confidence")
        self.buttonleft.setText('Return')
        self.buttonright.setText('Submit')
        self.set_question('How confident are you that the point\n'
                          'which you marked is correct?')
        self.confidence_slider = ConfidenceSlider()
        self.main_space_addWidget(self.confidence_slider)

    def get_confidence(self):
        return self.confidence_slider.get_slider_value()


class AnotherPointDialog(BaseQuestionDialog):
    def __init__(self, parent=None):
        super(AnotherPointDialog, self).__init__(parent)
        self.setWindowTitle("Mark Another Point?")
        self.set_question('Do you want to mark another point in this file?')


class AnotherFileDialog(BaseQuestionDialog):
    def __init__(self, parent=None):
        super(AnotherFileDialog, self).__init__(parent)
        self.setWindowTitle("Mark Another File?")
        self.set_question('Do you want to mark a point in another file?')


class ConfidenceSlider(QWidget):
    def __init__(self, parent=None):
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
        self.slider_move()
        self.slider.valueChanged.connect(self.slider_move)
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

    def slider_move(self):
        self.confidence = self.slider.value()
        self.confidencelabel.setText(str(self.confidence))

    def get_slider_value(self):
        return self.slider.value()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
