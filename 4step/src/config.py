"""Configuration loader for area-specific settings."""

import yaml
from pathlib import Path


class AreaConfig:
    """Load and manage area-specific configuration from settings files."""

    def __init__(self, settings_path=None, unit_conversions_path=None, **kwargs):
        """
        Initialize configuration from settings files.

        Parameters:
        -----------
        settings_path : Path or str, optional
            Path to the area settings YAML file. If None, uses brooklyn_settings.yaml.
        unit_conversions_path : Path or str, optional
            Path to the unit conversions YAML file. If None, uses unit_conversions.yaml.
        **kwargs
            Ignored, for backward compatibility (e.g., city_name).
        """
        # Accept but ignore old parameters like city_name for backward compatibility
        module_dir = Path(__file__).parent
        settings_dir = module_dir.parent / 'settings'

        if settings_path is None:
            settings_path = settings_dir / 'brooklyn_settings.yaml'
        if unit_conversions_path is None:
            unit_conversions_path = settings_dir / 'unit_conversions.yaml'

        self.settings_path = Path(settings_path)
        self.unit_conversions_path = Path(unit_conversions_path)
        self._load_settings()
        self._load_unit_conversions()

    def _load_settings(self):
        """Load area settings from YAML file."""
        if not self.settings_path.exists():
            raise FileNotFoundError(f"Settings file not found: {self.settings_path}")

        with open(self.settings_path, 'r') as f:
            self.settings = yaml.safe_load(f)

    def _load_unit_conversions(self):
        """Load unit conversions from YAML file."""
        if not self.unit_conversions_path.exists():
            raise FileNotFoundError(f"Unit conversions file not found: {self.unit_conversions_path}")

        with open(self.unit_conversions_path, 'r') as f:
            self.unit_conversions = yaml.safe_load(f)

    # -------------------------------------------------------------------------
    # Unit Conversions (from unit_conversions.yaml - never changes)
    # -------------------------------------------------------------------------
    @property
    def m2_to_sqft(self):
        """Get square meters to square feet conversion factor."""
        return self.unit_conversions['unit_conversions']['m2_to_sqft']

    @property
    def sqft_to_m2(self):
        """Get square feet to square meters conversion factor."""
        return self.unit_conversions['unit_conversions']['sqft_to_m2']

    @property
    def sqft_to_acres(self):
        """Get square feet to acres conversion factor."""
        return self.unit_conversions['unit_conversions']['sqft_to_acres']

    @property
    def acres_to_sqft(self):
        """Get acres to square feet conversion factor."""
        return self.unit_conversions['unit_conversions']['acres_to_sqft']

    @property
    def m_to_ft(self):
        """Get meters to feet conversion factor."""
        return self.unit_conversions['unit_conversions']['m_to_ft']

    @property
    def ft_to_m(self):
        """Get feet to meters conversion factor."""
        return self.unit_conversions['unit_conversions']['ft_to_m']

    # -------------------------------------------------------------------------
    # Building Defaults
    # -------------------------------------------------------------------------
    @property
    def default_floors(self):
        """Get default number of floors for buildings."""
        return self.settings['building_defaults']['default_floors']

    @property
    def avg_floor_height_m(self):
        """Get average floor height in meters."""
        return self.settings['building_defaults']['avg_floor_height_m']

    # -------------------------------------------------------------------------
    # Trip Generation Conversions
    # -------------------------------------------------------------------------
    @property
    def sqft_per_du(self):
        """Get average square feet per dwelling unit."""
        return self.settings['trip_gen_conversions']['residential']['sqft_per_du']

    @property
    def sqft_per_hotel_room(self):
        """Get average square feet per hotel room."""
        return self.settings['trip_gen_conversions']['hotel']['sqft_per_room']

    @property
    def sqft_per_student(self):
        """Get average square feet per student."""
        return self.settings['trip_gen_conversions']['school']['sqft_per_student']

    @property
    def sqft_per_cinema_seat(self):
        """Get average square feet per cinema seat."""
        return self.settings['trip_gen_conversions']['cinema']['sqft_per_seat']

    @property
    def residential_floors_threshold(self):
        """Get threshold for high-rise residential category."""
        return self.settings['residential_categories']['floors_threshold']

    # -------------------------------------------------------------------------
    # POI Mapping
    # -------------------------------------------------------------------------
    @property
    def trip_gen_land_use_map(self):
        """Get POI type to trip generation category mapping."""
        return self.settings['trip_gen_land_use_map']

    @property
    def default_trip_gen_category(self):
        """Get default trip generation category for unmapped POI types."""
        return self.settings['default_trip_gen_category']

    @property
    def trip_gen_units(self):
        """Get trip generation units by category."""
        return self.settings['trip_gen_units']

    # -------------------------------------------------------------------------
    # POI Heuristics
    # -------------------------------------------------------------------------
    @property
    def poi_heuristics(self):
        """Get POI space allocation heuristics."""
        return self.settings['poi_heuristics']

    @property
    def building_type_map(self):
        """Get building tag to POI type mapping."""
        return self.settings['building_type_map']

    @property
    def poi_filters(self):
        """Get POI filtering rules."""
        return self.settings['poi_filters']

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def get_trip_gen_residential_category(self, floors):
        """
        Get the appropriate residential trip generation category based on floors.

        Parameters:
        -----------
        floors : int
            Number of floors in the building

        Returns:
        --------
        str
            Trip generation category name
        """
        categories = self.settings['residential_categories']['categories']
        if floors >= self.residential_floors_threshold:
            return categories['high_rise']
        else:
            return categories['low_rise']


# Backward compatibility aliases
CityConfig = AreaConfig


def get_area_config(settings_path=None):
    """
    Get configuration from a settings file.

    Parameters:
    -----------
    settings_path : Path or str, optional
        Path to the settings YAML file. If None, uses brooklyn_settings.yaml.

    Returns:
    --------
    AreaConfig
        Configuration object
    """
    return AreaConfig(settings_path)


# Backward compatibility alias
def get_city_config(city_name='brooklyn'):
    """
    Backward compatibility wrapper. Use get_area_config() instead.

    Parameters:
    -----------
    city_name : str
        Ignored, kept for backward compatibility.

    Returns:
    --------
    AreaConfig
        Configuration object for Brooklyn
    """
    return AreaConfig()
