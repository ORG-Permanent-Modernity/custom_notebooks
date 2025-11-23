"""Configuration loader for city-specific parameters."""

import yaml
from pathlib import Path


class CityConfig:
    """Load and manage city-specific configuration parameters."""

    def __init__(self, city_name='brooklyn', config_path=None):
        """
        Initialize configuration for a specific city.

        Parameters:
        -----------
        city_name : str
            Name of the city (must match a key in the config file)
        config_path : Path or str, optional
            Path to the config file. If None, uses default location.
        """
        if config_path is None:
            # Try to find the config file relative to this module
            module_dir = Path(__file__).parent
            config_path = module_dir.parent / 'settings' / 'city_config.yaml'

        self.config_path = Path(config_path)
        self.city_name = city_name.lower()
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            full_config = yaml.safe_load(f)

        if self.city_name not in full_config['cities']:
            available = list(full_config['cities'].keys())
            raise ValueError(f"City '{self.city_name}' not found in config. Available: {available}")

        self.config = full_config['cities'][self.city_name]

    @property
    def default_floors(self):
        """Get default number of floors for buildings."""
        return self.config['building']['default_floors']

    @property
    def avg_floor_height_m(self):
        """Get average floor height in meters."""
        return self.config['building']['avg_floor_height_m']

    @property
    def m2_to_sqft(self):
        """Get square meters to square feet conversion factor."""
        return self.config['building']['m2_to_sqft']

    @property
    def sqft_per_du(self):
        """Get average square feet per dwelling unit."""
        return self.config['residential']['sqft_per_du']

    @property
    def residential_floors_threshold(self):
        """Get threshold for high-rise residential category."""
        return self.config['residential']['floors_threshold']

    @property
    def sqft_per_hotel_room(self):
        """Get average square feet per hotel room."""
        return self.config['commercial']['sqft_per_hotel_room']

    @property
    def sqft_per_student(self):
        """Get average square feet per student."""
        return self.config['commercial']['sqft_per_student']

    @property
    def sqft_per_cinema_seat(self):
        """Get average square feet per cinema seat."""
        return self.config['commercial']['sqft_per_cinema_seat']

    @property
    def sqft_to_acres(self):
        """Get square feet to acres conversion factor."""
        return self.config['land']['sqft_to_acres']

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
        if floors >= self.residential_floors_threshold:
            return 'Residential (3 or more floors)'
        else:
            return 'Residential (2 floors or less)'


# Convenience function to get config for a city
def get_city_config(city_name='brooklyn'):
    """
    Get configuration for a specific city.

    Parameters:
    -----------
    city_name : str
        Name of the city

    Returns:
    --------
    CityConfig
        Configuration object for the city
    """
    return CityConfig(city_name)