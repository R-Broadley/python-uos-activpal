#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 21 2017

@author: R-Broadley
"""

import sys
import os
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QWidget,
                             QDesktopWidget, QToolBar, QAction, QLabel,
                             QPushButton, QLineEdit, QSizePolicy,
                             QHBoxLayout, QVBoxLayout, qApp)

# Enable High DPI Scaling
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class BaseMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(BaseMainWindow, self).__init__(parent)
        self.resources = '/'.join([os.path.dirname(__file__), 'resources'])
        self.setGeometry(*self.base_geometry)
        self.centerOnScreen()
        self.style = """
            QMainWindow{
                background-color: rgba(255, 255, 255, 100%);
            }
            .QLabel{
                font-size: 15px;
            }"""
        self.setStyleSheet(self.style)
        toolbarstyle = """
            QToolBar{{
                background-image: url("{bkg_img}");
                background-repeat: repeat-x;
                border: 0px;
                qproperty-minimumSize: 100% 60px;
            }}
            .QWidget{{
                background-color: rgba(0, 0, 0, 0%);
            }}
            .QToolButton{{
                background-color: rgba(0, 0, 0, 0%);
                border: 0px;
                color: white;
                qproperty-minimumSize: 25px 48px;
                qproperty-maximumSize: 100px 48px;
                font-size: 25px;
                margin-bottom: 4px;
                }}
            .QToolButton:hover{{
                background-color: rgba(0, 0, 0, 20%);
            }}
            .QPushButton{{
                background-color: rgba(0, 0, 0, 0%);
                border: 0px;
                color: white;
                font-size: 25px;
                qproperty-iconSize: 48px 48px;
                qproperty-minimumSize: 25px 48px;
                qproperty-maximumSize: 100px 48px;
                qproperty-flat: True;
                padding-left: 10px;
                padding-right: 10px;
                margin-bottom: 4px;
            }}
            .QPushButton:checked{{
                background-color: rgba(0, 0, 0, 0%);
                padding-top: 3px;
                border-bottom: 3px solid black;
                qproperty-flat: True;
            }}
            .QPushButton:hover{{
                background-color: rgba(0, 0, 0, 20%);
                qproperty-flat: True;
            }}
            .QLabel{{
                background-color: rgba(0, 0, 0, 0%);
                color: white;
                font-size: 20px;
                qproperty-minimumSize: 25px 48px;
                qproperty-maximumSize: 100px 48px;
                border: 0px solid black;
                padding: 0px;
                margin-bottom: 4px;
            }}"""
        toolbarstyle = toolbarstyle.format(
            bkg_img='/'.join([self.resources, 'toolbar_bkground.png']))
        self.toolbar = self.addToolBar('Controls')
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.toolbar.setStyleSheet(toolbarstyle)
        self.statusBar().showMessage('Ready')

    def centerOnScreen(self):
        """Centers the window on the screen."""
        resolution = QDesktopWidget().screenGeometry()
        self.move((resolution.width() / 2) - (self.frameSize().width() / 2),
                  (resolution.height() / 2) - (self.frameSize().height() / 2))

    @property
    def base_geometry(self):
        return 0, 0, 1000, 700


class BaseSubWindow(BaseMainWindow):
    def __init__(self, parent=None):
        super(BaseSubWindow, self).__init__(parent)
        self.statusBar().hide()

    def setup_basic_toolbar(self):
        self.buttonleft = QAction('No', self)
        self.buttonleft.triggered.connect(self.left_button_action)
        self.toolbar.addAction(self.buttonleft)
        self.toolbar.addWidget(SpacerWidget())
        self.buttonright = QAction('Yes', self)
        self.buttonright.triggered.connect(self.right_button_action)
        self.toolbar.addAction(self.buttonright)

    def setup_one_button_toolbar(self):
        self.toolbar.addWidget(SpacerWidget())
        self.buttonright = QAction('OK', self)
        self.buttonright.triggered.connect(self.right_button_action)
        self.toolbar.addAction(self.buttonright)

    def left_button_action(self):
        pass

    def right_button_action(self):
        pass

    def closeEvent(self, *args, **kwargs):
        super(QMainWindow, self).closeEvent(*args, **kwargs)
        if hasattr(self, 'launch_on_close') and callable(self.launch_on_close):
            self.launch_on_close()

    @property
    def base_geometry(self):
        return 0, 0, 400, 200


class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super(BaseDialog, self).__init__(parent)
        # Setup
        self.resources = '/'.join([os.path.dirname(__file__), 'resources'])
        self.style = """
            QDialog{
                background-color: rgba(255, 255, 255, 100%);
            }
            .QLabel{
                font-size: 15px;
            }"""
        self.setStyleSheet(self.style)
        self.setGeometry(*self.base_geometry)
        self.setFixedWidth(self.base_geometry[2])
        self.setFixedHeight(self.base_geometry[3])
        self.centerOnScreen()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setup_controlbar()
        # self.setup_one_button_toolbar()
        layout.addWidget(self.controlbar)
        self.setup_main_space()
        layout.addWidget(self.main_space)
        self.setLayout(layout)
        # Uncomment one of the below for testing only
        # self.setup_one_button_toolbar()
        # self.setup_two_button_toolbar()

    def centerOnScreen(self):
        """Centers the window on the screen."""
        resolution = QDesktopWidget().screenGeometry()
        self.move((resolution.width() / 2) - (self.frameSize().width() / 2),
                  (resolution.height() / 2) - (self.frameSize().height() / 2))

    def setup_controlbar(self):
        self.controlbar = QWidget()
        controlbarstyle = """
            .QWidget{{
                background-image: url("{bkg_img}");
                background-repeat: repeat-x;
                background-color: rgba(0, 0, 0, 0%);
                qproperty-minimumSize: 100% 60px;
                border: 0px solid black;
            }}
            .QPushButton{{
                background-color: rgba(0, 0, 0, 0%);
                border: 0px black solid;
                color: white;
                font-size: 25px;
                qproperty-iconSize: 48px 48px;
                qproperty-minimumSize: 25px 48px;
                qproperty-maximumSize: 150px 48px;
                qproperty-flat: True;
                padding-left: 10px;
                padding-right: 10px;
                margin-bottom: 4px;
            }}
            .QPushButton:hover{{
                background-color: rgba(0, 0, 0, 20%);
            }}"""
        controlbarstyle = controlbarstyle.format(
            bkg_img='/'.join([self.resources, 'toolbar_bkground.png']))
        self.controlbar.setStyleSheet(controlbarstyle)
        self.controlbar.setGeometry(0, 0, self.base_geometry[2], 60)
        self.controlbar.setMaximumHeight(60)
        self.controlbar_layout = QHBoxLayout()
        self.controlbar_layout.setContentsMargins(10, 0, 10, 0)
        self.controlbar.setLayout(self.controlbar_layout)
        # Method Redirects
        self.controlbar.addWidget = self.controlbar_addWidget

    def setup_one_button_toolbar(self):
        self.buttonright = QPushButton('OK', self)
        self.buttonright.clicked.connect(self.right_button_action)
        self.controlbar.addWidget(SpacerWidget())
        self.controlbar.addWidget(self.buttonright)

    def setup_two_button_toolbar(self):
        self.buttonleft = QPushButton('No', self)
        self.buttonleft.clicked.connect(self.left_button_action)
        self.controlbar.addWidget(self.buttonleft)
        self.controlbar.addWidget(SpacerWidget())
        self.buttonright = QPushButton('Yes', self)
        self.buttonright.clicked.connect(self.right_button_action)
        self.controlbar.addWidget(self.buttonright)

    def left_button_action(self):
        self.reject()

    def right_button_action(self):
        self.accept()

    def setup_main_space(self):
        self.main_space = SpacerWidget()
        self.main_space_layout = QVBoxLayout()
        self.main_space.setLayout(self.main_space_layout)
        # Method Redirects
        self.addWidget = self.main_space_addWidget

    def controlbar_addWidget(self, widget):
        self.controlbar_layout.addWidget(widget)

    def main_space_addWidget(self, widget):
        self.main_space_layout.addWidget(widget)

    @property
    def base_geometry(self):
        return 0, 0, 400, 200


class BaseMessageDialog(BaseDialog):
    def __init__(self, parent=None, msg=None):
        super(BaseMessageDialog, self).__init__(parent)
        self.setup_one_button_toolbar()
        if msg is not None:
            self.msg = QLabel(msg)
        else:
            self.msg = QLabel('')
        self.msg.setAlignment(QtCore.Qt.AlignCenter)
        self.main_space_addWidget(self.msg)

    def set_message(self, msg):
        self.msg.setText(msg)


class BaseQuestionDialog(BaseDialog):
    def __init__(self, parent=None, question=None):
        super(BaseQuestionDialog, self).__init__(parent)
        self.setup_two_button_toolbar()
        if question is not None:
            self.question = QLabel(question)
        else:
            self.question = QLabel('')
        self.question.setAlignment(QtCore.Qt.AlignCenter)
        self.main_space_addWidget(self.question)

    def set_question(self, question):
        self.question.setText(question)


class SpacerWidget(QWidget):
    def __init__(self, parent=None):
        super(SpacerWidget, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class QuestionResponse(QWidget):
    def __init__(self, parent=None):
        super(QuestionResponse, self).__init__(parent)
        widget_layout = self.layout
        self.question = QLabel('')
        self.response_box = QLineEdit(self)
        widget_layout.addWidget(self.question)
        widget_layout.addWidget(self.response_box)
        self.setLayout(widget_layout)

    @property
    def layout(self):
        return QHBoxLayout()


class VQuestionResponse(QuestionResponse):
    def __init__(self, parent=None):
        super(VQuestionResponse, self).__init__(parent)
        self.question.setAlignment(QtCore.Qt.AlignCenter)

    @property
    def layout(self):
        return QVBoxLayout()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = BaseMainWindow()
    w.show()
    sys.exit(app.exec_())
