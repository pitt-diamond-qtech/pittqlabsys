"""
MATLAB-style struct / struct-array save & load using HDF5 (+ SWMR-ready).
"""

import numpy as np
import h5py
from typing import Any
from src import ur  # pint unit registry
import datetime
from src.core import Parameter

# ============================================================
# Core data containers
# ============================================================

class MyStruct:
    """
    MATLAB-like struct:
    - arbitrary attributes
    - attribute access (obj.field)
    - dict-like access (obj['field'])
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        items = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"MyStruct({items})"


class StructArray:
    """
    MATLAB-like struct array:
    obj[0].field = value
    obj[10].other = value   # auto-expands
    """

    def __init__(self):
        self._items = []

    def __getitem__(self, index):
        while len(self._items) <= index:
            self._items.append(MyStruct())
        return self._items[index]

    def __repr__(self):
        return f"StructArray({self._items})"


# ============================================================
# Public API
# ============================================================
def save_data(filename, obj, mode="w", swmr=True):
    with h5py.File(filename, mode, libver="latest") as f:
        if isinstance(obj, StructArray):
            _write_structarray(f, obj)
        else:
            print(f"obj{obj}")
            _write_mystruct(f, obj)

        if swmr and mode in ("w", "r+"):
            f.swmr_mode = True
            f.flush()


def load_data(filename):
    with h5py.File(filename, "r", libver="latest", swmr=True) as f:
        obj = MyStruct()
        _read_mystruct(f, obj)
        return obj

# ============================================================
# Internal: write helpers
# ============================================================

def _write_structarray(h5group, struct_array):
    for i, item in enumerate(struct_array._items):
        grp = h5group.require_group(str(i))
        _write_mystruct(grp, item)


def _write_mystruct(h5group, mystruct):
    for key, value in mystruct.__dict__.items():
        _write_value(h5group, key, value)


def _write_value(h5group, name, value):
    # Nested struct
    if isinstance(value, MyStruct):
        grp = h5group.require_group(name)
        _write_mystruct(grp, value)

    # Nested struct array
    elif isinstance(value, StructArray):
        grp = h5group.require_group(name)
        _write_structarray(grp, value)

    # Scalars & strings → attributes
    elif np.isscalar(value) or isinstance(value, str):
        h5group.attrs[name] = value

    elif isinstance(value, dict):
        grp = h5group.require_group(name)
        for k, v in value.items():
            _write_value(grp, k, v)

    elif isinstance(value, datetime.datetime):
        h5group.attrs[name] = value.timestamp()

    # Everything else → dataset
    else:
        try:
            arr = np.asarray(value)
            if name in h5group:
                del h5group[name]
            h5group.create_dataset(
            name,
            data=arr,
            chunks=True)
        except Exception:
            h5group.attrs[name] = str(value)
            """print(f"Failed to create {name}")
            raise Exception"""


# ============================================================
# Internal: read helpers
# ============================================================

def _read_structarray(h5group):
    sa = StructArray()

    for key in sorted(h5group.keys(), key=int):
        item = MyStruct()
        _read_mystruct(h5group[key], item)
        sa._items.append(item)

    return sa


def _read_mystruct(h5group, mystruct):
    # Attributes → scalars
    for k, v in h5group.attrs.items():
        mystruct.__dict__[k] = v

    # Datasets / subgroups
    for name, obj in h5group.items():
        if isinstance(obj, h5py.Dataset):
            mystruct.__dict__[name] = obj[()]

        elif isinstance(obj, h5py.Group):
            # Numeric group names → StructArray
            if obj.keys() and all(k.isdigit() for k in obj.keys()):
                mystruct.__dict__[name] = _read_structarray(obj)
            else:
                sub = MyStruct()
                _read_mystruct(obj, sub)
                mystruct.__dict__[name] = sub

def is_image_array(arr: np.ndarray) -> bool:
    if not isinstance(arr, np.ndarray):
        return False
    if arr.dtype != np.uint8:
        return False
    if arr.ndim == 2:
        return True              # grayscale
    if arr.ndim == 3 and arr.shape[2] in (3, 4):
        return True              # RGB / RGBA
    return False
def iter_struct(obj, prefix=""):
    """
    Yields (path, value)
    Example path: FINAL/top_left/camera_image
    """
    if isinstance(obj, MyStruct):
        for k, v in obj.__dict__.items():
            new_prefix = f"{prefix}/{k}" if prefix else k
            yield from iter_struct(v, new_prefix)

    elif isinstance(obj, StructArray):
        for i, item in enumerate(obj._items):
            new_prefix = f"{prefix}/{i}"
            yield from iter_struct(item, new_prefix)

    else:
        yield prefix, obj

def is_scalar_or_small(value, max_elements=100):

    # NumPy scalar (np.int64, np.float32, etc.)
    if isinstance(value, np.generic):
        return True

    # Python scalar
    if isinstance(value, (int, float, bool, str)):
        return True

    # Small numpy arrays
    if isinstance(value, np.ndarray):
        return value.size <= max_elements

    return False

def normalize_value(value):
    import numpy as np
    if isinstance(value, np.generic):
        return value.item()
    return value

def parameter_to_mystruct(obj):
    """
    Convert Parameter / dict / scalar into MyStruct recursively.
    """
    # Case 1: full Parameter object
    if isinstance(obj, Parameter):
        ms = MyStruct()

        for key in obj.keys():
            value = obj[key]

            # Nested Parameter
            if isinstance(value, Parameter):
                setattr(ms, key, parameter_to_mystruct(value))
                continue

            # Pint quantity
            if obj.is_pint_quantity(key):
                q = value
                setattr(
                    ms,
                    key,
                    MyStruct(value=q.magnitude, units=str(q.units))
                )
                continue

            # Plain value
            setattr(ms, key, normalize_value(value))

        # Attach metadata once per Parameter
        ms._parameter_metadata = MyStruct(
            info=dict_to_mystruct(obj.info),
            units=dict_to_mystruct(obj.units),
            visible=dict_to_mystruct(obj.visible),
            valid_values=str(obj.valid_values),
        )

        return ms

    # Case 2: dict-like (already unwrapped Parameter)
    elif isinstance(obj, dict):
        ms = MyStruct()
        for k, v in obj.items():
            setattr(ms, k, parameter_to_mystruct(v))
        return ms

    # Case 3: scalar / array
    else:
        return normalize_value(obj)


def dict_to_mystruct(d):
    ms = MyStruct()
    for k, v in d.items():
        if isinstance(v, dict):
            setattr(ms, k, dict_to_mystruct(v))
        else:
            setattr(ms, k, normalize_value(v))
    return ms

def save_parameters_hdf5(
    filename,
    parameters,
    root_name="parameters",
    mode="w",
    swmr=True
):
    root = MyStruct()
    setattr(root, root_name, parameter_to_mystruct(parameters))
    save_data(filename, root, mode=mode, swmr=swmr)



# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    obj = StructArray()
    obj[0].name = "first"
    obj[0].color = "blue"
    obj[0].matrix = [
        [1, 2, 3],
        [4, 5, 6],
    ]

    obj[1].vector = [1.0, 2.0, 3.0]
    obj[1].matrix = np.eye(2)

    save_data("example.h5", obj)
    loaded = load_data("example.h5")

    print(loaded)
    print(loaded[1].matrix)
    # PARAM HELPERS EXAMPLE USAGE
    """Save spectrum analyzer defaults
    save_parameters_hdf5(
        "agilent8596e_params.h5",
        _DEFAULT_SETTINGS,
        root_name="agilent8596e"
    )
    Save pulsed ODMR experiment parameters
    save_parameters_hdf5(
        "odmr_pulsed_params.h5",
        _DEFAULT_SETTINGS,
        root_name="odmr_pulsed"
    )
    Save multiple parameter sets at once
    save_parameters_hdf5(
        "experiment_params.h5",
        {
            "spectrum_analyzer": sa_params,
            "odmr": odmr_params,
        }
    )"""





