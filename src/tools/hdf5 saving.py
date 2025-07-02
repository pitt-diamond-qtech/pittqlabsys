import h5py
import numpy as np
from src.core.helper_functions import structure_data_for_hdf5


def guess_numpy_dtype(value):
    if isinstance(value, float) or isinstance(value, list):
        return 'f8'
    elif isinstance(value, bool): #need to put bool before int as True/False are technically 1/0
        return 'bool'
    elif isinstance(value, int):
        return 'i4'
    elif isinstance(value, str):
        return 'S{}'.format(len(value) + 1)  # +1 so empty string (S0) dont casue an error
    elif isinstance(value, np.ndarray):
        return value.dtype
    elif isinstance(value, dict):
        print('dictionary detected')
        return 'O'
    else:
        raise ValueError('hdf5 unsupported data type')


def get_shape(value):
    if isinstance(value, np.ndarray):
        return value.shape
    elif isinstance(value, (list, tuple)):
        try:
            return np.array(value).shape
        except:
            return ()  # fallback if conversion fails
    else:
        return ()  # scalar or unknown type

name = 'random.hdf5'
file = r'D:\Data\dylan_staples\hdf5_save_testing\\'

rand_1 = np.random.random((16,))
img_1 = rand_1.reshape((4,4))
rand_2 = np.random.random((16,))
img_2 = rand_1.reshape((4,4))
rand_3 = np.random.random((64,))
img_3 = rand_1.reshape((8,8))
rand_4 = np.random.random((64,))
img_4 = rand_1.reshape((8,8))

ex_data_1 = {'random_data':list(rand_1),'image_data': img_1}
ex_settings_1 = {'count': 16, 'name': 'this is a counter', 'wait_time': 0.1, 'point':{'x':1,'y':2}, 'plot_style': '2D', 'path': '', 'tag': 'exampleexperiment_1', 'save': False}

ex_data_2 = {'random_data': list(rand_2),'image_data': img_2}
ex_settings_2 = {'count': 16, 'name': 'this is a counter', 'wait_time': 0.1, 'point':{'x':1,'y':2}, 'plot_style': '2D', 'path': '', 'tag': 'exampleexperiment_2', 'save': False}

ex_data_3 = {'random_data': list(rand_3),'image_data': img_3}
ex_settings_3 = {'count': 64, 'name': 'this is a counter', 'wait_time': 0.1, 'point':{'x':1,'y':2}, 'plot_style': '2D', 'path': '', 'tag': 'exampleexperiment_3', 'save': False}

ex_data_4 = {'random_data': list(rand_4),'image_data': img_4}
ex_settings_4 = {'count': 64, 'name': 'this is a counter', 'wait_time': 0.1, 'point':{'x':1,'y':2}, 'plot_style': '2D', 'path': '', 'tag': 'exampleexperiment_4', 'save': False}

#general way to save data from a dictionary
'''with h5py.File(file+name, 'w') as f:
    ex_1 = f.create_group('example_experiment_1')

    for key, value in ex_data_1.items():
        value_type = guess_numpy_dtype(value)
        value_shape = get_shape(value)
        dset = ex_1.create_dataset(key, shape=value_shape, dtype=value_type, data=value)
        if value_type == 'bool':
            dset.attrs['description'] = "0 = False, 1 = True"
    for key, value in ex_settings_1.items():
        value_type = guess_numpy_dtype(value)
        value_shape = get_shape(value)
        dset = ex_1.create_dataset(key, shape=value_shape, dtype=value_type, data=value)
        if value_type == 'bool':
            dset.attrs['description'] = "0 = False, 1 = True"'''

#saving with function 1 iterator deep
data_1_layer = [ex_data_1, ex_data_2]
settings_1_layer = [ex_settings_1, ex_settings_2]

structure_data_for_hdf5(filename=file+'func_test.hdf5',data=data_1_layer, settings=settings_1_layer)

data_2_layer = [[ex_data_1, ex_data_2],[ex_data_3, ex_data_4]]
settings_2_layer = [[ex_settings_1, ex_settings_2],[ex_settings_3, ex_settings_4]]


