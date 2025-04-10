import os
import osmnx as ox
import pandas as pd
import geopandas as gpd
import ipywidgets as widgets
from ipywidgets import HBox, VBox, Layout, HTML
from IPython.display import display, clear_output
import matplotlib.pyplot as plt
import folium
from folium.plugins import MarkerCluster
from osm_tags import osm_features
from heatmap_templates import all_templates

from osm_service_classes import OSMDataService, HeatmapService, StreetNetworkService

# Initialize the default area
default_area = "Yerevan, Armenia"

class OSMProcessor:
    def __init__(self, folder):
        self.data = {}  # Dictionary to store GeoDataFrames for each feature type
        self.area = None
        self.boundary_gdf = None
        self.feature_selections = {}  # To store which features and tags were selected
        self.base_output_folder = folder

        self.data_service = OSMDataService()
        self.heatmap_service = HeatmapService()
        self.network_service = StreetNetworkService()

        self.create_initial_widgets()
        self.display_widgets()

    #### INITIAL WIDGETS ####
    def create_progress_callback(self, output_widget):
        """
        Create a progress callback function that writes to a specific output widget.
        
        Parameters:
            output_widget (ipywidgets.Output): Widget where progress messages will be displayed
            
        Returns:
            function: A callback function that can be passed to methods requiring progress updates
        """
        def progress_callback(message):
            with output_widget:
                print(message)
        
        return progress_callback

    def create_initial_widgets(self):
        """
        Create all initial widgets for the user interface.
        This includes location input, area selection, workflow options, and data collection controls.
        """
        
        self.output_folder_display = widgets.HTML(
            value="<b>Output Folder:</b> Not selected yet",
            layout=Layout(width='80%')
        )
        
        # self.select_folder_button = widgets.Button(
        #     description='Select Output Folder',
        #     button_style='info',
        #     tooltip='Click to browse and select a folder for all outputs',
        #     layout=Layout(width='20%')
        # )
        # self.select_folder_button.on_click(self.on_select_folder_clicked)
        
        # self.folder_status = widgets.Output()


        # Step 1: Location input
        self.location_input = widgets.Text(
            value=default_area,
            placeholder='Enter location (e.g., "Ghent, Belgium")',
            description='Location:',
            layout=Layout(width='70%')
        )
        
        # Add radio buttons for area selection method
        self.area_method = widgets.RadioButtons(
            options=['Enter Location Name', 'Upload Custom Area'],
            description='Area Method:',
            layout=Layout(width='50%')
        )
        self.area_method.observe(self.on_area_method_changed, names='value')
        
        # Container for custom area upload
        self.custom_area_container = widgets.Output()
        
        # Create file upload widget (initially hidden)
        self.file_upload = widgets.FileUpload(
            accept='.geojson,.json,.shp,.zip',  # Accept GeoJSON and Shapefile (as zip)
            multiple=False,
            description='Upload:',
            layout=Layout(width='70%')
        )
        
        self.get_location = widgets.Button(
            description='Set Location',
            button_style='primary', 
            tooltip='Click to set this location for data collection',
            layout=Layout(width='20%')
        )
        self.get_location.on_click(self.on_get_location_clicked)
        
        # Status output
        self.status_output = widgets.Output()
        
        # Step 2: Workflow selection
        self.workflow_selector = widgets.RadioButtons(
            options=['Heatmap Generation', 'Gather Street Network', 'Custom (DEPRECATED - functionality may not work fully)'],
            description='Workflow:',
            disabled=True,
            layout=Layout(width='50%')
        )
        self.workflow_selector.observe(self.on_workflow_changed, names='value')
        
        # Container for workflow-specific widgets
        self.workflow_container = widgets.Output()
        
        # Custom workflow widgets (initially hidden)
        # Feature type selection
        self.feature_type_selector = widgets.SelectMultiple(
            options=list(osm_features.keys()),
            description='Feature Types:',
            disabled=True,
            layout=Layout(width='50%', height='200px')
        )
        
        # Tag selection (initially empty)
        self.tag_container = widgets.Output()
        
        # Button to update tag selection based on feature type
        self.update_tags_button = widgets.Button(
            description='Show Tags for Selected Features',
            disabled=True,
            button_style='info',
            tooltip='Show tags for selected feature types'
        )
        self.update_tags_button.on_click(self.on_update_tags_clicked)
        
        # Step 4: Data collection button
        self.collect_data_button = widgets.Button(
            description='Collect OSM Data',
            disabled=True,
            button_style='success',
            tooltip='Collect data for selected features and tags'
        )
        self.collect_data_button.on_click(self.on_collect_data_clicked)
        
        # Results container
        self.results_output = widgets.Output()

    def display_widgets(self):
        """
        Organize and display all widgets in a structured layout.
        Sets up the main UI with steps for location selection, workflow selection, and results display.
        """

        # Set the output folder for the entire session
        folder_box = VBox([
            HTML("<h3>Output Location</h3>"),
            HBox([self.output_folder_display, self.select_folder_button]),
            self.folder_status
        ])

        # Step 1: Location selection with new area selection method
        location_box = VBox([
            HTML("<h3>Step 1: Select Location</h3>"),
            self.area_method,
            HBox([self.location_input, self.get_location]),
            self.custom_area_container,
            self.status_output
        ])
        
        # Step 2: Workflow selection
        workflow_box = VBox([
            HTML("<h3>Step 2: Select Workflow</h3>"),
            self.workflow_selector,
            self.workflow_container
        ])
        
        # Results display
        results_box = VBox([
            HTML("<h3>Results</h3>"),
            self.results_output
        ])
        
        # Main layout
        main_layout = VBox([
            folder_box,
            location_box,
            workflow_box,
            results_box
        ])
        display(main_layout)
    
    def on_area_method_changed(self, change):
        """
        Handle changes in the area selection method radio buttons.
        
        Parameters:
            change (dict): Dictionary containing the new selected value
        """        
        method = change['new']
        
        with self.custom_area_container:
            clear_output()
            
            if method == 'Upload Custom Area':
                # Show file upload widget and instructions
                display(HTML("<p>Upload a GeoJSON file or a zipped Shapefile defining your area of interest:</p>"))
                display(self.file_upload)
                
                # Hide the location input
                self.location_input.layout.display = 'none'
            else:
                # Show the location input
                self.location_input.layout.display = 'block'

    def on_get_location_clicked(self, b):
        """
        Handle the "Set Location" button click event.
        Gets boundary data for the specified location name or processes uploaded boundary files.
        
        Parameters:
            b (Button): The button that was clicked
        """        

        with self.status_output:
            clear_output()
            
            if self.area_method.value == 'Enter Location Name':
                print(f"Setting location to: {self.location_input.value}...")
                
                try:
                    self.area = self.location_input.value
                    
                    # Get boundary polygon for the area to confirm it exists
                    self.boundary_gdf = ox.geocode_to_gdf(self.area)
                    
                    # Enable workflow selection once location is confirmed
                    self.workflow_selector.disabled = False
                    
                    with self.status_output:
                        clear_output()
                        print(f"✓ Location set to: {self.area}")
                        print("Now select a workflow in Step 2.")
                
                except Exception as e:
                    with self.status_output:
                        clear_output()
                        print(f"❌ Error: {str(e)}")
                        print("Unable to find this location. Please try a different place name or format.")
            
            else:  # Upload Custom Area
                print("Processing uploaded file...")
                
                if not self.file_upload.value:
                    print("❌ Error: No file uploaded. Please upload a GeoJSON or Shapefile.")
                    return
                
                try:
                    # Process the uploaded file based on its type
                    # Handle the file_upload value correctly
                    uploaded_file = self.file_upload.value[0]  # Get the first uploaded file
                    filename = uploaded_file.name
                    content = uploaded_file.content
                    
                    # Create a temporary file
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                        temp_file.write(content)
                        temp_path = temp_file.name
                    
                    # Load the file into a GeoDataFrame
                    if filename.endswith('.geojson') or filename.endswith('.json'):
                        self.boundary_gdf = gpd.read_file(temp_path)
                    elif filename.endswith('.zip'):
                        # For shapefiles in a zip
                        import zipfile
                        
                        # Extract to a temporary directory
                        temp_dir = tempfile.mkdtemp()
                        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                        
                        # Find the .shp file
                        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
                        if not shp_files:
                            raise ValueError("No .shp file found in the zip archive")
                        
                        # Set the shapefile restoration environment variable
                        import os
                        os.environ['SHAPE_RESTORE_SHX'] = 'YES'
                        
                        shp_path = os.path.join(temp_dir, shp_files[0])
                        self.boundary_gdf = gpd.read_file(shp_path)
                    elif filename.endswith('.shp'):
                        # Direct shapefile upload 
                        import os
                        os.environ['SHAPE_RESTORE_SHX'] = 'YES'
                        self.boundary_gdf = gpd.read_file(temp_path)
                    else:
                        raise ValueError("Unsupported file format. Please upload a GeoJSON or Shapefile (zipped).")
                    
                    # Ensure the CRS is EPSG:4326 (WGS84) for compatibility with OSM
                    if self.boundary_gdf.crs is None:
                        # If no CRS is defined, assume it's already in WGS84
                        self.boundary_gdf.set_crs(epsg=4326, inplace=True)
                        print("  ↳ No CRS found in file, assuming WGS84 (EPSG:4326)")
                    elif self.boundary_gdf.crs != "EPSG:4326":
                        # Convert to WGS84
                        original_crs = self.boundary_gdf.crs
                        self.boundary_gdf = self.boundary_gdf.to_crs(epsg=4326)
                        print(f"  ↳ Converted CRS from {original_crs} to WGS84 (EPSG:4326)")
                    
                    # Clean up temporary file
                    os.unlink(temp_path)
                    
                    # Set a name for the area based on the filename
                    self.area = os.path.splitext(filename)[0]
                    
                    # Validate the boundary
                    if self.boundary_gdf is None or len(self.boundary_gdf) == 0:
                        raise ValueError("The file does not contain valid geometry data.")
                    
                    # Enable workflow selection
                    self.workflow_selector.disabled = False
                    
                    with self.status_output:
                        clear_output()
                        print(f"✓ Custom area loaded from: {filename}")
                        print(f"  - Contains {len(self.boundary_gdf)} geometry features")
                        print(f"  - CRS: {self.boundary_gdf.crs}")
                        print("Now select a workflow in Step 2.")
                
                except Exception as e:
                    with self.status_output:
                        clear_output()
                        print(f"❌ Error processing file: {str(e)}")
                        import traceback
                        traceback.print_exc()

    def update_directory_list(self):
        """Update the directory selector dropdown with current directories"""
        import os
        
        try:
            # Get directories in current path
            dirs = ['..'] + [d for d in os.listdir(self.current_path) 
                        if os.path.isdir(os.path.join(self.current_path, d))]
            # Sort directories (keep '..' at the beginning)
            sorted_dirs = ['..'] + sorted([d for d in dirs if d != '..'])
            self.directory_selector.options = sorted_dirs
            
            # Update the path display
            self.path_display.value = f"<b>Current Path:</b> {self.current_path}"
        except Exception as e:
            with self.folder_status:
                clear_output()
                print(f"Error reading directory: {str(e)}")

    def on_select_folder_clicked(self, b):
        """
        Open a folder selection dialog and set the chosen folder as the output location.
        
        Parameters:
            b (Button): The button that was clicked
        """
        with self.folder_status:
            clear_output()
            
            try:
                # Import modules for folder selection
                import tkinter as tk
                from tkinter import filedialog
                
                # Hide the main Tkinter window
                root = tk.Tk()
                root.withdraw()
                
                # Open the folder selection dialog
                folder_path = filedialog.askdirectory(title="Select Output Folder")
                
                # Check if a folder was selected
                if folder_path:
                    # Store the selected path
                    self.base_output_folder = folder_path
                    
                    # Update the display
                    self.output_folder_display.value = f"<b>Output Folder:</b> {self.base_output_folder}"
                    
                    print(f"✓ Output folder set to: {self.base_output_folder}")
                    print(f"All results will be saved to this location.")
                else:
                    print("No folder selected. Using default locations.")
                    
            except Exception as e:
                print(f"❌ Error selecting folder: {str(e)}")
                print("If you're running in a hosted Jupyter environment (like Google Colab), folder selection dialogs may not work.")
                print("You may need to upload and mount your drive instead.")


    #### WORKFLOW EXEXUTION AND STEPS ####
    def on_workflow_changed(self, change):

        """
        Handle workflow selection change events.
        Configures the interface based on the selected workflow type.
        
        Parameters:
            change (dict): Dictionary containing the new selected value
        """

        workflow = change['new']
        
        # Clear previous workflow content
        with self.workflow_container:
            clear_output()
            
            if workflow == 'Heatmap Generation':
                self.setup_heatmap_workflow()
            elif workflow == 'Gather Street Network':
                self.setup_street_network_workflow()
            elif workflow == 'Custom':
                self.setup_custom_workflow()

    ## MAIN WORKFLOW STEPS ##
    def setup_heatmap_workflow(self):
        """
        Set up the interface for the heatmap generation workflow.
        Creates widgets for template selection and category definition.
        """

        with self.workflow_container:
            print("Initializing Heatmap Workflow...")
            
            # Create category selection interface
            category_selection = widgets.RadioButtons(
                options=['Use Template Categories', 'Define Custom Categories'],
                description='Categories:',
                layout=Layout(width='70%')
            )
            
            # Add template selector dropdown (initially hidden)
            template_selector = widgets.Dropdown(
                options=list(all_templates.keys()),
                description='Template:',
                disabled=False,
                layout=Layout(width='60%')
            )
            
            # Container for template selection
            template_container = widgets.Output()
            
            # Button to start the process
            start_button = widgets.Button(
                description='Start Heatmap Process',
                button_style='success',
                layout=Layout(width='30%')
            )
            # Container for category definition widgets
            category_container = widgets.Output()
            
            # Handle category selection change
            def on_category_selection_change(change):
                with category_container:
                    clear_output()
                    if change['new'] == 'Use Template Categories':
                        print("Select a template to use for category definitions:")
                        display(template_selector)
                    else:
                        print("You'll be able to define custom categories after data collection.")

            category_selection.observe(on_category_selection_change, names='value')

            # Handle start button click - modified to use HeatmapService
            def on_start_heatmap(b):
                with self.results_output:
                    clear_output()
                    print(f"Starting heatmap data collection for {self.area}...")
                    print("Collecting 'amenity' and 'shop' data automatically...")
                
                # Define tags to collect automatically for heatmap
                self.feature_selections = {
                    'amenity': osm_features.get('amenity', []),
                    'shop': osm_features.get('shop', [])
                }
                
                try:
                    # Clear existing data
                    self.data = {}
                    total_features = 0
                    
                    # Create a progress callback for the results output
                    progress_callback = self.create_progress_callback(self.results_output)
                    
                    # Determine the appropriate query target based on area method
                    if self.area_method.value == 'Enter Location Name':
                        # Use the place name
                        query_target = self.area
                    else:
                        # Use the polygon
                        query_target = self.boundary_gdf.unary_union
                    
                    # Process each feature type using the data service
                    for feature_type, selected_tags in self.feature_selections.items():
                        try:
                            # Fetch data using the OSMDataService
                            gdf = self.data_service.fetch_osm_data(
                                query_target,
                                feature_type,
                                selected_tags,
                                progress_callback=progress_callback,
                                convert_polygons_to_points=True  # Always convert polygons to points for heatmaps
                            )
                            
                            # Store in the data dictionary if we got results
                            if gdf is not None and len(gdf) > 0:
                                # Store the processed data
                                self.data[feature_type] = gdf
                                total_features += len(gdf)
                                
                                with self.results_output:
                                    print(f"✓ Processed {len(gdf)} {feature_type} features")
                            else:
                                with self.results_output:
                                    print(f"No {feature_type} features found.")
                        
                        except Exception as e:
                            with self.results_output:
                                print(f"Error fetching {feature_type} data: {str(e)}")
                    
                    with self.results_output:
                        print("\n--- DATA COLLECTION COMPLETE ---")
                        print(f"Total features: {total_features}")
                        
                        # Now show the category definition interface based on user's choice
                        if category_selection.value == 'Use Template Categories':
                            print("\nUsing selected template categories...")
                            # Load the selected template
                            selected_template = template_selector.value
                            if selected_template in all_templates:
                                self.categories = all_templates[selected_template]
                                print(f"Loaded template: {selected_template} with {len(self.categories)} category groups")
                                
                                # Now use the HeatmapService to process the data with the template categories
                                self.process_data_with_template()
                            else:
                                print("No template selected or template not found.")
                        else:
                            print("\nSetting up custom category definition interface...")
                            self.on_heatmap_clicked(None)
                
                except Exception as e:
                    with self.results_output:
                        print(f"Error in heatmap workflow: {str(e)}")
                        import traceback
                        traceback.print_exc()
            
            start_button.on_click(on_start_heatmap)
            
            # Display the widgets
            display(VBox([
                HTML("<h4>Heatmap Generation Workflow</h4>"),
                HTML("<p>This workflow will automatically collect amenity and shop data for your selected area, then help you create density heatmaps.</p>"),
                category_selection,
                start_button,
                category_container
            ]))

    def setup_street_network_workflow(self):
        """
        Set up the interface for the street network analysis workflow.
        Creates widgets for network type selection and processing options.
        """

        with self.workflow_container:
            display(HTML("<h4>Street Network Workflow</h4>"))
            display(HTML("<p>This feature will collect and analyze the street network for your selected area.</p>"))
            
            # Street network parameters
            network_type = widgets.Dropdown(
                options=['drive'],
                value='drive',
                description='Network Type:',
                layout=Layout(width='50%')
            )
            
            # simplify = widgets.Checkbox(
            #     value=True,
            #     description='Simplify Network',
            #     tooltip='Simplify network topology',
            #     layout=Layout(width='50%')
            # )
            
            start_button = widgets.Button(
                description='Get Street Network',
                button_style='success',
                layout=Layout(width='30%')
            )
            
            def on_get_network(b):
                with self.results_output:
                    clear_output()
                    print(f"Fetching street network for {self.area}...")
                    
                    try:
                        # For highway data, we want to get all highway types
                        feature_type = 'highway'
                        
                        # Get a list of common highway types in OSM
                        common_highway_types = [
                            'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 
                            'service', 'motorway_link', 'trunk_link', 'primary_link', 'secondary_link',
                            'tertiary_link', 'unclassified', 'road', 'living_street', 'pedestrian',
                            'footway', 'cycleway', 'path', 'track'
                        ]
                        
                        # Create a progress callback for status updates
                        progress_callback = self.create_progress_callback(self.results_output)
                        
                        # Determine the appropriate query target based on area method
                        if self.area_method.value == 'Enter Location Name':
                            query_target = self.area
                            print(f"Getting highway data using place name: {self.area}")
                        else:
                            query_target = self.boundary_gdf.unary_union
                            print(f"Getting highway data using custom boundary")
                        
                        # Fetch highway data using the data service
                        gdf = self.data_service.fetch_osm_data(
                            query_target,
                            feature_type,
                            common_highway_types,
                            progress_callback=progress_callback,
                            convert_polygons_to_points=False  # Keep original line geometries for streets
                        )
                        
                        # Check if we got any data
                        if gdf is None or len(gdf) == 0:
                            print("No highway data found for the specified area.")
                            return
                            
                        print(f"Retrieved {len(gdf)} highway features")
                        
                        # Process the street network using the StreetNetworkService
                        network_results = self.network_service.process_street_network(
                            gdf, 
                            self.base_output_folder,
                            self.area, 
                            progress_callback
                        )
                        
                        if network_results:
                            # Store the results
                            self.street_network = network_results['raw_network']
                            self.processed_street_network = network_results['processed_network']
                            
                            # Analyze network statistics
                            stats = self.network_service.analyze_network_statistics(
                                self.street_network,
                                self.processed_street_network,
                                progress_callback
                            )
                            
                            # Display some statistics
                            if stats and 'raw' in stats:
                                print("\n--- STREET NETWORK STATISTICS ---")
                                print(f"Total segments: {stats['raw']['segment_count']}")
                                print(f"Total length: {stats['raw']['total_length_km']:.2f} km")
                                print(f"Average segment length: {stats['raw']['avg_segment_length_m']:.2f} meters")
                            
                            # Add visualization button
                            vis_button = widgets.Button(
                                description='Visualize Network',
                                button_style='info',
                                layout=Layout(width='150px')
                            )
                            
                            def visualize_network(b):
                                with self.results_output:
                                    clear_output()
                                    
                                    # Get the centroid for map center
                                    centroid = self.boundary_gdf.unary_union.centroid
                                    center = (centroid.y, centroid.x)
                                    
                                    # Create the map using the StreetNetworkService
                                    m = self.network_service.create_network_map(
                                        self.street_network,
                                        self.processed_street_network,
                                        center=center,
                                        progress_callback=progress_callback
                                    )
                                    
                                    # Display the map
                                    display(m)
                            
                            vis_button.on_click(visualize_network)
                            # display(vis_button)
                            
                    except Exception as e:
                        print(f"Error fetching street network: {str(e)}")
                        import traceback
                        traceback.print_exc()
            
            start_button.on_click(on_get_network)
            
            display(VBox([
                network_type,
                # simplify,
                start_button
            ]))
    
    def setup_custom_workflow(self):
        """
        Set up the interface for the custom data collection workflow.
        Enables feature and tag selection for specific OpenStreetMap data.
        """

        with self.workflow_container:
            # Step 2 & 3: Feature and tag selection
            feature_tag_box = VBox([
                HTML("<h4>Custom Data Collection Workflow</h4>"),
                HTML("<p>Select specific feature types and tags to collect from OpenStreetMap.</p>"),
                HTML("<h5>Step 1: Select Feature Types</h5>"),
                self.feature_type_selector,
                self.update_tags_button,
                HTML("<h5>Step 2: Select Tags for Each Feature Type</h5>"),
                self.tag_container,
                HTML("<h5>Step 3: Collect Data</h5>"),
                self.collect_data_button
            ])
            
            # Enable the feature selector for custom workflow
            self.feature_type_selector.disabled = False
            self.update_tags_button.disabled = False
            
            display(feature_tag_box)
    
    ## ADDITIONAL WORKFLOW HELPERS AND WIDGETS ##
    def on_update_tags_clicked(self, b):
        """
        Handle the "Show Tags for Selected Features" button click event.
        Creates tag selection widgets based on selected feature types.
        
        Parameters:
            b (Button): The button that was clicked
        """
        
        selected_features = self.feature_type_selector.value
        
        if not selected_features:
            with self.tag_container:
                clear_output()
                print("Please select at least one feature type first.")
            return
        
        # Create tag selectors for each selected feature type
        with self.tag_container:
            clear_output()
            
            # Container to store all tag selector widgets
            self.tag_selectors = {}
            self.select_all_buttons = {}
            
            for feature_type in selected_features:
                print(f"\n--- {feature_type.upper()} TAGS ---")
                
                # Create a multi-select widget for this feature's tags
                tag_selector = widgets.SelectMultiple(
                    options=osm_features.get(feature_type, []),
                    description=f'{feature_type}:',
                    layout=Layout(width='90%', height='150px')
                )
                
                # Add a "Select All" button for this feature type
                select_all_button = widgets.Button(
                    description='Select All',
                    layout=Layout(width='100px')
                )
                
                # Create a closure to capture the current feature_type and tag_selector
                def create_select_all_handler(feature_type, tag_selector):
                    def select_all_handler(b):
                        tag_selector.value = tag_selector.options
                    return select_all_handler
                
                select_all_button.on_click(create_select_all_handler(feature_type, tag_selector))
                
                # Store the widgets in dictionaries for later access
                self.tag_selectors[feature_type] = tag_selector
                self.select_all_buttons[feature_type] = select_all_button
                
                # Display the widgets
                display(HBox([tag_selector, select_all_button]))
        
        # Enable the collect data button
        self.collect_data_button.disabled = False

    def on_collect_data_clicked(self, b):
        """
        Handle the "Collect OSM Data" button click event.
        Fetches OpenStreetMap data for selected feature types and tags.
        
        Parameters:
            b (Button): The button that was clicked
        """

        with self.results_output:
            clear_output()
            print("Collecting OSM data...")
            
        try:
            # Get all selected feature types and their tags
            selected_features = self.feature_type_selector.value
            
            if not selected_features:
                with self.results_output:
                    clear_output()
                    print("Please select at least one feature type.")
                return
            
            # Check if tags are selected for each feature type
            self.feature_selections = {}
            for feature_type in selected_features:
                if feature_type not in self.tag_selectors:
                    continue
                    
                selected_tags = self.tag_selectors[feature_type].value
                if not selected_tags:
                    with self.results_output:
                        print(f"Warning: No tags selected for {feature_type}. Skipping...")
                    continue
                
                self.feature_selections[feature_type] = list(selected_tags)
            
            if not self.feature_selections:
                with self.results_output:
                    clear_output()
                    print("Please select at least one tag for at least one feature type.")
                return
            
            # Clear existing data
            self.data = {}
            
            # Get the polygon for querying
            polygon = self.boundary_gdf.unary_union
            
            # Collect data for each feature type
            total_features = 0
            for feature_type, selected_tags in self.feature_selections.items():
                with self.results_output:
                    print(f"Fetching {feature_type} data with {len(selected_tags)} tags...")
                
                # Create a tags dictionary for OSMnx
                tags = {feature_type: selected_tags}
                
                try:
                    # Fetch the data using polygon instead of place name
                    try:
                        # First attempt with standard method
                        gdf = ox.features_from_polygon(polygon, tags=tags)
                    except Exception as e:
                        # If error contains indication of query being too large
                        if "too long" in str(e).lower() or "bad request" in str(e).lower():
                            # Try with the tiled approach
                            gdf = self.fetch_data_by_tiles(polygon, feature_type, selected_tags)
                        else:
                            # If it's some other error, re-raise it
                            raise e
                                
                    # Store in the data dictionary
                    if gdf is not None and len(gdf) > 0:
                        # Special processing for amenity polygons - convert to points
                        if feature_type in ['amenity', 'shop']:
                            # Identify polygons and multipolygons
                            polygon_mask = gdf.geometry.apply(lambda geom: 
                                geom.geom_type == 'Polygon' or geom.geom_type == 'MultiPolygon')
                            
                            if polygon_mask.any():
                                # Number of polygons to convert
                                num_polygons = polygon_mask.sum()
                                
                                # Convert polygons to centroid points
                                gdf.loc[polygon_mask, 'geometry'] = gdf.loc[polygon_mask, 'geometry'].centroid
                                
                                with self.results_output:
                                    print(f"  ↳ Converted {num_polygons} polygons to points for {feature_type} features")
                        
                        self.data[feature_type] = gdf
                        total_features += len(gdf)
                        with self.results_output:
                            print(f"✓ Found {len(gdf)} {feature_type} features")
                    else:
                        with self.results_output:
                            print(f"No {feature_type} features found.")
                
                except Exception as e:
                    with self.results_output:
                        print(f"Error fetching {feature_type} data: {str(e)}")
            
            # Display summary of collected data
            with self.results_output:
                print("\n--- DATA COLLECTION SUMMARY ---")
                print(f"Location: {self.area}")
                print(f"Total feature types: {len(self.data)}")
                print(f"Total features: {total_features}")
                
                # Add single export button for all data
                if self.data:
                    print("\n--- EXPORT OPTIONS ---")
                    export_pkl_button = widgets.Button(
                        description=f'Export All Data as Pickle ({sum(len(gdf) for gdf in self.data.values())} features)',
                        button_style='info',
                        layout=Layout(width='300px')
                    )
                    
                    def export_pkl_handler(b):
                        import pickle
                        import os
                        folder_name = self.area.replace(', ', '_').replace(' ', '_')
                        os.makedirs(folder_name, exist_ok=True)
                        filename = os.path.join(folder_name, "all_data.pkl")

                        with open(filename, 'wb') as f:
                            pickle.dump(self.data, f)
                        print(f"All data exported to {filename}")
                        print(f"Data structure: dictionary with {len(self.data)} keys: {list(self.data.keys())}")
                        print("Example access: data['amenity'] for amenity features")

                    export_pkl_button.on_click(export_pkl_handler)
                    display(export_pkl_button)
                    
                    export_gdf_button = widgets.Button(
                        description=f'Export Each Feature Type as GDF ({len(self.data)} feature type(s))',
                        button_style='info',
                        layout=Layout(width='300px')
                    )
                    
                    def export_gdf_handler(b):
                        
                        # Create a folder with the self.area name, if not exists
                        import os
                        folder_name = self.area.replace(', ', '_').replace(' ', '_')
                        os.makedirs(folder_name, exist_ok=True)

                        for feature_type, gdf in self.data.items():
                            filename = os.path.join(folder_name, f"{feature_type}.geojson")
                            gdf.to_file(filename, driver='GeoJSON')
                            print(f"✓ {feature_type} data exported to {filename}")

                    export_gdf_button.on_click(export_gdf_handler)
                    display(export_gdf_button)

                    # Add a preview data button
                    preview_button = widgets.Button(
                        description='Preview Data on Map',
                        button_style='warning',
                        layout=Layout(width='300px')
                    )
                    preview_button.on_click(self.on_preview_clicked)
                    display(preview_button)

                    print("\n--- ANALYSIS OPTIONS ---")

                    heatmap_button = widgets.Button(
                        description='Generate Heatmaps per Category',
                        button_style='warning',
                        layout=Layout(width='300px')
                    )
                    heatmap_button.on_click(self.on_heatmap_clicked)
                    display(heatmap_button)

        except Exception as e:
            with self.results_output:
                print(f"Error: {str(e)}")
    
    def on_preview_clicked(self, b):
        """
        Handle the "Preview Data on Map" button click event.
        Creates an interactive map showing all collected data.
        
        Parameters:
            b (Button): The button that was clicked
        """
       
        with self.results_output:
            print("\nPreparing map preview...")
            
            if not self.data:
                print("No data to preview.")
                return
            
            # Determine the center of the map using the boundary
            if self.boundary_gdf is not None:
                centroid = self.boundary_gdf.unary_union.centroid
                map_center = [centroid.y, centroid.x]
            else:
                # Use the centroid of the first dataset if no boundary
                first_gdf = list(self.data.values())[0]
                centroid = first_gdf.unary_union.centroid
                map_center = [centroid.y, centroid.x]
            
            # Create the map
            m = folium.Map(location=map_center, zoom_start=12)
            
            # Add each feature type with a different color
            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
                      'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 
                      'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightred']
            
            for i, (feature_type, gdf) in enumerate(self.data.items()):
                color = colors[i % len(colors)]
                
                # Create a feature group for this layer so it can be toggled
                feature_group = folium.FeatureGroup(name=feature_type)
                
                # Add a marker cluster for points
                marker_cluster = MarkerCluster().add_to(feature_group)
                
                # Process each feature
                for idx, row in gdf.iterrows():
                    # Skip if no geometry
                    if not row.geometry:
                        continue
                        
                    # Create popup content
                    popup_content = f"<b>Type:</b> {feature_type}<br>"
                    if 'name' in row and row['name']:
                        popup_content += f"<b>Name:</b> {row['name']}<br>"
                    
                    # Add relevant tags
                    if feature_type in row:
                        popup_content += f"<b>{feature_type}:</b> {row[feature_type]}<br>"
                    
                    # Add different geometry types
                    if row.geometry.geom_type == 'Point':
                        folium.Marker(
                            [row.geometry.y, row.geometry.x],
                            popup=folium.Popup(popup_content, max_width=300),
                            icon=folium.Icon(color=color)
                        ).add_to(marker_cluster)
                    
                    elif row.geometry.geom_type in ['LineString', 'MultiLineString']:
                        # Simplify geometry for better performance
                        simplified = row.geometry.simplify(0.0001)
                        if not simplified.is_empty:
                            folium.GeoJson(
                                simplified.__geo_interface__,
                                popup=folium.Popup(popup_content, max_width=300),
                                style_function=lambda x, color=color: {
                                    'color': color,
                                    'weight': 3,
                                    'opacity': 0.7
                                }
                            ).add_to(feature_group)
                    
                    elif row.geometry.geom_type in ['Polygon', 'MultiPolygon']:
                        # Simplify geometry for better performance
                        simplified = row.geometry.simplify(0.0001)
                        if not simplified.is_empty:
                            folium.GeoJson(
                                simplified.__geo_interface__,
                                popup=folium.Popup(popup_content, max_width=300),
                                style_function=lambda x, color=color: {
                                    'fillColor': color,
                                    'color': color,
                                    'weight': 2,
                                    'fillOpacity': 0.4
                                }
                            ).add_to(feature_group)
                
                # Add the feature group to the map
                feature_group.add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Display the map
            display(m)

    def process_data_with_template(self):
        """
        Process collected data using predefined template categories.
        Categorizes points of interest based on the selected template.
        """

        if not hasattr(self, 'categories') or not self.categories:
            with self.results_output:
                print("Error: No template categories loaded.")
            return
        
        # Create a progress callback for the results output
        progress_callback = self.create_progress_callback(self.results_output)
        
        # Use the heatmap service to prepare and categorize the data
        if 'amenity' in self.data or 'shop' in self.data:
            amenity_gdf = self.data.get('amenity')
            shop_gdf = self.data.get('shop')
            
            # Use our HeatmapService to prepare the heatmap data
            self.heatmap_data = self.heatmap_service.prepare_heatmap_data(
                amenity_gdf, shop_gdf, progress_callback
            )
            
            if self.heatmap_data is not None and len(self.heatmap_data) > 0:
                # Use our HeatmapService to categorize the data with the template
                self.heatmap_data = self.heatmap_service.categorize_facilities(
                    self.heatmap_data, self.categories, progress_callback
                )
                
                with self.results_output:
                    print(f"Data processed with template categories: {len(self.heatmap_data)} points categorized")
                    print(f"Found {self.heatmap_data['category'].nunique()} unique categories")
                    
                    # Display the heatmap generation interface
                    self.show_heatmap_generation_interface()
            else:
                with self.results_output:
                    print("No data to process.")
        else:
            with self.results_output:
                print("No amenity or shop data available for heatmap processing.")
                
    def show_heatmap_generation_interface(self):
        """
        Display the interface for generating heatmaps after data categorization.
        Creates widgets for setting output folder, cell size, bandwidth, and category selection.
        """

        with self.results_output:
            display(HTML("<h4>Generate Heatmap Density Rasters</h4>"))
            
            # Create widgets for heatmap parameters
            # Folder path for output
            new_output_path = widgets.Text(
                value=f"{self.area.replace(', ', '_').replace(' ', '_')}_heatmaps",
                placeholder='Enter output folder path',
                description='Output folder:',
                layout=Layout(width='70%')
            )
            
            output_folder = os.path.join(self.base_output_folder, new_output_path.value.strip())

            # Cell size parameter (with reasonable defaults)
            cell_size = widgets.FloatText(
                value=0.001,
                description='Cell size:',
                tooltip='Size of each cell in raster (in degrees). Lower = higher resolution but slower processing',
                min=0.0001,
                max=0.01,
                step=0.0001,
                layout=Layout(width='40%')
            )
            
            # Bandwidth parameter
            bandwidth = widgets.FloatText(
                value=0.1,
                description='Bandwidth:',
                tooltip='KDE bandwidth parameter. Lower = more detailed but may be noisier',
                min=0.01,
                max=1.0,
                step=0.01,
                layout=Layout(width='40%')
            )
            
            # Category selection (multi-select)
            category_selector = widgets.SelectMultiple(
                options=sorted(self.heatmap_data['category'].unique()),
                description='Categories:',
                tooltip='Select specific categories to process (leave empty for all)',
                layout=Layout(width='50%', height='150px')
            )
            
            # Add "Select All" button for categories
            select_all_cats_button = widgets.Button(
                description='Select All',
                layout=Layout(width='100px')
            )
            
            def select_all_cats(b):
                category_selector.value = category_selector.options
            
            select_all_cats_button.on_click(select_all_cats)
            
            # Generate button
            generate_button = widgets.Button(
                description='Generate Heatmaps',
                button_style='success',
                tooltip='Generate and save heatmap rasters for all categories',
                layout=Layout(width='200px')
            )
            
            # Set up the generate button to call our new generate_heatmaps method
            generate_button.on_click(lambda b: self.generate_heatmaps(
                b, output_folder, cell_size, bandwidth, category_selector
            ))
            
            # Display the widgets
            display(widgets.VBox([
                widgets.HBox([new_output_path]),
                widgets.HBox([cell_size, bandwidth]),
                widgets.HBox([category_selector, select_all_cats_button]),
                generate_button
            ]))

    def generate_heatmaps(self, b, output_folder, cell_size, bandwidth, category_selector):
        """
        Generate density heatmaps based on the specified parameters.
        
        Parameters:
            b (Button): The button that was clicked
            output_folder (Text): Widget containing the output folder path
            cell_size (FloatText): Widget containing the cell size value
            bandwidth (FloatText): Widget containing the bandwidth value
            category_selector (SelectMultiple): Widget containing selected categories
        """        
        
        with self.results_output:
            clear_output()
            
            # Check the output folder
            folder_path = output_folder
            if not folder_path:
                print("Error: Please enter a valid output folder path")
                return
            
            # Get selected categories or use all if none selected
            selected_categories = list(category_selector.value)
            if not selected_categories:
                selected_categories = self.heatmap_data['category'].unique()
                print(f"No specific categories selected, processing all {len(selected_categories)} categories")
            else:
                print(f"Processing {len(selected_categories)} selected categories")

            try:
                # Create a progress callback for the results output
                progress_callback = self.create_progress_callback(self.results_output)
                
                # Use the HeatmapService to generate the heatmaps
                results = self.heatmap_service.generate_heatmaps(
                    self.heatmap_data,
                    folder_path,
                    cell_size=cell_size.value,
                    bandwidth=bandwidth.value,
                    selected_categories=selected_categories,
                    progress_callback=progress_callback
                )
                
                if results:
                    # Create and display a visualization of the first few rasters
                    try:
                        # Use the HeatmapService to create previews
                        self.heatmap_service.create_heatmap_preview(
                            folder_path, 
                            selected_categories,
                            progress_callback
                        )
                        
                    except Exception as e:
                        print(f"Could not create previews: {str(e)}")
                    
                    # Add a button to open the visualization tool
                    viz_button = widgets.Button(
                        description='Visualize Generated Heatmaps',
                        button_style='info',
                        layout=Layout(width='250px')
                    )
                    
                    def show_visualization(b):
                        # Add the visualization component
                        viz_output = self.add_heatmap_visualization()
                        display(viz_output)
                    
                    viz_button.on_click(show_visualization)
                    display(viz_button)
                    
            except Exception as e:
                print(f"Error generating heatmaps: {str(e)}")
                import traceback
                traceback.print_exc()

    def on_heatmap_clicked(self, b):
        """
        Handle the "Generate Heatmaps per Category" button click event.
        Prepares data for heatmap analysis and displays the category grouping interface.
        
        Parameters:
            b (Button): The button that was clicked
        """

        
        with self.results_output:
            clear_output()
            print("Preparing data for heatmap analysis...")
            
            # Check if we have amenity or shop data
            if 'amenity' not in self.data and 'shop' not in self.data:
                print("Error: Heatmap requires 'amenity' or 'shop' data. Please collect this data first.")
                return
        
        # Create a progress callback for the results output
        progress_callback = self.create_progress_callback(self.results_output)
        
        # Use the heatmap service to prepare the data
        amenity_gdf = self.data.get('amenity')
        shop_gdf = self.data.get('shop')
        
        # Use HeatmapService to prepare the data for heatmap analysis
        self.heatmap_data = self.heatmap_service.prepare_heatmap_data(
            amenity_gdf, shop_gdf, progress_callback
        )
        
        if self.heatmap_data is not None and len(self.heatmap_data) > 0:
            with self.results_output:
                # Display unique facility types for selection
                unique_facilities = sorted(self.heatmap_data['facility_type'].unique())
                print(f"\nFound {len(unique_facilities)} unique facility types for heatmap analysis:")
                
                # Display the selector
                display(HTML("<h4>Select Facility Types for Heatmap</h4>"))
                
                # Display facility types as before
                facility_types_text = widgets.Textarea(
                    value=", ".join([f"'{facility}'" for facility in unique_facilities]),
                    description="Facility Types:",
                    disabled=False,
                    layout=Layout(width='90%', height='200px')
                )
                
                # Display instructions and the facility types
                display(HTML("<p>The facility types are listed above. You can copy this list for future use.</p>"))
                display(facility_types_text)
                
                # Add the category grouping interface
                self.display_category_grouping_interface()
        else:
            with self.results_output:
                print("No data available for heatmap analysis.")

    def display_category_grouping_interface(self):
        """
        Display the interface for grouping facility types into categories.
        Creates widgets for defining category names and associated facility types.
        """

        with self.results_output:
            display(HTML("<h4>Group Facility Types into Categories</h4>"))
            display(HTML("<p>Create categories and assign facility types to each category.</p>"))
            
            # Container for all category-tag pairs
            category_pairs_container = widgets.VBox([])
            
            # Function to create a new category-tag pair
            def create_category_pair():
                # Category name input
                category_input = widgets.Text(
                    placeholder='Enter category name (e.g., "Urban Living")',
                    description='Category:',
                    layout=Layout(width='30%')
                )
                
                # Tags input
                tags_input = widgets.Textarea(
                    placeholder='Enter tags separated by commas (e.g., "restaurant", "cafe", "bar")',
                    description='Tags:',
                    layout=Layout(width='60%', height='80px')
                )
                
                # Delete button for this pair
                delete_button = widgets.Button(
                    description='🗑️',
                    tooltip='Delete this category',
                    layout=Layout(width='5%')
                )
                
                # Create the horizontal box for this pair
                pair_box = widgets.HBox([
                    category_input, 
                    tags_input, 
                    delete_button
                ])
                
                # Add delete functionality
                def delete_pair(b):
                    # Remove this pair from the container
                    pairs = list(category_pairs_container.children)
                    if pair_box in pairs:
                        pairs.remove(pair_box)
                        category_pairs_container.children = tuple(pairs)
                
                delete_button.on_click(delete_pair)
                
                return pair_box
            
            # Add button for creating new category-tag pairs
            add_button = widgets.Button(
                description='+ Add Category',
                button_style='success',
                tooltip='Add a new category',
                layout=Layout(width='150px')
            )
            
            # Add button functionality
            def add_category(b):
                # Create a new pair and add it to the container
                new_pair = create_category_pair()
                pairs = list(category_pairs_container.children)
                pairs.append(new_pair)
                category_pairs_container.children = tuple(pairs)
            
            add_button.on_click(add_category)
            
            # Create some initial pairs to start with
            for _ in range(3):  # Start with 3 empty pairs
                add_category(None)
                
            save_button = widgets.Button(
                description='Save Categories',
                button_style='primary',
                tooltip='Save the category groupings',
                layout=Layout(width='150px')
            )
            
            # Save button functionality
            def save_categories(b):
                categories = {}
                
                # Collect data from all pairs
                for pair in category_pairs_container.children:
                    category_name = pair.children[0].value.strip()
                    tags_text = pair.children[1].value.strip()
                    
                    # Skip empty categories
                    if not category_name or not tags_text:
                        continue
                    
                    # Process tags: split by commas, strip whitespace and quotes
                    tags = []
                    for tag in tags_text.split(','):
                        tag = tag.strip()
                        # Remove quotes if they exist
                        if (tag.startswith("'") and tag.endswith("'")) or (tag.startswith('"') and tag.endswith('"')):
                            tag = tag[1:-1]
                        if tag:  # Only add non-empty tags
                            tags.append(tag)
                    
                    # Add to categories dictionary
                    if category_name in categories:
                        # Append to existing category
                        categories[category_name].extend(tags)
                    else:
                        # Create new category
                        categories[category_name] = tags
                
                # Save to the class instance
                self.categories = categories

                # Create a progress callback for the results output
                progress_callback = self.create_progress_callback(self.results_output)
                
                # Use the heatmap service to categorize the data
                self.heatmap_data = self.heatmap_service.categorize_facilities(
                    self.heatmap_data, self.categories, progress_callback
                )

                display(HTML("<h4>Categories saved successfully!</h4>"))
                
                # Show the heatmap generation interface
                self.show_heatmap_generation_interface()
            
            save_button.on_click(save_categories)
            
            # Display the category interface
            display(VBox([
                category_pairs_container,
                HBox([add_button, save_button])
            ]))

# Create and display the processor
processor = OSMProcessor()
