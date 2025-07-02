import numpy as np
from scipy.io import savemat
from src.core.helper_functions import structure_data_for_matlab


filename = 'test_pyton_matlab_save.mat'
filelocation = r'C:\Users\Duttlab\Experiments\AQuISS_default_save_location\data\\' + filename

#MAKE A ARRAY OF TUPLES !!! Structure is important
array = np.array([(1, 'a', False), (np.nan, 'b', True), (3,'c', False)], dtype=[('field1 has a really long name like over 31 characters',float),('field2',object),('field3',bool)])
#dicts save as 1x1 structs only!
dicts = [{'field1':0.5, 'field2':'one'},{'field1':0.6, 'field2':'two'},{'field1':0.8,'field2':'three'}]

savemat(filelocation, {'dicts':dicts, 'tuple_array':array})

#Stack overflow
#https://stackoverflow.com/questions/61542500/convert-multiple-python-dictionaries-to-matlab-structure-array-with-scipy-io-sav


ex_data_1 = {'random_data': [0.8486161845846729, 0.3130657602243422, 0.08220784202620657, 0.7566239357229991, 0.1566956979052001, 0.7763677820680961, 0.2822495884326256, 0.07358801896021061, 0.31546483249754065, 0.09602905292983566, 0.4708363377901481, 0.7606587079228375, 0.5911818105719729, 0.19326385842390115, 0.3569708749172422, 0.06579632322101503, 0.46004952942452815, 0.11000005199119756, 0.7802220450958514, 0.9844957645722522, 0.38069637275321766, 0.3387975697602441, 0.3255874429958806, 0.7306502495430353, 0.815690771973527, 0.7686951861780189, 0.292695932732541, 0.9765989723690504, 0.5490912704525974, 0.3737056760497047, 0.32364875029619977, 0.9531146682182229, 0.8746040122154536, 0.25742952003459707, 0.7057662535379657, 0.2551614160706245, 0.9150765684493058, 0.7244515224434058, 0.5233202410366595, 0.17639138956682998, 0.2516063889187946, 0.19254417798646706, 0.6320315640610223, 0.35385166196057805, 0.11544327009564181, 0.030240801268020756, 0.5848237412619066, 0.9772667456935146, 0.5487955220209074, 0.38684281884035454, 0.45543813051957194, 0.5819199971261986, 0.124871093746875, 0.3149922940983798, 0.8838274557598422, 0.6387070545009906, 0.2341066565754999, 0.2370868196635849, 0.3825689872722846, 0.45526046737403136, 0.15911380778058426, 0.09479991503726515, 0.05006934680646735, 0.6726924720799815],
                'image_data': np.array([[0.84861618, 0.31306576, 0.08220784, 0.75662394, 0.1566957 ,0.77636778, 0.28224959, 0.07358802],
                                        [0.31546483, 0.09602905, 0.47083634, 0.76065871, 0.59118181,0.19326386, 0.35697087, 0.06579632],
                                        [0.46004953, 0.11000005, 0.78022205, 0.98449576, 0.38069637,0.33879757, 0.32558744, 0.73065025],
                                        [0.81569077, 0.76869519, 0.29269593, 0.97659897, 0.54909127,0.37370568, 0.32364875, 0.95311467],
                                        [0.87460401, 0.25742952, 0.70576625, 0.25516142, 0.91507657,0.72445152, 0.52332024, 0.17639139],
                                        [0.25160639, 0.19254418, 0.63203156, 0.35385166, 0.11544327,0.0302408 , 0.58482374, 0.97726675],
                                        [0.54879552, 0.38684282, 0.45543813, 0.58192000, 0.12487109,0.31499229, 0.88382746, 0.63870705],
                                        [0.23410666, 0.23708682, 0.38256899, 0.45526047, 0.15911381,0.09479992, 0.05006935, 0.67269247]])}
ex_settings_1 = {'count': 64, 'name': 'this is a counter', 'wait_time': 0.1,'point2': {'array':np.array([0.1,0.2,0.3,0.4]).reshape((2,2))}, 'plot_style': '2D', 'path': '', 'tag': 'exampleexperiment_1', 'save': False}

ex_data_2 = {'random_data': [0.8486161845846729, 0.3130657602243422, 0.08220784202620657, 0.7566239357229991, 0.1566956979052001, 0.7763677820680961, 0.2822495884326256, 0.07358801896021061, 0.31546483249754065, 0.09602905292983566, 0.4708363377901481, 0.7606587079228375, 0.5911818105719729, 0.19326385842390115, 0.3569708749172422, 0.06579632322101503, 0.46004952942452815, 0.11000005199119756, 0.7802220450958514, 0.9844957645722522, 0.38069637275321766, 0.3387975697602441, 0.3255874429958806, 0.7306502495430353, 0.815690771973527, 0.7686951861780189, 0.292695932732541, 0.9765989723690504, 0.5490912704525974, 0.3737056760497047, 0.32364875029619977, 0.9531146682182229, 0.8746040122154536, 0.25742952003459707, 0.7057662535379657, 0.2551614160706245, 0.9150765684493058, 0.7244515224434058, 0.5233202410366595, 0.17639138956682998, 0.2516063889187946, 0.19254417798646706, 0.6320315640610223, 0.35385166196057805, 0.11544327009564181, 0.030240801268020756, 0.5848237412619066, 0.9772667456935146, 0.5487955220209074, 0.38684281884035454, 0.45543813051957194, 0.5819199971261986, 0.124871093746875, 0.3149922940983798, 0.8838274557598422, 0.6387070545009906, 0.2341066565754999, 0.2370868196635849, 0.3825689872722846, 0.45526046737403136, 0.15911380778058426, 0.09479991503726515, 0.05006934680646735, 0.6726924720799815],
                'image_data': np.array([[0.84861618, 0.31306576, 0.08220784, 0.75662394, 0.1566957 ,0.77636778, 0.28224959, 0.07358802],
                                        [0.31546483, 0.09602905, 0.47083634, 0.76065871, 0.59118181,0.19326386, 0.35697087, 0.06579632],
                                        [0.46004953, 0.11000005, 0.78022205, 0.98449576, 0.38069637,0.33879757, 0.32558744, 0.73065025],
                                        [0.81569077, 0.76869519, 0.29269593, 0.97659897, 0.54909127,0.37370568, 0.32364875, 0.95311467],
                                        [0.87460401, 0.25742952, 0.70576625, 0.25516142, 0.91507657,0.72445152, 0.52332024, 0.17639139],
                                        [0.25160639, 0.19254418, 0.63203156, 0.35385166, 0.11544327,0.0302408 , 0.58482374, 0.97726675],
                                        [0.54879552, 0.38684282, 0.45543813, 0.58192000, 0.12487109,0.31499229, 0.88382746, 0.63870705],
                                        [0.23410666, 0.23708682, 0.38256899, 0.45526047, 0.15911381,0.09479992, 0.05006935, 0.67269247]])}
ex_settings_2 = {'count': 64, 'name': 'this is a counter', 'wait_time': 0.1, 'point2': {'array':np.array([0.1,0.2,0.3,0.4]).reshape((2,2))},  'plot_style': '2D', 'path': '', 'tag': 'exampleexperiment_2', 'save': False}

arr = np.array([(ex_data_1['random_data'],ex_data_1['image_data'],ex_settings_1),(ex_data_2['random_data'],ex_data_2['image_data'],ex_settings_2)], dtype=[('random_data', 'f8', (64,)),('image_data', 'f8', (8, 8)),('experiment_settings',dict)])
savemat(filelocation, {'ex_data':arr})
#print('This arr saves as a 1x2 struct with columns for random_data, image_data, and experiment_settings. The data are arrays with numbers and the settings is a 1x1 struct housing the experiment parameter names and values.')
'''
Need to pay attention to data type and length to get a dtype matlab can interpret correctly

Here is the data type that should be passed for each type of data
 - a single number should be float/int
 - a string should be an object (note object kinda defines everything BUT a simple string is the only object matlab can interpret correctly)
 - an array with number should be f8 (float with 64 bits) and the shape of the array ex: ('name','f8',(8x8)) for a 1D array the shape is (len,) the second component is blank
    -> can use np.shape to get shape
'''

#want to see if we can get each experiment to be its on

#The function structure_data_for_matlab should automate the structing process. Here is first test
filename = 'test_auto_structure.mat'
filelocation = r'C:\Users\Duttlab\Experiments\AQuISS_default_save_location\data\\' + filename

#structured_data = structure_data_for_matlab(data=[ex_data_1,ex_data_2],settings=[ex_settings_1,ex_settings_2],tag='example_experiment')
#savemat(filelocation,structured_data)
#It works the same as above!! One thing is the data and settings should be a list, but this should be actually really easy to do in say the experiment iterator just have a list and append new data set

#need to test infinite recursion and infinite demension structs (inductive proof of 1 and 2 levels)

#Trying to put a 1x2 struct in another 1x2 struct
filename = 'test_recursive_structs.mat'
filelocation = r'C:\Users\Duttlab\Experiments\AQuISS_default_save_location\data\\' + filename


arr_1 = np.array([(0.5,'one',1),(0.6,'two',5),(0.7,'hi',6)], dtype=[('x1',float),('y1',object),('z1',int)])
arr_2 = np.array([(0.7,'three'),(0.8,'four')], dtype=[('x2',float),('y2',object)])
arr_3 = np.array([(0.9,'five'),(1,'six')], dtype=[('x3',float),('y3',object)])
arr_4 = np.array([(1.1,'seven'),(1.2,'eight')], dtype=[('x4',float),('y4',object)])

arr = np.array([(arr_2,arr_4),(arr_4,arr_1),(arr_2,arr_3),(arr_1,arr_3)],dtype=[('field1',object),('field2',object)])
arr_extra_1 = np.array([(arr_2,arr_4),(arr_4,arr_1),(arr_2,arr_3),(arr_1,arr_3)],dtype=[('field1',object),('field2',object)])
arr_extra_2 = np.array([(arr_2,arr_4),(arr_4,arr_1),(arr_2,arr_3),(arr_1,arr_3)],dtype=[('field1',object),('field2',object)])
arr_extra_3 = np.array([(arr_2,arr_4),(arr_4,arr_1),(arr_2,arr_3),(arr_1,arr_3)],dtype=[('field1',object),('field2',object)])

#saving arr creates a 1x4 struct with 8 componets each being 1x2 structs
arr = np.reshape(arr,(2,2))
#savemat(filelocation,{'arr':arr})



filename = 'multi_iterator_data.mat'
filelocation = r'C:\Users\Duttlab\Experiments\AQuISS_default_save_location\data\\' + filename
'''
structured_data_new, dtype_list = structure_data_for_matlab(data=[ex_data_1,ex_data_2],settings=[ex_settings_1,ex_settings_2],tag='example_experiment',return_array=True)
print(dtype_list)

storage_list = [(structured_data_new),(structured_data_new)]
print(np.shape(storage_list))
print(storage_list)
#dtype=[('val_1',object),('val_2',object),('val_3',object),('val_4',object)]
#iterator_2_arr = np.array(storage_list,dtype=dtype_list)
iterator_2 = np.concatenate(storage_list)
print(iterator_2.dtype)
iterator_2_arr = np.array(storage_list)
print(np.shape(iterator_2_arr))
print(iterator_2_arr)
print(iterator_2_arr.dtype)


savemat(filelocation,{'2D_iterator':iterator_2_arr})
'''




'''#reshaping saving as a 2x2 struct with 4 1x1 struct componets each component has 2 feild each a 1x2 struct ie each componet is arr_i

arr_extra_1 = np.reshape(arr_extra_1,(2,2))
arr_extra_2 = np.reshape(arr_extra_2,(2,2))
arr_extra_3 = np.reshape(arr_extra_3,(2,2))
print(np.shape(arr))

complex_arr = np.array([(arr),(arr_extra_2),(arr_extra_3),(arr_extra_1)],dtype=[('field1',object),('field2',object)])
complex_arr = np.reshape(complex_arr,(2,2))
print(np.shape(complex_arr))'''




experiment_aqs = {
    "experiments": {
        "ConfocalScan_Fast": {
            "class": "ConfocalScan_Fast",
            "filepath": r"D:\\PyCharmProjects\\pittqlabsys-dylan-working-repo\\src\\Model\\experiments\\confocal.py",
            "info": "This class runs a confocal microscope scan using the MCL NanoDrive to move the sample stage and the ADwin Gold II to get count data.\nThe code loads a waveform on the nanodrive, starts the Adwin process, triggers a waveform aquisition, then reads the count data array from the Adwin.\n\nTo get accurate counts, the loaded waveforms are extended to compensate for 'warm up' and 'cool down' movements. The data arrays are then\nmanipulated to get the counts for the inputed region.",
            "package": "src",
            "devices": {
                "nanodrive": {
                    "class": "MCLNanoDrive",
                    "settings": {
                        "serial": 2849,
                        "x_pos": 9.533682598157963,
                        "y_pos": 92.0119579548992,
                        "z_pos": 64.22011154093373,
                        "read_rate": 2.0,
                        "load_rate": 2.0,
                        "num_datapoints": 1,
                        "axis": "x",
                        "load_waveform": [
                            0
                        ],
                        "read_waveform": [
                            0
                        ],
                        "mult_ax": {
                            "waveform": [
                                [
                                    0
                                ],
                                [
                                    0
                                ],
                                [
                                    0
                                ]
                            ],
                            "time_step": 1.0,
                            "iterations": 1
                        },
                        "Pixel": {
                            "mode": "low",
                            "polarity": "low-to-high",
                            "binding": "read",
                            "pulse": False
                        },
                        "Line": {
                            "mode": "low",
                            "polarity": "low-to-high",
                            "binding": "load",
                            "pulse": False
                        },
                        "Frame": {
                            "mode": "low",
                            "polarity": "low-to-high",
                            "binding": "read",
                            "pulse": False
                        },
                        "Aux": {
                            "mode": "low",
                            "polarity": "low-to-high",
                            "binding": "read",
                            "pulse": False
                        }
                    }
                },
                "adwin": {
                    "class": "ADwinGold",
                    "settings": {
                        "process_1": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_2": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_3": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_4": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_5": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_6": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_7": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_8": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_9": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        },
                        "process_10": {
                            "load": "",
                            "delay": 3000,
                            "running": False
                        }
                    }
                }
            },
            "settings": {
                "point_a": {
                    "x": 5.0,
                    "y": 5.0
                },
                "point_b": {
                    "x": 95.0,
                    "y": 95.0
                },
                "z_pos": 50.0,
                "resolution": 1.0,
                "time_per_pt": 2.0,
                "ending_behavior": "return_to_origin",
                "3D_scan": {
                    "enable": False,
                    "folderpath": r"D:\\Data\\dylan_staples\\image_NV_confocal_scans"
                },
                "reboot_adwin": False,
                "cropping": {
                    "crop_data": True
                },
                "laser_clock": "Pixel",
                "path": "",
                "tag": "confocalscan_fast",
                "save": False
            }
        }
    }
}
filename = 'test_pyton_matlab_save_aqs.mat'
filelocation = r'C:\Users\Duttlab\Experiments\AQuISS_default_save_location\data\\' + filename
#savemat(filelocation, experiment_aqs)

filename = 'another_test.mat'
filelocation = r'D:\Data\dylan_staples\\' + filename

structured_data = {'ex_sweep_mat_2': np.array([
       ([0.86321529, 0.59724984, 0.22583211], 'x', 4, 3, 'this is a counter', 0.1, 8., 0.1, 'main', '', 'exampleexperiment', 1),
       ([0.07275898, 0.16412021, 0.02875495], 'x', 4, 3, 'this is a counter', 0.1, 8., 0.1, 'main', '', 'exampleexperiment', 1),
       ([0.74131829, 0.61229449, 0.83500967], 'x', 4, 3, 'this is a counter', 0.1, 8., 0.1, 'main', '', 'exampleexperiment', 1),
       ([0.74131829, 0.61229449, 0.83500967], 'x', 4, 3, 'this is a counter', 0.1, 8., 0.1, 'main', '', 'exampleexperiment', 1)
        ],
      dtype=[('random data', '<f8', (3,)), ('python_scan_map_scan_parameter', 'O'), ('python_scan_map_num_steps', '<i4'), ('count', '<i4'), ('name', 'O'), ('wait_time', '<f8'), ('point2_x', '<f8'), ('point2_y', '<f8'), ('plot_style', 'O'), ('path', 'O'), ('tag', 'O'), ('save', '<i4')])}


print(structured_data)
savemat(filelocation, structured_data)




it_3_data = {


}