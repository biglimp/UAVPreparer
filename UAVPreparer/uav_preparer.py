# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UAVPreparer
                                 A QGIS plugin
 This plug-in examines height properties on a DSM
                              -------------------
        begin                : 2017-09-09
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.gui import QgsMapLayerComboBox, QgsMapLayerProxyModel, QgsFieldComboBox, QgsFieldProxyModel, QgsMessageBar
from qgis.core import QgsVectorLayer
import webbrowser
import numpy as np
from osgeo import gdal
import subprocess
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from uav_preparer_dialog import UAVPreparerDialog
import os.path


class UAVPreparer:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'UAVPreparer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&UAV Preparer')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'UAVPreparer')
        self.toolbar.setObjectName(u'UAVPreparer')

        # Declare variables
        self.outputfile = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('UAVPreparer', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        # Create the dialog (after translation) and keep reference
        self.dlg = UAVPreparerDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/UAVPreparer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Access the raster layer
        self.layerComboManagerDSM = QgsMapLayerComboBox(self.dlg.widgetDSM)
        self.layerComboManagerDSM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSM.setFixedWidth(175)
        self.layerComboManagerDSM.setCurrentIndex(-1)

        # Access the vector layer and an attribute field
        self.layerComboManagerPoint = QgsMapLayerComboBox(self.dlg.widgetPointLayer)
        self.layerComboManagerPoint.setCurrentIndex(-1)
        self.layerComboManagerPoint.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.layerComboManagerPoint.setFixedWidth(175)
        self.layerComboManagerPointField = QgsFieldComboBox(self.dlg.widgetField)
        self.layerComboManagerPointField.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPoint.layerChanged.connect(self.layerComboManagerPointField.setLayer)

        # Set up of file save dialog
        self.fileDialog = QFileDialog()
        self.dlg.pushButtonSave.clicked.connect(self.savefile)

        # Set up for the Help button
        self.dlg.helpButton.clicked.connect(self.help)

        # Set up for the Run button
        self.dlg.runButton.clicked.connect(self.start_progress)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UAV Preparer'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):

        # re-setting scroll-down lists
        self.layerComboManagerDSM.setCurrentIndex(-1)
        self.layerComboManagerPoint.setCurrentIndex(-1)

        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def savefile(self):
        self.outputfile = self.fileDialog.getSaveFileName(None, "Save File As:", None, "Text Files (*.txt)")
        self.dlg.textOutput.setText(self.outputfile)

    def help(self):
        url = "https://github.com/biglimp/UAVPreparer"
        webbrowser.open_new_tab(url)

    def start_progress(self):

        if not self.outputfile:
            QMessageBox.critical(None, "Error", "Specify an output file")
            return

        # Acquiring geodata and attributes
        dsm_layer = self.layerComboManagerDSM.currentLayer()
        if dsm_layer is None:
            QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            return
        else:
            provider = dsm_layer.dataProvider()
            filepath_dsm = str(provider.dataSourceUri())

        point_layer = self.layerComboManagerPoint.currentLayer()
        if point_layer is None:
            QMessageBox.critical(None, "Error", "No valid vector point layer is selected")
            return
        else:
            vlayer = QgsVectorLayer(point_layer.source(), "polygon", "ogr")

        point_field = self.layerComboManagerPointField.currentField()
        idx = vlayer.fieldNameIndex(point_field)
        if idx == -1:
            QMessageBox.critical(None, "Error", "An attribute filed with unique fields must be selected")
            return

        ### main code ###

        #  set radius
        rSquare = 100  # half picture size

        # finding ID column
        idx = vlayer.fieldNameIndex(point_field)

        numfeat = vlayer.featureCount()
        result = np.zeros([numfeat, 4])

        self.dlg.progressBar.setRange(0, numfeat)
        i = 0
        for f in vlayer.getFeatures():
            self.dlg.progressBar.setValue(i + 1)
            # get the coordinate for the point
            y = f.geometry().centroid().asPoint().y()
            x = f.geometry().centroid().asPoint().x()

            gdalclipdsm = 'gdalwarp -dstnodata -9999 -q -overwrite -te ' + str(x - rSquare) + ' ' + str(
                y - rSquare) + ' ' + str(x + rSquare) + ' ' + str(y + rSquare) + ' -of GTiff ' + filepath_dsm + ' ' + self.plugin_dir + '/clipdsm.tif'

            # call the gdal function
            si = subprocess.STARTUPINFO()  # used to suppress cmd window
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.call(gdalclipdsm, startupinfo=si)

            dataset = gdal.Open(self.plugin_dir + '/clipdsm.tif')
            dsm_array = dataset.ReadAsArray().astype(np.float)
            result[i, 0] = int(f.attributes()[idx])
            result[i, 1] = np.mean(dsm_array)
            result[i, 2] = np.max(dsm_array)
            result[i, 3] = np.min(dsm_array)

            i = i + 1

        # Saving to file
        numformat = '%d ' + '%6.2f ' * 3
        headertext = 'id mean max min'
        np.savetxt(self.outputfile, result, fmt=numformat, delimiter=' ', header=headertext)

        self.iface.messageBar().pushMessage('UAV Preparer. Operation successful!', level=QgsMessageBar.INFO, duration=5)
