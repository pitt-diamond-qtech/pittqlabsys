# Created by Gurudev Dutt <gdutt@pitt.edu> on 2020-07-27
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

from src import ur


class ValidationError(Exception):
    """Exception raised when parameter validation fails."""
    pass


class Parameter(dict):
    def __init__(self, name, value=None, valid_values=None, info=None, visible=False, units=None,
                 min_value=None, max_value=None, pattern=None, validator=None):
        """
        Parameter class for managing experiment parameters with validation and units.

        Supported initialization patterns:
        - Parameter(name, value, valid_values, info, units)
        - Parameter({name: value})
        - Parameter([Parameter(...), Parameter(...)])

        Args:
            name: Parameter name (str) or dict/list for multiple parameters
            value: Parameter value (any type)
            valid_values: Type or list of valid values
            info: Description string
            visible: Boolean for GUI visibility
            units: Units string
            min_value: Minimum allowed value (for numeric parameters)
            max_value: Maximum allowed value (for numeric parameters)
            pattern: Regex pattern for string validation
            validator: Custom validation function
        """
        super().__init__()

        # Initialize caches for Phase 3 performance improvements
        self._conversion_cache = {}
        self._validation_cache = {}
        self._cache_max_size = 100

        if isinstance(name, str):
            self._init_single_parameter(name, value, valid_values, info, visible, units,
                                      min_value, max_value, pattern, validator)
        elif isinstance(name, (list, dict)):
            self._init_multiple_parameters(name, visible)
        else:
            raise TypeError(f"Invalid name type: {type(name)}")

    def _init_single_parameter(self, name, value, valid_values, info, visible, units,
                              min_value=None, max_value=None, pattern=None, validator=None):
        """Initialize a single parameter."""
        if valid_values is None:
            valid_values = type(value)

        assert isinstance(valid_values, (type, list))
        if info is None:
            info = ''
        assert isinstance(info, str)
        if units is None:
            units = ""
        assert isinstance(units, str)

        # Initialize validation rules for Phase 3
        self._validation_rules = {}
        if min_value is not None or max_value is not None:
            self._validation_rules[name] = {'range': {'min': min_value, 'max': max_value}}
        if pattern is not None:
            if name not in self._validation_rules:
                self._validation_rules[name] = {}
            self._validation_rules[name]['pattern'] = pattern
        if validator is not None:
            if name not in self._validation_rules:
                self._validation_rules[name] = {}
            self._validation_rules[name]['custom'] = validator

        # Validate value using enhanced validation
        self._validate_value(name, value, valid_values)

        # Handle nested Parameter objects in value
        if isinstance(value, list) and value and isinstance(value[0], Parameter):
            # Create nested Parameter structure
            nested_param = Parameter(value)
            self.name = name
            self._valid_values = {name: nested_param.valid_values}
            self._info = {name: nested_param.info}
            self._visible = {name: nested_param.visible}
            self._units = {name: nested_param.units}
            self.update({name: nested_param})
        else:
            self.name = name
            self._valid_values = {name: valid_values}
            self._info = {name: info}
            self._visible = {name: visible}
            self._units = {name: units}
            self.update({name: value})
            
            # Handle pint Quantity objects
            self._pint_quantity = {name: False}
            self._original_units = {name: None}
            self._original_magnitude = {name: None}
            
            if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                # Value is a pint Quantity
                self._pint_quantity[name] = True
                self._original_units[name] = value.units
                self._original_magnitude[name] = value.magnitude

    def _init_multiple_parameters(self, name, visible):
        """Initialize multiple parameters."""
        self.name = {}
        self._valid_values = {}
        self._info = {}
        self._visible = {}
        self._units = {}
        self._pint_quantity = {}
        self._original_units = {}
        self._original_magnitude = {}

        if isinstance(name, dict):
            for k, v in name.items():
                if isinstance(v, dict):
                    v = Parameter(v)
                self._add_parameter(k, v, visible)
        elif isinstance(name, list):
            for param in name:
                if isinstance(param, Parameter):
                    self._add_parameter_from_param(param)
                else:
                    raise TypeError(f"List must contain Parameter objects, got {type(param)}")

    def _add_parameter(self, name, value, visible):
        """Add a single parameter to the collection."""
        self.name[name] = name
        self._valid_values[name] = type(value)
        self._info[name] = ''
        self._visible[name] = visible
        self._units[name] = ''
        self.update({name: value})
        
        # Handle pint Quantity objects
        self._pint_quantity[name] = False
        self._original_units[name] = None
        self._original_magnitude[name] = None
        
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            # Value is a pint Quantity
            self._pint_quantity[name] = True
            self._original_units[name] = value.units
            self._original_magnitude[name] = value.magnitude

    def _add_parameter_from_param(self, param):
        """Add parameters from an existing Parameter object."""
        for k, v in param.items():
            self.name[k] = k
            self._valid_values[k] = param.valid_values[k]
            self._info[k] = param.info[k]
            self._visible[k] = param.visible[k]
            self._units[k] = param.units[k]
            self.update({k: v})
            
            # Handle pint Quantity objects from nested parameters
            if hasattr(param, '_pint_quantity') and k in param._pint_quantity:
                self._pint_quantity[k] = param._pint_quantity[k]
                self._original_units[k] = param._original_units.get(k)
                self._original_magnitude[k] = param._original_magnitude.get(k)
            else:
                self._pint_quantity[k] = False
                self._original_units[k] = None
                self._original_magnitude[k] = None

    def __setitem__(self, key, value):
        """
        Set item with validation for nested Parameter objects.
        
        Args:
            key: Dictionary key
            value: Dictionary value
        """
        # Use enhanced validation if available
        if hasattr(self, '_validation_rules') and key in self._validation_rules:
            self._validate_value(key, value, self.valid_values.get(key, type(value)))
        elif key in self.valid_values:
            message = f"{value} (of type {type(value)}) is not valid for {key}"
            assert self.is_valid(value, self.valid_values[key]), message

        # Handle nested Parameter objects
        if isinstance(value, dict) and key in self and isinstance(self[key], Parameter):
            # Update nested Parameter object
            self[key].update(value)
        else:
            super().__setitem__(key, value)

    def update(self, *args):
        """
        updates the values of the parameter, just as a regular dictionary
        """
        for d in args:
            for (key, value) in d.items():
                self.__setitem__(key, value)

    @property
    def visible(self):
        """

        Returns: if parameter should be shown (False) or hidden (True) in the GUI

        """
        return self._visible

    @property
    def valid_values(self):
        """
        Returns: valid value of the paramerer (a type like int, float or a list)
        """
        return self._valid_values

    @property
    def info(self):
        """

        Returns: a text describing the paramter

        """
        return self._info
    @property
    def units(self):
        """
        :return: the units of the parameter
        """
        return self._units

    @staticmethod
    def is_valid(value, valid_values):
        """
        check is the value is valid
        Args:
            value: value to be tested
            valid_values: allowed valid values (type or list of values)

        Returns:

        """

        valid = False

        if isinstance(valid_values, type) and type(value) is valid_values:
            valid = True
        elif isinstance(valid_values, type) and value is None:
            # Allow None values for any type (useful for optional parameters)
            valid = True
        elif isinstance(valid_values, type) and valid_values == float and type(value) == int:
            # special case to allow ints as float inputs
            valid = True
        elif isinstance(valid_values, type) and valid_values == float and hasattr(value, 'magnitude'):
            # special case to allow pint Quantity objects as float inputs
            valid = True
        elif isinstance(value, dict) and isinstance(valid_values, dict):
            # check that all values actually exist in valid_values
            # assert value.keys() & valid_values.keys() == value.keys() # python 3 syntax
            assert set(value.keys()) & set(valid_values.keys()) == set(value.keys())  # python 2
            # valid = True
            for k, v in value.items():
                valid = Parameter.is_valid(v, valid_values[k])
                if not valid:
                    break

        elif isinstance(value, dict) and valid_values == Parameter:
            valid = True

        elif isinstance(valid_values, list) and value in valid_values:
            valid = True

        return valid

    # Pint Integration Methods
    
    def is_pint_quantity(self, key=None):
        """
        Check if parameter value is a pint Quantity.
        
        Args:
            key: Parameter key (if None, checks first parameter)
            
        Returns:
            bool: True if parameter value is a pint Quantity
        """
        if key is None:
            # For single parameters, use the parameter name
            key = list(self.keys())[0] if self else None
            
        if key is None or key not in self._pint_quantity:
            return False
            
        return self._pint_quantity[key]
    
    def get_value_in_units(self, target_units, key=None):
        """
        Get parameter value converted to target units (with caching).
        
        Args:
            target_units: Target units (string or pint unit)
            key: Parameter key (if None, uses first parameter)
            
        Returns:
            pint.Quantity: Value in target units
        """
        if key is None:
            key = list(self.keys())[0] if self else None
            
        if key is None or not self.is_pint_quantity(key):
            return self[key]
        
        # Check cache first
        cache_key = f"{key}_{target_units}"
        if cache_key in self._conversion_cache:
            return self._conversion_cache[cache_key]
            
        from src import ur
        
        # Convert string to pint unit if needed
        if isinstance(target_units, str):
            try:
                target_units = getattr(ur, target_units)
            except AttributeError:
                raise ValueError(f"Unknown unit: {target_units}")
        
        # Perform conversion
        result = self[key].to(target_units)
        
        # Cache result
        if len(self._conversion_cache) >= self._cache_max_size:
            # Remove oldest entry (simple LRU)
            oldest_key = next(iter(self._conversion_cache))
            del self._conversion_cache[oldest_key]
        
        self._conversion_cache[cache_key] = result
        return result
    
    def set_value_with_units(self, value, units=None, key=None):
        """
        Set parameter value with units.
        
        Args:
            value: Parameter value
            units: Units (string or pint unit)
            key: Parameter key (if None, uses first parameter)
        """
        if key is None:
            key = list(self.keys())[0] if self else None
            
        if key is None:
            raise ValueError("No parameter key specified")
            
        from src import ur
        
        # Convert to pint Quantity if units provided
        if units is not None:
            if isinstance(units, str):
                units = getattr(ur, units)
            value = value * units
            
        self[key] = value
    
    def convert_units(self, target_units, key=None):
        """
        Convert parameter value to target units in place.
        
        Args:
            target_units: Target units (string or pint unit)
            key: Parameter key (if None, uses first parameter)
        """
        if key is None:
            key = list(self.keys())[0] if self else None
            
        if key is None or not self.is_pint_quantity(key):
            return
            
        converted_value = self.get_value_in_units(target_units, key)
        self[key] = converted_value
        
        # Update stored unit information
        self._original_units[key] = converted_value.units
        self._original_magnitude[key] = converted_value.magnitude
    
    def get_unit_info(self, key=None):
        """
        Get detailed unit information.
        
        Args:
            key: Parameter key (if None, uses first parameter)
            
        Returns:
            dict: Unit information including magnitude, units, etc.
        """
        if key is None:
            key = list(self.keys())[0] if self else None
            
        if key is None:
            return {}
            
        if not self.is_pint_quantity(key):
            return {
                'is_pint_quantity': False,
                'value': self[key],
                'units_string': self._units.get(key, '')
            }
            
        value = self[key]
        return {
            'is_pint_quantity': True,
            'magnitude': value.magnitude,
            'units': value.units,
            'units_string': str(value.units),
            'dimensionality': str(value.dimensionality),
            'value': value
        }
    
    def validate_units(self, unit1, unit2):
        """
        Validate that two units are compatible.
        
        Args:
            unit1: First unit (string or pint unit)
            unit2: Second unit (string or pint unit)
            
        Returns:
            bool: True if units are compatible
            
        Raises:
            ValueError: If units are incompatible
        """
        from src import ur
        
        # Convert strings to pint units if needed
        if isinstance(unit1, str):
            unit1 = getattr(ur, unit1)
        if isinstance(unit2, str):
            unit2 = getattr(ur, unit2)
            
        try:
            # Try to convert between units
            test_value = 1.0 * unit1
            converted = test_value.to(unit2)
            return True
        except Exception as e:
            raise ValueError(f"Units {unit1} and {unit2} are incompatible: {e}")
    
    def get_compatible_units(self, key=None):
        """
        Get list of compatible units for this parameter.
        
        Args:
            key: Parameter key (if None, uses first parameter)
            
        Returns:
            list: List of compatible unit strings
        """
        if key is None:
            key = list(self.keys())[0] if self else None
            
        if key is None or not self.is_pint_quantity(key):
            return []
            
        from src import ur
        
        # Get the base dimensionality
        value = self[key]
        dimensionality = value.dimensionality
        
        # Find all units with the same dimensionality
        compatible_units = []
        for unit_name in dir(ur):
            try:
                unit = getattr(ur, unit_name)
                if hasattr(unit, 'dimensionality') and unit.dimensionality == dimensionality:
                    compatible_units.append(unit_name)
            except:
                continue
        
        # Add common units for this dimensionality
        from src.core.unit_utils import get_common_units_for_dimensionality
        common_units = get_common_units_for_dimensionality(dimensionality)
        for unit in common_units:
            if unit not in compatible_units:
                compatible_units.append(unit)
                
        return compatible_units

    # Phase 3: Enhanced Validation and Caching Methods
    
    def _validate_value(self, key, value, valid_values):
        """
        Enhanced validation with multiple rule types.
        
        Args:
            key: Parameter key
            value: Value to validate
            valid_values: Type or list of valid values
            
        Raises:
            ValidationError: If validation fails
        """
        # Check cache first
        cache_key = f"{key}_{value}_{type(value)}"
        if cache_key in self._validation_cache:
            if not self._validation_cache[cache_key]:
                raise ValidationError(f"Value {value} failed cached validation for {key}")
            return
        
        # Perform validation
        is_valid = True
        error_messages = []
        
        # Get validation rules for this key
        rules = getattr(self, '_validation_rules', {}).get(key, {})
        
        # Range validation
        if 'range' in rules:
            range_rule = rules['range']
            if range_rule.get('min') is not None and value < range_rule['min']:
                is_valid = False
                error_messages.append(f"Value {value} is below minimum {range_rule['min']}")
            if range_rule.get('max') is not None and value > range_rule['max']:
                is_valid = False
                error_messages.append(f"Value {value} is above maximum {range_rule['max']}")
        
        # Pattern validation
        if 'pattern' in rules and isinstance(value, str):
            import re
            if not re.match(rules['pattern'], value):
                is_valid = False
                error_messages.append(f"Value '{value}' does not match pattern '{rules['pattern']}'")
        
        # Custom validation
        if 'custom' in rules:
            validator = rules['custom']
            if not validator(value):
                is_valid = False
                error_messages.append(f"Value {value} failed custom validation")
        
        # Existing type validation
        if not self.is_valid(value, valid_values):
            is_valid = False
            error_messages.append(f"Value {value} (of type {type(value)}) is not valid for {key}")
        
        # Cache result
        if len(self._validation_cache) >= self._cache_max_size:
            # Remove oldest entry (simple LRU)
            oldest_key = next(iter(self._validation_cache))
            del self._validation_cache[oldest_key]
        
        self._validation_cache[cache_key] = is_valid
        
        # Raise error if validation failed
        if not is_valid:
            raise ValidationError(f"Validation failed for {key}: {'; '.join(error_messages)}")
    
    def clear_cache(self):
        """Clear all caches."""
        self._conversion_cache.clear()
        self._validation_cache.clear()
    
    def get_cache_stats(self):
        """Get cache statistics for monitoring."""
        return {
            'conversion_cache_size': len(self._conversion_cache),
            'validation_cache_size': len(self._validation_cache),
            'max_cache_size': self._cache_max_size
        }
    
    def to_json(self):
        """
        Serialize Parameter to JSON with unit preservation.
        
        Returns:
            dict: JSON-serializable dictionary with unit information
        """
        import json
        
        data = {}
        
        for key, value in self.items():
            if isinstance(value, Parameter):
                # Handle nested Parameter objects
                data[key] = value.to_json()
            elif self.is_pint_quantity(key):
                data[key] = {
                    'value': value.magnitude,
                    'units': str(value.units),
                    'pint_quantity': True
                }
            else:
                data[key] = {
                    'value': value,
                    'units': self._units.get(key, ''),
                    'pint_quantity': False
                }
        
        # Add metadata
        data['_metadata'] = {
            'valid_values': self._valid_values,
            'info': self._info,
            'visible': self._visible,
            'validation_rules': getattr(self, '_validation_rules', {})
        }
        
        return data
    
    @classmethod
    def from_json(cls, json_data):
        """
        Create Parameter from JSON with unit restoration.
        
        Args:
            json_data: JSON data from to_json() method
            
        Returns:
            Parameter: Restored Parameter object
        """
        from src import ur
        
        # Extract metadata
        metadata = json_data.pop('_metadata', {})
        valid_values = metadata.get('valid_values', {})
        info = metadata.get('info', {})
        visible = metadata.get('visible', {})
        validation_rules = metadata.get('validation_rules', {})
        
        # Create parameter
        param = cls({})
        
        for key, value_data in json_data.items():
            if key == '_metadata':
                continue  # Skip metadata, handled separately
            elif isinstance(value_data, dict) and '_metadata' in value_data:
                # This is a nested Parameter object
                param[key] = Parameter.from_json(value_data)
                continue
            elif value_data.get('pint_quantity', False):
                # Restore pint Quantity
                magnitude = value_data['value']
                units_str = value_data['units']
                try:
                    units = getattr(ur, units_str)
                    value = magnitude * units
                    param._pint_quantity[key] = True
                except AttributeError:
                    # Fallback to string units if pint unit not found
                    value = magnitude
                    param._units[key] = units_str
                    param._pint_quantity[key] = False
            else:
                # Regular value
                value = value_data['value']
                param._pint_quantity[key] = False
                # Restore string units if present
                if 'units' in value_data and value_data['units']:
                    param._units[key] = value_data['units']
            
            param[key] = value
        
        # Restore metadata
        param._valid_values = valid_values
        param._info = info
        param._visible = visible
        param._validation_rules = validation_rules
        
        return param
    


if __name__ == '__main__':
    # Parameter is working with units.
    p = Parameter([
        Parameter('x', 1,units='m'),
        Parameter('filter wheel', [
            Parameter('channel', 1, int, 'channel to which motor is connected'),
            Parameter('settle_time', 0.8, float, 'settling time',units='s'),
            Parameter('ND2.0', 4 * 2700, int, 'position corresponding to position 1'),
            Parameter('ND1.0', 4 * 1700, int, 'position corresponding to position 2'),
            Parameter('Red', 4 * 750, int, 'position corresponding to position 3'),
            Parameter('current_position', 'ND1.0', ['ND1.0', 'ND2.0', 'Red'], 'current position of filter wheel')
        ])
    ])

    print((p['filter wheel'], type(p['filter wheel'])))
    print('======')
    print((p.valid_values['filter wheel']))
    print("Units for {} are {}".format(p.name['filter wheel'], p.units['filter wheel']))
    print('======')
    print((p['x'], type(p['x'])))
    print((p.valid_values['x']))
    print("Units for {} are {}".format(p.name['x'],p.units['x']))