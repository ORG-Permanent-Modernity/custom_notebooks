import osmnx as ox
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
import numpy as np
import logging
import os
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import rasterio
from rasterio.transform import from_origin
from scipy.stats import gaussian_kde
import folium
from folium.plugins import MarkerCluster


class OSMDataService:
    """
    Service class for handling all OpenStreetMap data fetching and processing.
    Centralizes query logic, error handling, and data post-processing.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the OSM data service.

        Parameters:
        -----------
        logger : logging.Logger, optional
            Logger for outputting status messages. If None, a new logger will be created.
        """
        self.logger = logger or logging.getLogger("OSMDataService")
    
    def fetch_osm_data(self, area_or_polygon, feature_type, tags, 
                       progress_callback=None, convert_polygons_to_points=False,
                       auto_tiled=True, grid_size=3):
        """
        Unified method for fetching OSM data that handles both place names and polygons.
        
        Parameters:
        -----------
        area_or_polygon : str or shapely.geometry
            Either a place name (string) or a polygon geometry
        feature_type : str
            The OSM feature type (e.g., 'amenity', 'shop', 'highway')
        tags : list
            List of specific tags to fetch for the feature type
        progress_callback : callable, optional
            Function to call with progress updates
        convert_polygons_to_points : bool, default=False
            If True, converts polygon geometries to their centroids
        auto_tiled : bool, default=True
            If True, automatically switches to tiled approach if the initial query fails
        grid_size : int, default=3
            Number of grid cells to use in each dimension for tiled queries
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            GeoDataFrame containing the requested data, or None if no data found
        """
        self._log_progress("Fetching {} data with {} tags...", 
                          feature_type, len(tags), progress_callback)
        
        # Create a tags dictionary for OSMnx
        tags_dict = {feature_type: tags}
        
        try:
            # Determine if we're using a place name or a polygon
            if isinstance(area_or_polygon, str):
                # It's a place name
                self._log_progress("Using place name: {}", area_or_polygon, progress_callback)
                gdf = ox.features_from_place(area_or_polygon, tags=tags_dict)
            else:
                # It's a polygon
                self._log_progress("Using polygon geometry", None, progress_callback)
                gdf = ox.features_from_polygon(area_or_polygon, tags=tags_dict)

            # Process the results
            return self._process_results(gdf, feature_type, convert_polygons_to_points, progress_callback)
            
        except Exception as e:
            # Handle query errors
            if auto_tiled and ("too long" in str(e).lower() or "bad request" in str(e).lower()):
                self._log_progress("Query too large, switching to tiled approach...", 
                                  None, progress_callback)
                return self.fetch_data_by_tiles(
                    area_or_polygon, feature_type, tags, 
                    progress_callback, convert_polygons_to_points, grid_size
                )
            else:
                self._log_progress("Error fetching data: {}", str(e), progress_callback, is_error=True)
                raise e

    def fetch_data_by_tiles(self, area_or_polygon, feature_type, tags, 
                           progress_callback=None, convert_polygons_to_points=False, 
                           grid_size=3, recursive=True):
        """
        Fetch data by dividing the area into a grid of smaller tiles for large areas.
        
        Parameters:
        -----------
        area_or_polygon : str or shapely.geometry
            Either a place name (string) or a polygon geometry
        feature_type : str
            The OSM feature type (e.g., 'amenity', 'shop', 'highway')
        tags : list
            List of specific tags to fetch for the feature type
        progress_callback : callable, optional
            Function to call with progress updates
        convert_polygons_to_points : bool, default=False
            If True, converts polygon geometries to their centroids
        grid_size : int, default=3
            Number of grid cells to use in each dimension
        recursive : bool, default=True
            If True, recursively subdivides tiles that are still too large
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            Combined GeoDataFrame from all tiles, or None if no data found
        """
        self._log_progress("Dividing area into {}x{} grid...", 
                          grid_size, grid_size, progress_callback)
        
        # Handle both place names and polygons
        boundary = self._get_boundary(area_or_polygon)
        if boundary is None:
            return None
        
        # Get the bounds
        minx, miny, maxx, maxy = boundary.bounds
        
        # Calculate the size of each grid cell
        cell_width = (maxx - minx) / grid_size
        cell_height = (maxy - miny) / grid_size
        
        # Create a list to store all the GeoDataFrames
        all_gdfs = []
        
        # Create a tags dictionary for OSMnx
        tags_dict = {feature_type: tags}
        
        # Total number of cells to process
        total_cells = grid_size * grid_size
        cells_processed = 0
        
        # Loop through the grid
        for i in range(grid_size):
            for j in range(grid_size):
                cells_processed += 1
                
                # Calculate the bounds of this cell
                cell_minx = minx + i * cell_width
                cell_maxx = minx + (i + 1) * cell_width
                cell_miny = miny + j * cell_height
                cell_maxy = miny + (j + 1) * cell_height
                
                # Create a polygon for this cell
                cell = box(cell_minx, cell_miny, cell_maxx, cell_maxy)
                
                # Skip if the cell doesn't intersect with the boundary
                if not cell.intersects(boundary):
                    continue
                
                self._log_progress("Fetching grid cell {}/{} ...", 
                                  cells_processed, total_cells, progress_callback)
                
                try:
                    # Get the data for this cell using polygon argument
                    gdf = ox.features_from_polygon(cell, tags=tags_dict)
                    
                    if gdf is not None and len(gdf) > 0:
                        all_gdfs.append(gdf)
                        self._log_progress("  ✓ Found {} features in this cell", 
                                          len(gdf), None, progress_callback)
                
                except Exception as e:
                    self._log_progress("  ✗ Error fetching cell: {}", 
                                      str(e), progress_callback, is_error=True)
                    
                    # If we still get an error and recursive is True, try with smaller cells
                    if recursive and ("too long" in str(e).lower() or "bad request" in str(e).lower()):
                        self._log_progress("  Trying with smaller subdivisions...", 
                                          None, None, progress_callback)
                        
                        # Process subcells recursively
                        subcell_gdf = self._process_subcells(
                            cell_minx, cell_miny, cell_maxx, cell_maxy, 
                            feature_type, tags, progress_callback
                        )
                        
                        if subcell_gdf is not None and len(subcell_gdf) > 0:
                            all_gdfs.append(subcell_gdf)
        
        # Combine all the GeoDataFrames
        if all_gdfs:
            combined_gdf = pd.concat(all_gdfs, ignore_index=True)
            
            # Remove duplicate geometries
            combined_gdf = self._remove_duplicates(combined_gdf)
            
            self._log_progress("Total features after grid processing: {}", 
                              len(combined_gdf), progress_callback)
            
            # Process the results
            return self._process_results(
                combined_gdf, feature_type, convert_polygons_to_points, progress_callback
            )
        else:
            self._log_progress("No features found in any grid cells", 
                              None, progress_callback)
            return None

    def _process_subcells(self, cell_minx, cell_miny, cell_maxx, cell_maxy, 
                         feature_type, tags, progress_callback=None, subcell_size=2):
        """
        Process subcells when a tile is still too large.
        
        Parameters:
        -----------
        cell_minx, cell_miny, cell_maxx, cell_maxy : float
            Boundaries of the cell to subdivide
        feature_type : str
            The OSM feature type
        tags : list
            List of specific tags to fetch
        progress_callback : callable, optional
            Function to call with progress updates
        subcell_size : int, default=2
            Number of subcells in each dimension
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame or None
            Combined GeoDataFrame from all subcells, or None if no data found
        """
        subcell_gdfs = []
        subcell_width = (cell_maxx - cell_minx) / subcell_size
        subcell_height = (cell_maxy - cell_miny) / subcell_size
        
        tags_dict = {feature_type: tags}
        
        for si in range(subcell_size):
            for sj in range(subcell_size):
                subcell_minx = cell_minx + si * subcell_width
                subcell_maxx = cell_minx + (si + 1) * subcell_width
                subcell_miny = cell_miny + sj * subcell_height
                subcell_maxy = cell_miny + (sj + 1) * subcell_height
                
                subcell = box(subcell_minx, subcell_miny, subcell_maxx, subcell_maxy)
                
                try:
                    sub_gdf = ox.features_from_polygon(subcell, tags=tags_dict)
                    if sub_gdf is not None and len(sub_gdf) > 0:
                        subcell_gdfs.append(sub_gdf)
                        self._log_progress("    ✓ Subdivision {}/{}: Found {} features", 
                                          si*subcell_size+sj+1, subcell_size*subcell_size, 
                                          len(sub_gdf), progress_callback)
                except Exception as sub_e:
                    self._log_progress("    ✗ Error in subdivision: {}", 
                                      str(sub_e), progress_callback, is_error=True)
        
        # Combine all subcell GeoDataFrames
        if subcell_gdfs:
            return pd.concat(subcell_gdfs, ignore_index=True)
        else:
            return None

    def clean_data(self, gdf, feature_type=None, filter_types=None):
        """
        Clean and standardize the data.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The data to clean
        feature_type : str, optional
            The feature type, used for type-specific cleaning
        filter_types : list, optional
            List of unwanted types to filter out
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            The cleaned data
        """
        if gdf is None or len(gdf) == 0:
            return gdf
        
        # Make a copy to avoid modifying the original
        cleaned_gdf = gdf.copy()
        
        # Define unwanted feature types if not provided
        if filter_types is None and feature_type in ['amenity', 'shop']:
            filter_types = [
                'bench', 'atm', 'drinking_water', 'toilets', 'waste_basket', 
                'vending_machine', 'fountain', 'training', 'waste_disposal', 
                'recycling', 'payment_terminal', 'yes', 'driving_school', 
                'public_bookcase'
            ]
        
        # Apply the filter if we have unwanted types
        if filter_types is not None and feature_type is not None:
            type_column = feature_type  # The column name is usually the feature type
            if type_column in cleaned_gdf.columns:
                before_len = len(cleaned_gdf)
                cleaned_gdf = cleaned_gdf[~cleaned_gdf[type_column].isin(filter_types)]
                self.logger.info(f"Removed {before_len - len(cleaned_gdf)} unwanted {feature_type} types")
        
        # Remove entries containing 'was:' (historical features)
        if feature_type is not None:
            type_column = feature_type
            if type_column in cleaned_gdf.columns:
                before_len = len(cleaned_gdf)
                cleaned_gdf = cleaned_gdf[~cleaned_gdf[type_column].astype(str).str.contains('was:')]
                self.logger.info(f"Removed {before_len - len(cleaned_gdf)} historical entries")
        
        # Remove duplicate geometries
        cleaned_gdf = self._remove_duplicates(cleaned_gdf)
        
        return cleaned_gdf

    def _remove_duplicates(self, gdf):
        """
        Remove duplicate geometries from a GeoDataFrame.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The data to process
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            The de-duplicated data
        """
        if gdf is None or len(gdf) == 0:
            return gdf
            
        # Make a copy to avoid modifying the original
        unique_gdf = gdf.copy()
        
        # Create a string representation of geometries for comparison
        before_len = len(unique_gdf)
        unique_gdf['geom_str'] = unique_gdf.geometry.apply(lambda x: str(x))
        unique_gdf = unique_gdf.drop_duplicates(subset=['geom_str'])
        unique_gdf = unique_gdf.drop(columns=['geom_str'])
        
        self.logger.info(f"Removed {before_len - len(unique_gdf)} duplicate geometries")
        
        return unique_gdf

    def convert_polygons_to_points(self, gdf, feature_type=None):
        """
        Convert polygon geometries to point geometries (centroids).
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The data to process
        feature_type : str, optional
            The feature type, for logging purposes
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            The processed data with polygon geometries converted to points
        """
        if gdf is None or len(gdf) == 0:
            return gdf
            
        # Make a copy to avoid modifying the original
        converted_gdf = gdf.copy()
        
        # Identify polygons and multipolygons
        polygon_mask = converted_gdf.geometry.apply(
            lambda geom: geom is not None and 
            (geom.geom_type == 'Polygon' or geom.geom_type == 'MultiPolygon')
        )
        
        # Convert polygons to centroid points
        if polygon_mask.any():
            num_polygons = polygon_mask.sum()
            converted_gdf.loc[polygon_mask, 'geometry'] = converted_gdf.loc[polygon_mask, 'geometry'].centroid
            
            type_info = f" for {feature_type} features" if feature_type else ""
            self.logger.info(f"Converted {num_polygons} polygons to points{type_info}")
        
        return converted_gdf

    def standardize_columns(self, gdf, feature_type):
        """
        Standardize columns for a feature type, ensuring consistent column names.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The data to process
        feature_type : str
            The feature type (e.g., 'amenity', 'shop')
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            The data with standardized columns
        """
        if gdf is None or len(gdf) == 0:
            return gdf
            
        # Make a copy to avoid modifying the original
        std_gdf = gdf.copy()
        
        # Ensure 'name' column exists
        if 'name' not in std_gdf.columns:
            if 'name:en' in std_gdf.columns:
                std_gdf['name'] = std_gdf['name:en']
            else:
                std_gdf['name'] = None
        
        # Fill missing names with generic names if needed
        if 'name' in std_gdf.columns:
            nan_mask = std_gdf['name'].isna()
            if nan_mask.any():
                # Create list of unnamed identifiers
                unnamed_items = [f"unnamed_{feature_type}_{i}" for i in range(sum(nan_mask))]
                # Assign to NaN locations
                std_gdf.loc[nan_mask, 'name'] = unnamed_items
        
        return std_gdf

    def _process_results(self, gdf, feature_type, convert_polygons_to_points, progress_callback):
        """
        Process the results of a data fetch operation.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The data to process
        feature_type : str
            The feature type
        convert_polygons_to_points : bool
            Whether to convert polygons to points
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            The processed data
        """
        if gdf is None or len(gdf) == 0:
            self._log_progress("No {} features found.", 
                              feature_type, progress_callback)
            return None
        
        self._log_progress("✓ Found {} {} features", 
                          len(gdf), feature_type, progress_callback)
        
        # Convert polygons to points if requested
        if convert_polygons_to_points:
            gdf = self.convert_polygons_to_points(gdf, feature_type)
        
        return gdf

    def _get_boundary(self, area_or_polygon):
        """
        Get a boundary polygon from either a place name or a polygon.
        
        Parameters:
        -----------
        area_or_polygon : str or shapely.geometry
            Either a place name (string) or a polygon geometry
            
        Returns:
        --------
        boundary : shapely.geometry
            The boundary polygon
        """
        if isinstance(area_or_polygon, str):
            # It's a place name - get boundary from geocoding
            try:
                self.logger.info(f"Geocoding area: {area_or_polygon}")
                boundary = ox.geocode_to_gdf(area_or_polygon).unary_union
                return boundary
            except Exception as e:
                self.logger.error(f"Error geocoding area: {str(e)}")
                return None
        else:
            # It's already a polygon
            return area_or_polygon

    def _log_progress(self, message, arg1, arg2, progress_callback=None, is_error=False):

        """
        Log a progress message and call the progress callback if provided.
        
        Parameters:
        -----------
        message : str
            The message format string
        arg1 : any
            The first argument for the format string
        arg2 : any
            The second argument for the format string
        progress_callback : callable, optional
            Function to call with the formatted message
        is_error : bool, default=False
            Whether this is an error message
        """
        # Format the message
        if arg1 is not None and arg2 is not None:
            formatted_message = message.format(arg1, arg2)
        elif arg1 is not None:
            formatted_message = message.format(arg1)
        elif arg2 is not None:
            formatted_message = message.format(arg2)
        else:
            formatted_message = message
        
        # Log the message
        if is_error:
            self.logger.error(formatted_message)
        else:
            self.logger.info(formatted_message)
        
        # Call the progress callback if provided
        if progress_callback:
            progress_callback(formatted_message)



class HeatmapService:
    """
    Service class for handling heatmap generation and processing.
    Centralizes heatmap data preparation, categorization, and raster generation.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the heatmap service.
        
        Parameters:
        -----------
        logger : logging.Logger, optional
            Logger for outputting status messages. If None, a new logger will be created.
        """
        self.logger = logger or logging.getLogger("HeatmapService")
        
        # Default list of unwanted facility types
        self.unwanted_facilities = [
            'bench', 'atm', 'drinking_water', 'toilets', 'waste_basket', 
            'vending_machine', 'fountain', 'training', 'waste_disposal', 
            'recycling', 'payment_terminal', 'yes', 'driving_school', 
            'public_bookcase'
        ]
    
    def prepare_heatmap_data(self, amenity_gdf=None, shop_gdf=None, progress_callback=None):
        """
        Combine and prepare amenity and shop data for heatmap generation.
        
        Parameters:
        -----------
        amenity_gdf : geopandas.GeoDataFrame, optional
            GeoDataFrame containing amenity data
        shop_gdf : geopandas.GeoDataFrame, optional
            GeoDataFrame containing shop data
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        combined_gdf : geopandas.GeoDataFrame
            Combined and processed GeoDataFrame ready for heatmap generation
        """
        # List for storing combined data
        combined_data = []
        
        # Process amenity data if available
        if amenity_gdf is not None and len(amenity_gdf) > 0:
            # Make a copy to avoid modifying the original
            amenity_data = amenity_gdf.copy()
            
            # Keep only points
            points_mask = amenity_data.geometry.apply(lambda x: x.geom_type == 'Point')
            amenity_data = amenity_data[points_mask].copy()
            
            # Standardize columns
            if 'name' in amenity_data.columns:
                amenity_data = amenity_data[['geometry', 'name', 'amenity']].copy()
            else:
                amenity_data['name'] = None
                amenity_data = amenity_data[['geometry', 'name', 'amenity']].copy()
            
            # Rename columns for consistency
            amenity_data = amenity_data.rename(columns={'amenity': 'facility_type'})
            amenity_data['source'] = 'amenity'
            
            combined_data.append(amenity_data)
            self._log_progress(f"Added {len(amenity_data)} amenity points to heatmap dataset", progress_callback)
        
        # Process shop data if available
        if shop_gdf is not None and len(shop_gdf) > 0:
            # Make a copy to avoid modifying the original
            shop_data = shop_gdf.copy()
            
            # Keep only points
            points_mask = shop_data.geometry.apply(lambda x: x.geom_type == 'Point')
            shop_data = shop_data[points_mask].copy()
            
            # Standardize columns
            if 'name' in shop_data.columns:
                shop_data = shop_data[['geometry', 'name', 'shop']].copy()
            else:
                shop_data['name'] = None
                shop_data = shop_data[['geometry', 'name', 'shop']].copy()
            
            # Rename columns for consistency
            shop_data = shop_data.rename(columns={'shop': 'facility_type'})
            shop_data['source'] = 'shop'
            
            combined_data.append(shop_data)
            self._log_progress(f"Added {len(shop_data)} shop points to heatmap dataset", progress_callback)
        
        # Combine the datasets
        if combined_data:
            combined_gdf = pd.concat(combined_data, ignore_index=True)
            self._log_progress(f"Combined dataset has {len(combined_gdf)} points", progress_callback)
            
            # Clean the data
            combined_gdf = self.clean_heatmap_data(combined_gdf, progress_callback)
            
            return combined_gdf
        else:
            self._log_progress("No amenity or shop data available for heatmap", progress_callback)
            return None
    
    def clean_heatmap_data(self, gdf, progress_callback=None):
        """
        Clean the heatmap data by removing unwanted facility types,
        historical entries, and duplicates.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The GeoDataFrame to clean
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        cleaned_gdf : geopandas.GeoDataFrame
            The cleaned GeoDataFrame
        """
        if gdf is None or len(gdf) == 0:
            return gdf
        
        # Make a copy to avoid modifying the original
        cleaned_gdf = gdf.copy()
        
        # Remove unwanted facility types
        before_len = len(cleaned_gdf)
        cleaned_gdf = cleaned_gdf[~cleaned_gdf['facility_type'].isin(self.unwanted_facilities)]
        self._log_progress(f"Removed {before_len - len(cleaned_gdf)} unwanted facility types", progress_callback)
        
        # Remove entries containing 'was:' in facility_type (historical features)
        before_len = len(cleaned_gdf)
        cleaned_gdf = cleaned_gdf[~cleaned_gdf['facility_type'].astype(str).str.contains('was:')]
        self._log_progress(f"Removed {before_len - len(cleaned_gdf)} historical entries", progress_callback)
        
        # Remove duplicate geometries
        before_len = len(cleaned_gdf)
        cleaned_gdf['geom_str'] = cleaned_gdf.geometry.apply(lambda x: str(x))
        cleaned_gdf = cleaned_gdf.drop_duplicates(subset=['geom_str'])
        cleaned_gdf = cleaned_gdf.drop(columns=['geom_str'])
        self._log_progress(f"Removed {before_len - len(cleaned_gdf)} duplicate geometries", progress_callback)
        
        return cleaned_gdf
    
    def categorize_facilities(self, gdf, categories, progress_callback=None):
        """
        Categorize facilities based on a category dictionary.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The GeoDataFrame to categorize
        categories : dict
            Dictionary mapping categories to lists of facility types
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        categorized_gdf : geopandas.GeoDataFrame
            The categorized GeoDataFrame with a new 'category' column
        """
        if gdf is None or len(gdf) == 0:
            return gdf
        
        # Make a copy to avoid modifying the original
        categorized_gdf = gdf.copy()
        
        # Flatten the nested dictionary structure to get {amenity_type: category}
        amenity_to_category = {}
        for category, facility_types in categories.items():
            for facility_type in facility_types:
                amenity_to_category[facility_type] = category
        
        # Create a function to categorize each amenity
        def categorize_amenity(amenity):
            return amenity_to_category.get(amenity, 'uncategorized')
        
        # Apply categorization
        categorized_gdf['category'] = categorized_gdf['facility_type'].apply(categorize_amenity)
        
        self._log_progress(f"Data categorized with {categorized_gdf['category'].nunique()} unique categories", 
                         progress_callback)
        
        return categorized_gdf
    
    def generate_heatmaps(self, gdf, output_folder, cell_size=0.001, bandwidth=0.1, 
                         selected_categories=None, progress_callback=None):
        """
        Generate heatmap rasters for the given categories.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The categorized GeoDataFrame to process
        output_folder : str
            Path to the folder where rasters will be saved
        cell_size : float, default=0.001
            Size of each cell in the raster (in degrees)
        bandwidth : float, default=0.1
            KDE bandwidth parameter
        selected_categories : list, optional
            List of specific categories to process. If None, all categories will be processed.
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        results : dict
            Dictionary containing paths to generated rasters and metadata
        """
        if gdf is None or len(gdf) == 0:
            self._log_progress("No data to process for heatmaps", progress_callback)
            return None
        
        # Check if the data has a category column
        if 'category' not in gdf.columns:
            self._log_progress("Error: Data must be categorized before generating heatmaps", progress_callback)
            return None
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Get all categories if none specified
        if selected_categories is None or len(selected_categories) == 0:
            selected_categories = gdf['category'].unique()
            self._log_progress(f"No specific categories selected, processing all {len(selected_categories)} categories", 
                             progress_callback)
        else:
            self._log_progress(f"Processing {len(selected_categories)} selected categories", progress_callback)
        
        # Filter data to selected categories
        filtered_data = gdf[gdf['category'].isin(selected_categories)].copy()
        self._log_progress(f"Filtered data to {len(filtered_data)} points in selected categories", progress_callback)
        
        # Get the total bounds for creating the grid
        x_min, y_min, x_max, y_max = filtered_data.total_bounds
        
        # Create the base grid that will be used for all categories
        x_grid = np.arange(x_min, x_max + cell_size, cell_size)
        y_grid = np.arange(y_max, y_min - cell_size, -cell_size)
        xx, yy = np.meshgrid(x_grid, y_grid)
        
        # Calculate grid dimensions
        height = len(y_grid)
        width = len(x_grid)
        
        self._log_progress(f"Raster dimensions: {width}x{height} pixels", progress_callback)
        
        # Create the transform for the raster
        transform = from_origin(x_min, y_max, cell_size, cell_size)
        
        # Dictionary to store results
        results = {
            'raster_paths': {},
            'metadata': {
                'cell_size': cell_size,
                'bandwidth': bandwidth,
                'dimensions': (width, height),
                'bounds': (x_min, y_min, x_max, y_max)
            }
        }
        
        # Process each selected category
        for category in selected_categories:
            category_gdf = filtered_data[filtered_data['category'] == category]
            
            if len(category_gdf) < 15:
                self._log_progress(f"Skipping {category} due to low point count ({len(category_gdf)} points)", 
                                 progress_callback)
                continue
            
            self._log_progress(f"Processing {category} with {len(category_gdf)} points...", progress_callback)
            
            # Initialize an empty density array
            density = np.zeros((height, width), dtype='float32')
            
            # Get coordinates
            x_coords = category_gdf.geometry.x
            y_coords = category_gdf.geometry.y
            
            # Stack coordinates for KDE
            positions = np.vstack([xx.ravel(), yy.ravel()])
            values = np.vstack([x_coords, y_coords])
            
            # Perform KDE with specified bandwidth
            kernel = gaussian_kde(values, bw_method=bandwidth)
            density = kernel(positions)
            density = density.reshape(xx.shape)
            
            # Normalize density between 0 and 1
            if density.max() > density.min():
                density = (density - density.min()) / (density.max() - density.min())
            
            # Save raster
            output_path = os.path.join(output_folder, f"{category}_density.tif")
            
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=1,
                dtype='float32',
                crs=filtered_data.crs,
                transform=transform,
                nodata=None
            ) as dst:
                dst.write(density.astype('float32'), 1)
            
            # Store the path in results
            results['raster_paths'][category] = output_path
            self._log_progress(f"✓ Created raster for {category}", progress_callback)
        
        # Create a raster for all points combined
        self._log_progress("\nCreating combined heatmap of all points...", progress_callback)
        
        # Initialize an empty density array
        all_density = np.zeros((height, width), dtype='float32')
        
        # Get coordinates for all points
        x_coords = filtered_data.geometry.x
        y_coords = filtered_data.geometry.y
        
        # Stack coordinates for KDE
        positions = np.vstack([xx.ravel(), yy.ravel()])
        values = np.vstack([x_coords, y_coords])
        
        # Perform KDE
        kernel = gaussian_kde(values, bw_method=bandwidth)
        all_density = kernel(positions)
        all_density = all_density.reshape(xx.shape)
        
        # Normalize density between 0 and 1
        if all_density.max() > all_density.min():
            all_density = (all_density - all_density.min()) / (all_density.max() - all_density.min())
        
        # Save combined raster
        all_output_path = os.path.join(output_folder, "all_categories_density.tif")
        
        with rasterio.open(
            all_output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype='float32',
            crs=filtered_data.crs,
            transform=transform,
            nodata=None
        ) as dst:
            dst.write(all_density.astype('float32'), 1)
        
        # Store the path in results
        results['raster_paths']['all_categories'] = all_output_path
        self._log_progress(f"✓ Created combined raster for all categories", progress_callback)
        self._log_progress("\nHeatmap generation complete!", progress_callback)
        self._log_progress(f"All rasters saved to: {output_folder}", progress_callback)
        
        return results
    
    def create_heatmap_preview(self, output_folder, selected_categories, progress_callback=None):
        """
        Create a preview visualization of the generated heatmaps.
        
        Parameters:
        -----------
        output_folder : str
            Path to the folder containing the generated rasters
        selected_categories : list
            List of categories to include in the preview (up to 4 will be shown)
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        fig : matplotlib.figure.Figure
            The generated figure, or None if preview could not be created
        """
        try:
            # Limit to 4 categories for the preview
            max_previews = min(4, len(selected_categories))
            preview_categories = list(selected_categories)[:max_previews]
            
            # Create a figure with subplots
            fig, axes = plt.subplots(1, max_previews, figsize=(16, 4))
            
            # Create a custom colormap
            colors = [(0, 0, 0, 0), (0, 0, 1, 0.5), (0, 1, 0, 0.5), (1, 1, 0, 0.5), (1, 0, 0, 0.8)]
            cmap = LinearSegmentedColormap.from_list('density', colors, N=100)
            
            # Plot a preview of each raster
            for i, category in enumerate(preview_categories):
                # Find the corresponding raster file
                raster_path = os.path.join(output_folder, f"{category}_density.tif")
                if os.path.exists(raster_path):
                    with rasterio.open(raster_path) as src:
                        ax = axes[i] if max_previews > 1 else axes
                        raster_img = src.read(1)
                        ax.imshow(raster_img, cmap=cmap)
                        ax.set_title(f"{category}")
                        ax.axis('off')
            
            plt.tight_layout()
            
            self._log_progress("Previews shown for the first few generated heatmaps.", progress_callback)
            
            return fig
            
        except Exception as e:
            self._log_progress(f"Could not create previews: {str(e)}", progress_callback, is_error=True)
            return None
            
    def _log_progress(self, message, progress_callback=None, is_error=False):
        """
        Log a progress message and call the progress callback if provided.
        
        Parameters:
        -----------
        message : str
            The progress message
        progress_callback : callable, optional
            Function to call with the message
        is_error : bool, default=False
            Whether this is an error message
        """
        # Log the message
        if is_error:
            self.logger.error(message)
        else:
            self.logger.info(message)
        
        # Call the progress callback if provided
        if progress_callback:
            progress_callback(message)



class StreetNetworkService:
    """
    Service class for handling street network processing and analysis.
    Centralizes network processing, analysis, and visualization.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the street network service.
        
        Parameters:
        -----------
        logger : logging.Logger, optional
            Logger for outputting status messages. If None, a new logger will be created.
        """
        self.logger = logger or logging.getLogger("StreetNetworkService")
    
    def process_street_network(self, gdf, base_folder, area_name, progress_callback=None):
        """
        Process the raw street network data.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            GeoDataFrame containing street network data
        area_name : str
            Name of the area for folder naming
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        result : dict
            Dictionary containing processed data and metadata
        """
        if gdf is None or len(gdf) == 0:
            self._log_progress("No street network data to process", progress_callback)
            return None
        
        self._log_progress(f"Processing street network with {len(gdf)} features...", progress_callback)
        
        def get_utm_crs(gdf):
            """Determine the best UTM CRS based on the centroid of the data's extent."""
            # Calculate the centroid of the bounds in WGS84
            bounds = gdf.to_crs(epsg=4326).total_bounds  # (minx, miny, maxx, maxy)
            lon = (bounds[0] + bounds[2]) / 2  # average of min and max longitudes
            lat = (bounds[1] + bounds[3]) / 2  # average of min and max latitudes
            
            # Calculate UTM zone number
            zone_number = int(((lon + 180) / 6) % 60) + 1
            
            # Determine if in northern or southern hemisphere
            return 32600 + zone_number if lat >= 0 else 32700 + zone_number
            
        network_gdf = gdf.copy()

        utm_crs = get_utm_crs(network_gdf)
        self._log_progress(f"Converting to appropriate CRS -- {utm_crs}", progress_callback)
        network_gdf = network_gdf.to_crs(epsg=utm_crs)
        
        # Keep only LineString geometries
        self._log_progress(f"Filtering for LineStrings (before: {len(network_gdf)} features)", progress_callback)
        network_gdf = network_gdf[network_gdf.geometry.apply(lambda x: x.geom_type == 'LineString')]
        self._log_progress(f"After filtering: {len(network_gdf)} LineString features", progress_callback)
        
        # Standardize the columns
        network_gdf = self.standardize_network_columns(network_gdf, progress_callback)
        
        # Store the original street network
        raw_network = network_gdf.copy()
        
        # Generate folder name and ensure it exists
        folder_name = self.create_output_folder(base_folder, area_name, progress_callback)
        
        # Process the network geometry
        try:
            self._log_progress("Performing spatial operations...", progress_callback)
            
            # Import pygeoops (within the try block to handle potential import errors)
            import pygeoops
            
            # Dissolve by name
            self._log_progress("Dissolving by name...", progress_callback)
            dissolved = network_gdf.dissolve(by='name')
            
            # Create 10m buffer around each road
            self._log_progress("Creating 10m buffers around roads...", progress_callback)
            dissolved['geometry'] = dissolved.buffer(10)
            
            # Dissolve all to a single feature
            self._log_progress("Final dissolve...", progress_callback)
            final_dissolved = dissolved.dissolve()
            
            # Create centerlines
            self._log_progress("Generating centerlines...", progress_callback)
            final_dissolved.geometry = pygeoops.centerline(final_dissolved.geometry)
            
            # Store the processed data
            processed_network = final_dissolved
            
            # Save both original and processed networks
            self._log_progress(f"\nSaving data to {folder_name}...", progress_callback)
            
            raw_path = os.path.join(folder_name, "street_network_raw.geojson")
            processed_path = os.path.join(folder_name, "street_network_processed.geojson")
            
            raw_network.to_file(raw_path, driver='GeoJSON')
            processed_network.to_file(processed_path, driver='GeoJSON')
            
            self._log_progress("\n✓ Street network processing complete!", progress_callback)
            self._log_progress(f"Original network: {len(raw_network)} road segments", progress_callback)
            self._log_progress(f"Processed centerlines saved to {folder_name}", progress_callback)
            
            # Return results
            return {
                'raw_network': raw_network,
                'processed_network': processed_network,
                'paths': {
                    'raw': raw_path,
                    'processed': processed_path
                },
                'folder': folder_name
            }
            
        except Exception as e:
            self._log_progress(f"Error during spatial processing: {str(e)}", progress_callback, is_error=True)
            import traceback
            traceback.print_exc()
            return None
    
    def standardize_network_columns(self, gdf, progress_callback=None):
        """
        Standardize columns for street network data.
        
        Parameters:
        -----------
        gdf : geopandas.GeoDataFrame
            The GeoDataFrame to standardize
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        gdf : geopandas.GeoDataFrame
            GeoDataFrame with standardized columns
        """
        if gdf is None or len(gdf) == 0:
            return gdf
        
        # Make a copy to avoid modifying the original
        std_gdf = gdf.copy()
        
        # Select only required columns, handling missing columns gracefully
        all_columns = list(std_gdf.columns)
        keep_columns = ['highway', 'geometry']
        
        # Check if name columns exist and add them to our keep list
        if 'name' in all_columns:
            keep_columns.append('name')
        if 'name:en' in all_columns:
            keep_columns.append('name:en')
        
        # Filter to just the columns we want to keep
        std_gdf = std_gdf[[col for col in keep_columns if col in all_columns]]
        self._log_progress(f"Keeping only essential columns: {', '.join(keep_columns)}", progress_callback)
        
        # Ensure 'name' exists for the dissolve operation
        if 'name' not in std_gdf.columns:
            if 'name:en' in std_gdf.columns:
                std_gdf['name'] = std_gdf['name:en']
            else:
                # Create a name based on highway type and an index
                std_gdf['name'] = std_gdf.index.map(lambda idx: f"road_{idx}")
        
        # Fill missing names with generic names
        nan_mask = std_gdf['name'].isna()
        if nan_mask.any():
            # Create list of unnamed road identifiers
            unnamed_roads = [f"unnamed_road_{i}" for i in range(sum(nan_mask))]
            # Assign to NaN locations
            std_gdf.loc[nan_mask, 'name'] = unnamed_roads
            
        return std_gdf
    
    def create_output_folder(self, base_folder, area_name, progress_callback=None):
        """
        Create an output folder for storing processed data.
        
        Parameters:
        -----------
        area_name : str
            Name of the area for folder naming
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        folder_name : str
            Path to the created folder
        """
        # Create a clean folder name from the area name
        clean_area_name = area_name.replace(', ', '_').replace(' ', '_') + "_street_network"
        folder_name = os.path.join(base_folder, clean_area_name)

        # Create the folder if it doesn't exist
        os.makedirs(folder_name, exist_ok=True)
        
        return folder_name
    
    def create_network_map(self, raw_network=None, processed_network=None, center=None, zoom_start=13, progress_callback=None):
        """
        Create a Folium map visualization of the street network.
        
        Parameters:
        -----------
        raw_network : geopandas.GeoDataFrame, optional
            GeoDataFrame containing raw street network data
        processed_network : geopandas.GeoDataFrame, optional
            GeoDataFrame containing processed street network data
        center : tuple, optional
            (latitude, longitude) tuple for map center. If None, calculated from data.
        zoom_start : int, default=13
            Initial zoom level for the map
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        m : folium.Map
            Folium map object with the street network visualization
        """
        self._log_progress("Generating map visualization...", progress_callback)
        
        # Determine map center if not provided
        if center is None:
            if processed_network is not None:
                # convert to WGS84
                processed_network = processed_network.to_crs(epsg=4326)
                centroid = processed_network.unary_union.centroid
                center = (centroid.y, centroid.x)
            elif raw_network is not None:
                # convert to WGS84
                raw_network = raw_network.to_crs(epsg=4326)
                centroid = raw_network.unary_union.centroid
                center = (centroid.y, centroid.x)
            else:
                # Default center if no data is provided
                center = (40.1872, 44.5152)  # Yerevan, Armenia
        
        # Create the map
        m = folium.Map(location=center, zoom_start=zoom_start)
        
        # Add the raw street network as blue lines
        if raw_network is not None:
            self._log_progress("Adding original street network to map...", progress_callback)
            folium.GeoJson(
                raw_network.__geo_interface__, 
                name="Original Streets",
                style_function=lambda x: {'color': 'blue', 'weight': 1.5, 'opacity': 0.7}
            ).add_to(m)
        
        # Add the processed centerlines as red lines
        if processed_network is not None:
            self._log_progress("Adding processed centerlines to map...", progress_callback)
            folium.GeoJson(
                processed_network.__geo_interface__, 
                name="Processed Centerlines",
                style_function=lambda x: {'color': 'red', 'weight': 2.5, 'opacity': 0.9}
            ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        self._log_progress("Map visualization ready!", progress_callback)
        
        return m
    
    def analyze_network_statistics(self, raw_network, processed_network=None, progress_callback=None):
        """
        Analyze street network statistics.
        
        Parameters:
        -----------
        raw_network : geopandas.GeoDataFrame
            GeoDataFrame containing raw street network data
        processed_network : geopandas.GeoDataFrame, optional
            GeoDataFrame containing processed street network data
        progress_callback : callable, optional
            Function to call with progress updates
            
        Returns:
        --------
        stats : dict
            Dictionary containing network statistics
        """
        self._log_progress("Analyzing street network statistics...", progress_callback)
        
        stats = {}
        
        if raw_network is not None:
            # Calculate raw network statistics
            stats['raw'] = {
                'segment_count': len(raw_network),
                'total_length_km': raw_network.geometry.length.sum() / 1000,
                'avg_segment_length_m': raw_network.geometry.length.mean(),
                'highway_types': raw_network['highway'].value_counts().to_dict() if 'highway' in raw_network.columns else {},
            }
            
            # Calculate length by road type if highway column exists
            if 'highway' in raw_network.columns:
                length_by_type = raw_network.groupby('highway').agg({'geometry': lambda x: sum(geom.length for geom in x)})
                stats['raw']['length_by_type_km'] = {k: v/1000 for k, v in length_by_type.to_dict()['geometry'].items()}
        
        if processed_network is not None:
            # Calculate processed network statistics
            stats['processed'] = {
                'total_length_km': processed_network.geometry.length.sum() / 1000,
                'centerline_segments': len(processed_network),
            }
        
        self._log_progress("Network analysis complete", progress_callback)
        
        return stats
    
    def _log_progress(self, message, progress_callback=None, is_error=False):
        """
        Log a progress message and call the progress callback if provided.
        
        Parameters:
        -----------
        message : str
            The progress message
        progress_callback : callable, optional
            Function to call with the message
        is_error : bool, default=False
            Whether this is an error message
        """
        # Log the message
        if is_error:
            self.logger.error(message)
        else:
            self.logger.info(message)
        
        # Call the progress callback if provided
        if progress_callback:
            progress_callback(message)


