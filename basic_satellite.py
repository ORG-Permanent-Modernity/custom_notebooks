# improved_satellite_widgets.py
# Module containing improved interactive widgets for Earth Engine satellite processing

import ipywidgets as widgets
from IPython.display import display
import ee
import folium

class SatelliteProcessor:
    """A class to manage satellite data processing and visualization in a two-stage approach"""
    
    def __init__(self):
        """Initialize the processor and create the initial widget"""
        # Check if Earth Engine is initialized
        try:
            ee.Initialize()
        except:
            print("Earth Engine needs to be initialized. Please run: ee.Authenticate() and ee.Initialize()")
        
        # Store processed data
        self.processed_data = None
        self.region = None
        self.collections = {}
        self.yearly_averages = {}
        self.mean_indices = {}
        
        # Create the input widget
        self._create_input_widget()
    
    def _create_input_widget(self):
        """Create the first widget for data selection and processing"""
        # Create dropdown widgets for variables
        years = list(range(1985, 2026))
        months = list(range(1, 13))
        satellites = ['Landsat']  # Can add 'Sentinel' if needed
        
        # Year widgets
        self.year_start_widget = widgets.Dropdown(
            options=years,
            value=2020,
            description='Start Year:',
            disabled=False,
            layout=widgets.Layout(width='200px')
        )

        self.year_end_widget = widgets.Dropdown(
            options=years,
            value=2022,
            description='End Year:',
            disabled=False,
            layout=widgets.Layout(width='200px')
        )

        # Month widgets
        self.month_start_widget = widgets.Dropdown(
            options=months,
            value=1,
            description='Start Month:',
            disabled=False,
            layout=widgets.Layout(width='200px')
        )

        self.month_end_widget = widgets.Dropdown(
            options=months,
            value=5,
            description='End Month:',
            disabled=False,
            layout=widgets.Layout(width='200px')
        )

        # Satellite selection
        self.satellite_widget = widgets.Dropdown(
            options=satellites,
            value='Landsat',
            description='Satellite:',
            disabled=False,
            layout=widgets.Layout(width='200px')
        )

        # Region widget
        self.region_widget = widgets.Text(
            value="projects/ee-loucasdiamantboustead/assets/AOI_gaza",
            description='Region Asset:',
            disabled=False,
            layout=widgets.Layout(width='400px')
        )

        # Create process button
        self.process_button = widgets.Button(
            description='Process Data',
            button_style='primary',
            tooltip='Click to process satellite data',
            layout=widgets.Layout(width='150px'),
            icon='satellite'
        )
        self.process_button.on_click(self._on_process_click)

        # Create output area for processing feedback
        self.process_output = widgets.Output()
        
        # Header and description
        header = widgets.HTML(value="<h2>Earth Engine Satellite Processor</h2>")
        description = widgets.HTML(
            value="<p>Select parameters for satellite image processing and click 'Process Data'.</p>"
        )

        # Layout organization
        inputs_box = widgets.VBox([
            self.year_start_widget, 
            self.year_end_widget, 
            self.month_start_widget, 
            self.month_end_widget,
            self.satellite_widget,
            self.region_widget
        ])
        
        control_box = widgets.VBox([self.process_button])
        top_box = widgets.HBox([inputs_box, control_box])
        
        # Create the complete widget
        self.input_widget = widgets.VBox([header, description, top_box, self.process_output])
    
    def _on_process_click(self, button):
        """Handle the process button click event"""
        # Clear previous output
        self.process_output.clear_output()
        
        # Get current parameter values
        start_year = self.year_start_widget.value
        end_year = self.year_end_widget.value
        start_month = self.month_start_widget.value
        end_month = self.month_end_widget.value
        satellite = self.satellite_widget.value
        region_asset = self.region_widget.value
        
        # Display parameters
        with self.process_output:
            print(f"Parameters selected:")
            print(f"Year range: {start_year}-{end_year}")
            print(f"Month range: {start_month}-{end_month}")
            print(f"Satellite: {satellite}")
            print(f"Region asset: {region_asset}")
            print("\nProcessing data...")
            
            try:
                # Get the region feature
                self.region = ee.FeatureCollection(region_asset)
                
                # Process both indices (NDVI and NDSI)
                self._process_all_indices(start_year, end_year, start_month, end_month)
                
                # Create and display the visualization widget
                self._create_visualization_widget()
                display(self.viz_widget)
                
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                print("Please check your Earth Engine asset path and make sure Earth Engine is initialized.")
    
    def _process_all_indices(self, start_year, end_year, start_month, end_month):
        """Process all indices for the given parameters"""
        indices = ['NDVI', 'NDSI']
        
        for index_type in indices:
            with self.process_output:
                print(f"\nProcessing {index_type}...")
                
                # Process the data
                collections, yearly_averages = self._process_yearly_data(
                    start_year, 
                    end_year, 
                    self.region, 
                    index_type=index_type,
                    start_month=start_month,
                    end_month=end_month
                )
                
                # Store the processed data
                self.collections[index_type] = collections
                self.yearly_averages[index_type] = yearly_averages
                
                # Calculate mean index
                collection_list = self._list_to_collection(collections)
                mean_index = collection_list.select(index_type).reduce(ee.Reducer.mean())
                self.mean_indices[index_type] = mean_index
                
                print(f"Completed processing {index_type}")
                
        with self.process_output:
            print("\nAll processing complete! Use the visualization widget below to explore results.")
    
    def _create_visualization_widget(self):
        """Create a widget to visualize the processed results"""
        # Create widgets for visualization options
        self.index_viz_widget = widgets.Dropdown(
            options=['NDVI', 'NDSI'],
            value='NDSI',
            description='Index:',
            disabled=False,
            layout=widgets.Layout(width='200px')
        )
        
        self.viz_type_widget = widgets.Dropdown(
            options=[
                ('Yearly Deviation from Mean', 'deviation'),
                ('Yearly Composites', 'composite'),
                ('Mean Index Map', 'mean_map'),
                ('Yearly Averages Chart', 'chart'),
                ('Batch Export to Drive', 'batch_save')
            ],
            value='deviation',
            description='Function:',
            layout=widgets.Layout(width='250px')
        )
        
        # Year selection widget (initially hidden)
        start_year = self.year_start_widget.value
        end_year = self.year_end_widget.value
        years = list(range(start_year, end_year + 1))
        
        self.year_select_widget = widgets.Dropdown(
            options=years,
            value=years[-1],  # Default to most recent year
            description='Year:',
            disabled=False,
            layout=widgets.Layout(width='200px'),
            style={'visibility': 'hidden'}  # Initially hidden
        )
        
        # Google Drive folder input (initially hidden)
        self.drive_folder_widget = widgets.Text(
            value="satellite_data",
            description='Drive folder:',
            placeholder='Folder name to save to',
            disabled=False,
            layout=widgets.Layout(width='250px'),
            style={'visibility': 'hidden'}  # Initially hidden
        )
        
        # Create visualization button
        self.viz_button = widgets.Button(
            description='Visualize',
            button_style='info',
            tooltip='Click to visualize the selected data',
            layout=widgets.Layout(width='150px'),
            icon='chart-line'
        )
        self.viz_button.on_click(self._on_viz_click)
        
        # Create output area for visualization
        self.viz_output = widgets.Output()
        
        # Header and description
        viz_header = widgets.HTML(value="<h3>Visualization Options</h3>")
        viz_description = widgets.HTML(
            value="<p>Select which data to visualize and click 'Visualize'.</p>"
        )
        
        # Show/hide widgets based on visualization type
        def on_viz_type_change(change):
            if change['new'] in ['deviation', 'composite']:
                self.year_select_widget.layout.visibility = 'visible'
                self.drive_folder_widget.layout.visibility = 'hidden'
                self.viz_button.description = 'Visualize'
                self.viz_button.icon = 'chart-line'
            elif change['new'] == 'batch_save':
                self.year_select_widget.layout.visibility = 'hidden'
                self.drive_folder_widget.layout.visibility = 'visible'
                self.viz_button.description = 'Start Export'
                self.viz_button.icon = 'save'
            else:
                self.year_select_widget.layout.visibility = 'hidden'
                self.drive_folder_widget.layout.visibility = 'hidden'
                self.viz_button.description = 'Visualize'
                self.viz_button.icon = 'chart-line'
        
        self.viz_type_widget.observe(on_viz_type_change, names='value')
        
        # Layout
        viz_controls = widgets.HBox([
            self.index_viz_widget, 
            self.viz_type_widget, 
            self.year_select_widget,
            self.drive_folder_widget,
            self.viz_button
        ])
        
        # Create the complete visualization widget
        self.viz_widget = widgets.VBox([
            viz_header, 
            viz_description, 
            viz_controls, 
            self.viz_output
        ])
    
    def _on_viz_click(self, button):
        """Handle the visualization button click"""
        # Clear previous visualization
        self.viz_output.clear_output()
        
        # Get current visualization parameters
        index_type = self.index_viz_widget.value
        viz_type = self.viz_type_widget.value
        
        with self.viz_output:
            try:
                if viz_type == 'deviation':
                    self._display_deviation(index_type)
                elif viz_type == 'composite':
                    self._display_composites(index_type)
                elif viz_type == 'mean_map':
                    self._display_mean_map(index_type)
                elif viz_type == 'chart':
                    self._display_yearly_chart(index_type)
                elif viz_type == 'batch_save':
                    self._batch_save_to_drive(index_type)
            except Exception as e:
                print(f"Error in visualization: {e}")
                import traceback
                traceback.print_exc()
    
    def _display_deviation(self, index_type):
        """Display deviation from mean visualization for a specific year"""
        # Get selected year
        selected_year = self.year_select_widget.value
        
        print(f"Displaying {index_type} deviation from mean for {selected_year}")
        
        # Get the yearly averages
        yearly_avgs = self.yearly_averages[index_type]
        
        # Display yearly averages
        print("\nYearly averages:")
        for year, avg in yearly_avgs.items():
            print(f"{year}: {avg:.2f}")
            
        print(f"\nSelected year ({selected_year}): {yearly_avgs[selected_year]:.2f}")
        
        # Create map centered on the region
        region_center = self.region.geometry().centroid().coordinates().getInfo()
        center_lon, center_lat = region_center[0], region_center[1]
        
        # Create folium map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
        
        # Define visualization parameters
        viz_params = self._get_viz_params(index_type)
        
        # Create yearly composite for the selected year
        yearly_composite = self._create_yearly_composite(
            selected_year, 
            self.region, 
            index_type=index_type,
            start_month=self.month_start_widget.value, 
            end_month=self.month_end_widget.value
        )
        
        # Add mean index layer
        mean_index = self.mean_indices[index_type]
        map_id_dict = mean_index.getMapId(viz_params)
        folium.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'Mean {index_type}',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Add yearly composite layer
        comp_map_id_dict = yearly_composite.getMapId(viz_params)
        folium.TileLayer(
            tiles=comp_map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'{selected_year} {index_type}',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Calculate and display deviation
        deviation = yearly_composite.subtract(mean_index)
        deviation_viz = {
            'min': -0.5, 
            'max': 0.5, 
            'palette': ['blue', 'white', 'red']
        }
        
        dev_map_id_dict = deviation.getMapId(deviation_viz)
        folium.TileLayer(
            tiles=dev_map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'{selected_year} Deviation',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Display the map
        display(m)
    
    def _display_composites(self, index_type):
        """Display yearly composites for a specific year"""
        # Get selected year
        selected_year = self.year_select_widget.value
        
        print(f"Displaying {index_type} yearly composite for {selected_year}")
        
        # Get the yearly averages
        yearly_avgs = self.yearly_averages[index_type]
        
        # Display yearly average for selected year
        print(f"\nSelected year ({selected_year}): {yearly_avgs[selected_year]:.2f}")
        
        # Create map centered on the region
        region_center = self.region.geometry().centroid().coordinates().getInfo()
        center_lon, center_lat = region_center[0], region_center[1]
        
        # Create folium map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
        
        # Define visualization parameters
        viz_params = self._get_viz_params(index_type)
        
        # Create yearly composite for the selected year
        yearly_composite = self._create_yearly_composite(
            selected_year, 
            self.region, 
            index_type=index_type,
            start_month=self.month_start_widget.value, 
            end_month=self.month_end_widget.value
        )
        
        # Add yearly composite layer
        comp_map_id_dict = yearly_composite.getMapId(viz_params)
        folium.TileLayer(
            tiles=comp_map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'{selected_year} {index_type}',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Display the map
        display(m)
    
    def _display_mean_map(self, index_type):
        """Display mean index map"""
        print(f"Displaying {index_type} mean map")
        
        # Create map centered on the region
        region_center = self.region.geometry().centroid().coordinates().getInfo()
        center_lon, center_lat = region_center[0], region_center[1]
        
        # Create folium map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
        
        # Define visualization parameters
        viz_params = self._get_viz_params(index_type)
        
        # Add mean index layer
        mean_index = self.mean_indices[index_type]
        map_id_dict = mean_index.getMapId(viz_params)
        folium.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'Mean {index_type}',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Display the map
        display(m)
    
    def _display_yearly_chart(self, index_type):
        """Display yearly averages chart with trend line"""
        try:
            # Try to import required libraries
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Get yearly averages
            yearly_avgs = self.yearly_averages[index_type]
            
            # Extract data for plotting
            x = list(yearly_avgs.keys())
            y = list(yearly_avgs.values())
            
            # Calculate trend line
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            
            # Get month names for title
            months = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April', 
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'
            }
            start_month = self.month_start_widget.value
            end_month = self.month_end_widget.value
            
            # Get region name from asset path
            region_asset = self.region_widget.value
            site = region_asset.split('/')[-1]
            
            # Create figure
            plt.figure(figsize=(12, 6))
            
            # Plot data and trend line
            plt.plot(x, y, marker='o', linestyle='-', linewidth=2, markersize=6, label='Annual Average')
            plt.plot(x, p(x), 'r--', linewidth=2, label=f'Trend: {z[0]:.2f} per year')
            
            # Configure x-axis with appropriate step size
            year_range = max(x) - min(x)
            if year_range > 30:
                step = 10
            elif year_range > 15:
                step = 5
            else:
                step = 2
                
            plt.xticks(np.arange(min(x), max(x)+1, step=step))
            
            # Add labels and title
            plt.xlabel("Year", fontsize=12)
            plt.ylabel(f"Average {index_type} x 10,000", fontsize=12)
            plt.title(f"{site} {index_type} from {months[start_month]} - {months[end_month]}", fontsize=14)
            
            # Add grid and legend
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()
            
            # Improve appearance
            plt.tight_layout()
            
            # Display statistics
            avg_value = np.mean(y)
            slope = z[0]
            percent_change = (slope / avg_value) * 100
            
            stats_text = (
                f"Average {index_type}: {avg_value:.2f}\n"
                f"Trend: {slope:.2f} units/year\n"
                f"Relative change: {percent_change:.2f}% per year"
            )
            
            plt.figtext(0.02, -0.02, stats_text, fontsize=10)
            
            # Show plot
            plt.show()
            
        except ImportError:
            print("Matplotlib and NumPy are required for chart visualization.")
            print("Please install them with: !pip install matplotlib numpy")
        
    def _batch_save_to_drive(self, index_type):
        """Create batch export tasks for all processed images to Google Drive"""
        import time
        import ee
        
        # Get folder name for Google Drive
        folder_name = self.drive_folder_widget.value
        
        with self.viz_output:
            try:
                # Get parameters for file naming and export
                start_year = self.year_start_widget.value
                end_year = self.year_end_widget.value
                start_month = self.month_start_widget.value
                end_month = self.month_end_widget.value
                region_asset = self.region_widget.value.split('/')[-1]
                
                # Track all export tasks
                export_tasks = []
                
                print(f"Starting batch export tasks for {index_type}...")
                
                # 1. Export mean index
                mean_task = ee.batch.Export.image.toDrive(
                    image=self.mean_indices[index_type],
                    description=f"mean_{index_type}_{region_asset}",
                    folder=folder_name,
                    scale=30,
                    crs='EPSG:4326',
                    region=self.region.geometry(),
                    fileFormat='GeoTIFF',
                    maxPixels=1e9
                )
                mean_task.start()
                export_tasks.append(mean_task)
                print(f"Started task: mean_{index_type}_{region_asset}")
                
                # 2. Export yearly composites and deviations
                for year in range(start_year, end_year + 1):
                    # Create yearly composite
                    yearly_composite = self._create_yearly_composite(
                        year, 
                        self.region, 
                        index_type=index_type,
                        start_month=start_month, 
                        end_month=end_month
                    )
                    
                    # Export composite
                    composite_task = ee.batch.Export.image.toDrive(
                        image=yearly_composite,
                        description=f"{year}_{index_type}_composite_{region_asset}",
                        folder=folder_name,
                        scale=30,
                        crs='EPSG:4326',
                        region=self.region.geometry(),
                        fileFormat='GeoTIFF',
                        maxPixels=1e9
                    )
                    composite_task.start()
                    export_tasks.append(composite_task)
                    print(f"Started task: {year}_{index_type}_composite_{region_asset}")
                    
                    # Create and export deviation
                    deviation = yearly_composite.subtract(self.mean_indices[index_type])
                    deviation_task = ee.batch.Export.image.toDrive(
                        image=deviation,
                        description=f"{year}_{index_type}_deviation_{region_asset}",
                        folder=folder_name,
                        scale=30,
                        crs='EPSG:4326',
                        region=self.region.geometry(),
                        fileFormat='GeoTIFF',
                        maxPixels=1e9
                    )
                    deviation_task.start()
                    export_tasks.append(deviation_task)
                    print(f"Started task: {year}_{index_type}_deviation_{region_asset}")
                    
                    # Brief pause to avoid overwhelming the API
                    time.sleep(0.5)
                
                # Create table of all tasks
                print(f"\nStarted {len(export_tasks)} export tasks to folder '{folder_name}' in Google Drive")
                print("\nTask Summary:")
                print("-" * 50)
                for i, task in enumerate(export_tasks):
                    task_id = task.id
                    task_name = task.config['description']
                    print(f"{i+1}. Task ID: {task_id} | Name: {task_name}")
                print("-" * 50)
                print("\nYou can monitor these tasks in the Earth Engine Task tab.")
                print("Once completed, GeoTIFF files will appear in your Google Drive folder.")
                
            except Exception as e:
                print(f"Error in batch export: {e}")
                import traceback
                traceback.print_exc()


    # Helper functions
    def _list_to_collection(self, image_list):
        """Merge multiple image collections into one."""
        merged_collection = ee.ImageCollection(image_list[0])
        for collection in image_list[1:]:
            merged_collection = merged_collection.merge(collection)
        return merged_collection

    def _calculate_index(self, image, bands, index_name):
        """Calculate normalized difference index."""
        index = image.normalizedDifference(bands).rename(index_name)
        return image.addBands(index)

    def _calculate_L5_index(self, image, index_type='NDSI'):
        """Calculate index for Landsat 5."""
        bands = {
            'NDSI': ['SR_B2', 'SR_B5'],
            'NDVI': ['SR_B4', 'SR_B3']
        }
        return self._calculate_index(image, bands[index_type], index_type)

    def _calculate_L8_index(self, image, index_type='NDVI'):
        """Calculate index for Landsat 8."""
        bands = {
            'NDSI': ['SR_B3', 'SR_B6'],
            'NDVI': ['SR_B5', 'SR_B4']
        }
        return self._calculate_index(image, bands[index_type], index_type)

    def _calc_mean_index(self, collection, region, index_type):
        """Calculate mean value of the specified index for a collection."""
        mean = collection.select(index_type).reduce(ee.Reducer.mean())
        mean_value = mean.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=30,
            maxPixels=1e9
        )
        return mean_value.getInfo()[f'{index_type}_mean'] * 10_000

    def _get_imagery(self, satellite, year, region, start_month, end_month):
        """Get filtered imagery for a specific year and region."""
        return (satellite
                .filterBounds(region)
                .filterDate(f'{year}-{start_month:02d}-01', f'{year}-{end_month:02d}-30')
                .filterMetadata('CLOUD_COVER', 'less_than', 20))

    def _create_yearly_composite(self, year, region, index_type='NDSI', start_month=1, end_month=5, return_index=True):
        """Create a yearly composite with the specified index."""
        # Determine which Landsat satellite and calculator to use
        if year < 2013:
            if year in [2003, 2012]:
                landsat = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
            else:
                landsat = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
            calculate_fn = lambda img: self._calculate_L5_index(img, index_type)
        else:
            landsat = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
            calculate_fn = lambda img: self._calculate_L8_index(img, index_type)
        
        # Process collection
        collection = self._get_imagery(landsat, year, region, start_month, end_month)
        clipped = collection.map(lambda img: img.clip(region))
        index_added = clipped.map(calculate_fn)
        
        if return_index:
            composite = index_added.select(index_type).mean()
        else:
            composite = index_added.mean()
        
        return composite.set('year', ee.Number(year))

    def _process_yearly_data(self, start_year, end_year, region, index_type='NDSI', start_month=1, end_month=5):
        """Process data for a range of years and return collections and averages."""
        # Initialize Landsat collections
        landsat5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
        landsat7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        landsat8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        
        collection_list = []
        yearly_averages = {}
        
        for year in range(start_year, end_year + 1):
            # Determine which Landsat and calculator to use
            if year in [2003, 2012]:
                landsat = landsat7
                calculate_fn = lambda img: self._calculate_L5_index(img, index_type)
            elif year < 2013:
                landsat = landsat5
                calculate_fn = lambda img: self._calculate_L5_index(img, index_type)
            else:
                landsat = landsat8
                calculate_fn = lambda img: self._calculate_L8_index(img, index_type)
            
            # Process imagery
            collection = self._get_imagery(landsat, year, region, start_month, end_month)
            clipped = collection.map(lambda img: img.clip(region))
            index_added = clipped.map(calculate_fn)
            
            # Calculate and store results
            yearly_averages[year] = self._calc_mean_index(index_added, region, index_type)
            collection_list.append(index_added)
            print(f"Processed {year}")
        
        return collection_list, yearly_averages
        
    def _get_viz_params(self, index_type):
        """Get visualization parameters based on index type"""
        if index_type == 'NDVI':
            return {'min': -1, 'max': 1, 'palette': ['red', 'white', 'green']}
        else:  # NDSI
            return {'min': -1, 'max': 1, 'palette': ['blue', 'white', 'red']}
            

def create_satellite_processor():
    """
    Creates and returns an improved satellite processor widget
    that separates data processing from visualization
    """
    processor = SatelliteProcessor()
    return processor.input_widget