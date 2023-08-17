# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import numpy as np
from matplotlib.ticker import FormatStrFormatter

def update_fluorescence(image_data, axes_image, max_counts = -1):
    """
    updates a the data in a fluorescence  plot. This is more efficient than replotting from scratch
    Args:
        image_data: 2D - array
        axes_image: axes object on which to plot
        implot: reference to image plot
    Returns:

    """

    if max_counts >= 0:
        image_data = np.clip(image_data, 0, max_counts)

    implot = axes_image.images[0]
    colorbar = implot.colorbar

    implot.set_data(image_data)

    implot.autoscale()

    implot.set_clim(np.min(image_data, None))

    if colorbar is not None and max_counts < 0:
        # colorbar_min = 0
        colorbar_min = np.min(image_data)
        colorbar_max = np.max(image_data)
        colorbar_labels = [np.floor(x) for x in np.linspace(colorbar_min, colorbar_max, 5, endpoint=True)]
        colorbar.set_ticks(colorbar_labels)
        #colorbar.set_clim(colorbar_min, colorbar_max)
        colorbar.mappable.set_clim(colorbar_min, colorbar_max)
        colorbar.update_normal(implot)


def plot_fluorescence(image_data, extent, axes_image, max_counts = -1, colorbar = None, labels = None, aspect=1):
    """
    plots fluorescence data in a 2D plot
    Args:
        image_data: 2D - array
        extent: vector of length 4, i.e. [x_min, x_max, y_max, y_min]
        axes_image: axes object on which to plot
        max_counts: cap colorbar at this value if negative autoscale
        labels: labels for plotting [title, x_label, y_label, cbar_label]

    Returns:

    """
    if max_counts >= 0:
        image_data = np.clip(image_data, 0, max_counts)

    if labels is None:
        labels = ['Confocal Image', r'V$_x$ [V]', r'V$_y$ [V]', 'kcounts/sec']

    extra_x_extent = (extent[1]-extent[0])/float(2*(len(image_data[0])-1))
    extra_y_extent = (extent[2]-extent[3])/float(2*(len(image_data)-1))
    extent = [extent[0] - extra_x_extent, extent[1] + extra_x_extent, extent[2] + extra_y_extent, extent[3] - extra_y_extent]

    fig = axes_image.get_figure()

    implot = axes_image.imshow(image_data, cmap='pink', interpolation="nearest", extent=extent, aspect=aspect)

    title, x_label, y_label, cbar_label = labels
    axes_image.set_xlabel(x_label)
    axes_image.set_ylabel(y_label)
    axes_image.set_title(title)

    # explicitly round x_ticks because otherwise they have too much precision (~17 decimal points) when displayed
    # on plot
    axes_image.set_xticklabels([round(xticklabel, 4) for xticklabel in axes_image.get_xticks()], rotation=90)

    if np.min(image_data)<200:
        #colorbar_min = 0
        colorbar_min = np.min(image_data)
    else:
        colorbar_min = np.min(image_data)

    if max_counts < 0:
        colorbar_max = np.max(image_data)
    else:
        colorbar_max = max_counts
    colorbar_labels = [np.floor(x) for x in np.linspace(colorbar_min, colorbar_max, 5, endpoint=True)]

    if max_counts <= 0:
        implot.autoscale()

    if colorbar is None:
        colorbar = fig.colorbar(implot, label=cbar_label)
        colorbar.set_ticks(colorbar_labels)
        colorbar.mappable.set_clim(colorbar_min, colorbar_max)
    else:
        colorbar = fig.colorbar(implot, cax=colorbar.ax, label=cbar_label)
        colorbar.set_ticks(colorbar_labels)
        colorbar.mappable.set_clim(colorbar_min, colorbar_max)

def plot_fluorescence_pos(image_data, extent, axes_image, max_counts = -1, colorbar = None):
    """
    plots fluorescence data in a 2D plot
    Args:
        image_data: 2D - array
        extent: vector of length 4, i.e. [x_min, x_max, y_max, y_min]
        axes_image: axes object on which to plot
        max_counts: cap colorbar at this value if negative autoscale

    Returns:

    """

    extent = [extent[2], extent[3], extent[1], extent[0]]

    if max_counts >= 0:
        image_data = np.clip(image_data, 0, max_counts)

    fig = axes_image.get_figure()

    implot = axes_image.imshow(image_data, cmap='pink', interpolation="nearest", extent=extent)
    axes_image.set_xlabel(r'pos$_{outer}$ [mm]')
    axes_image.set_ylabel(r'pos$_{inner}$ [mm]')
    axes_image.set_title('Position scan: NV fluorescence')

    # explicitly round x_ticks because otherwise they have too much precision (~17 decimal points) when displayed
    # on plot
    axes_image.set_xticklabels([round(xticklabel, 4) for xticklabel in axes_image.get_xticks()], rotation=90)

    if np.min(image_data)<200:
        colorbar_min = 0
    else:
        colorbar_min = np.min(image_data)

    if max_counts < 0:
        colorbar_max = np.max(image_data)
        implot.autoscale()
    else:
        colorbar_max = max_counts
    colorbar_labels = [np.floor(x) for x in np.linspace(colorbar_min, colorbar_max, 5, endpoint=True)]

    if max_counts <= 0:
        implot.autoscale()

    if colorbar is None:
        colorbar = fig.colorbar(implot, label='kcounts/sec')
        colorbar.set_ticks(colorbar_labels)
        colorbar.set_clim(colorbar_min, colorbar_max)
    else:
        colorbar = fig.colorbar(implot, cax=colorbar.ax, label='kcounts/sec')
        colorbar.set_ticks(colorbar_labels)
        colorbar.set_clim(colorbar_min, colorbar_max)