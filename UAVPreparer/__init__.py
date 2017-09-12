# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UAVPreparer
                                 A QGIS plugin
 This plug-in examines height properties on a DSM
                             -------------------
        begin                : 2017-09-09
        copyright            : (C) 2017 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load UAVPreparer class from file UAVPreparer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .uav_preparer import UAVPreparer
    return UAVPreparer(iface)
