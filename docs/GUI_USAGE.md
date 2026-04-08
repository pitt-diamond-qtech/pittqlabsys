# GUI Documentations

## OLD GUI (please note that these features are kept in the new GUI):
### Experiment Tab:
- **[experiment_guide_1](guides/experiment_guide_1.jpg)** - Experiment Guide 1
- **[experiment_guide_2](guides/experiment_guide_2.jpg)** - Experiment Guide 2
- **[experiment_guide_3](guides/experiment_guide_3.jpg)** - Experiment Guide 3
- **[experiment_guide_4](guides/experiment_guide_4.jpg)** - Experiment Guide 4
- **[experiment_guide_5](guides/experiment_guide_5.jpg)** - Experiment Guide 5
- **[experiment_guide_6](guides/experiment_guide_6.jpg)** - Experiment Guide 6
### Devices Tab:
You can use the devices Tab to control all of you configured devices. Please edit your config.json to add your device. Only devices inhereting from the Device Class can be implemented here. To add more Parameters, programmers need to add more settings in their device file)
- **[Devices_tab](guides/Devices_tab.jpg)** - Devices_tab

## NEW GUI:
### spectrum analyzer tab:
- **[Spectrum_analyzer_tab](guides/Spectrum_analyzer_tab.jpg)** - Spectrum_analyzer_tab
you can use this tab to connect your agilent 8596E (communication via GPIB), start and stop plotting, adjust span, center frequency, marker, marker span, resolution BW, video BW, Video AVG. To use FFT mode, click on start FFT and stop FFT instead of start and stop. You can choose your window through the dropdown menu.
In addition, you can take a snapshot of your graph and save.

### Positioning tab:
- **[Positioning_tab](guides/Positioning_tab.jpg)** - Positioning_tab
This tab was made from many widgets: display, positioning, and camera widgets. To add new cameras/sensors you need to program its widget and add it as an option in the positioning Gui code and designer. You should follow the same variable names for it to work automatically with our display GUI code. To add more positioning stages, add them as an option in designer and positioning GUI code. Again you have to follow the same variable names and function calls that we have in the positioning GUI code.   
You can adjust the position of your motors and watch yoour sensor in real time. You can switch from live to snapshot. You can adjust the crosshair and watch the 2D plots intensity VS position along each line. You can also move the crosshair and adjust its thickness, which adjusts the averaging of the 2D plots.  
We also have Find NV algorithm where you select which point, save 4 corners, save old NV position, then if you take your sample and would like to get data from the same NV center, you can just save the positions of the 4 corners and our algorithm should find where your NV should be. Please note that this is dependent on the jitter of the motors and the tilt of the sample so you will need to take more confocal scans. This will get you close though. 

### Data saving tab:
- **[Data_saving_tab](guides/Data_saving_tab.jpg)** - Data_saving_tab
You can go to your data saving path, see hdf5 data, see images, create, rename, and delete files here. Most importantly, you can see your data when you click on the file, click read data button, and you can clich view value to see the value of the data point. As for 04/01/2026: this is only linked to the positioning tab (your path is automatically adjusted when you navigate to the data saving tab). For future implementations, programmers can decide whether data saving path should go on the json, the experiment settings, or in a way that is similar to the positioning code.
