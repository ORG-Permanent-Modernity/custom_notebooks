
import ee


def get_imagery(satellite, year, region, start_month, end_month):
    """Get filtered imagery for a specific year and region."""
    return (satellite
            .filterBounds(region)
            .filterDate(f'{year}-{start_month:02d}-01', f'{year}-{end_month:02d}-30')
            .filterMetadata('CLOUD_COVER', 'less_than', 20))


def calculate_index(image, bands, index_name):
    """Calculate normalized difference index."""
    index = image.normalizedDifference(bands).rename(index_name)
    return image.addBands(index)


def calculate_L5_index(image, index_type='NDSI'):
    """Calculate index for Landsat 5."""
    bands = {
        'NDSI': ['SR_B2', 'SR_B5'],
        'NDVI': ['SR_B4', 'SR_B3']
    }
    return calculate_index(image, bands[index_type], index_type)


def calculate_L8_index(image, index_type='NDVI'):
    """Calculate index for Landsat 8."""
    bands = {
        'NDSI': ['SR_B3', 'SR_B6'],
        'NDVI': ['SR_B5', 'SR_B4']
    }
    return calculate_index(image, bands[index_type], index_type)


def calculate_S2_index(image, index_type='NDVI'):
    """Calculate index for Sentinel 2."""

    bands = {
        'NDVI': ['B8', 'B4'],
        'NDSI': ['B3', 'B11'] ### NEED TO DOUBLE CHECK
    }

    return calculate_index(image, bands[index_type], index_type)






def get_cloud_free_composite(image_collection, sensor_type):
    """
    Creates a cloud-free composite from an image collection by masking clouds
    and then creating a median composite of the remaining pixels.
    
    Args:
        image_collection (ee.ImageCollection): The input image collection
        sensor_type (str): 'Sentinel' or 'Landsat' to determine the cloud masking approach
        
    Returns:
        ee.Image: A cloud-free composite image
    """
    # Function to mask clouds in Sentinel-2 imagery
    def mask_clouds_sentinel(image):
        # For Sentinel-2, use the QA60 band for cloud masking
        qa_band = image.select('QA60')
        
        # Bits 10 and 11 are clouds and cirrus
        cloud_bitmask = 1 << 10
        cirrus_bitmask = 1 << 11
        
        # Create a mask for clear conditions (no clouds or cirrus)
        mask = qa_band.bitwiseAnd(cloud_bitmask).eq(0).And(
                qa_band.bitwiseAnd(cirrus_bitmask).eq(0))
        
        # Apply the mask to the image and maintain the original metadata
        return image.updateMask(mask).copyProperties(image, ['system:time_start'])
    
    # Function to mask clouds in Landsat imagery (works for Landsat 4-7)
    def mask_clouds_landsat_457(image):
        # Use the QA band for cloud masking
        qa = image.select('pixel_qa')
        
        # Bit 5: Cloud
        # Bit 6: Cloud Confidence
        # Bit 7: Cloud Shadow
        cloud_shadow = 1 << 7
        clouds = 1 << 5
        
        # Create a mask for clear conditions
        mask = qa.bitwiseAnd(cloud_shadow).eq(0).And(
               qa.bitwiseAnd(clouds).eq(0))
        
        return image.updateMask(mask).copyProperties(image, ['system:time_start'])
    
    # Function to mask clouds in Landsat 8-9 imagery
    def mask_clouds_landsat_89(image):
        # Use the QA_PIXEL band for cloud masking
        qa = image.select('QA_PIXEL')
        
        # Bits 3: Cloud Shadow
        # Bits 4: Snow
        # Bits 5: Cloud
        cloud_shadow = 1 << 3
        snow = 1 << 4
        cloud = 1 << 5
        
        # Create a mask for clear conditions
        mask = qa.bitwiseAnd(cloud_shadow).eq(0).And(
               qa.bitwiseAnd(cloud).eq(0)).And(
               qa.bitwiseAnd(snow).eq(0))
        
        return image.updateMask(mask).copyProperties(image, ['system:time_start'])
    
    # Function to detect which Landsat sensor we're working with
    def detect_landsat_sensor(image_collection):
        # Get the first image to check which bands are available
        first_image = image_collection.first()
        band_names = first_image.bandNames().getInfo()
        
        # Check if QA_PIXEL exists (Landsat 8-9) or pixel_qa (Landsat 4-7)
        if 'QA_PIXEL' in band_names:
            return 'Landsat_89'
        elif 'pixel_qa' in band_names:
            return 'Landsat_457' 
        else:
            raise ValueError("Could not determine Landsat sensor type from band names")
        
    # Apply the appropriate cloud masking based on sensor type
    if sensor_type.lower() == 'sentinel':
        masked_collection = image_collection.map(mask_clouds_sentinel)
    elif sensor_type.lower() == 'landsat':
        # Detect which Landsat sensor we're using
        landsat_sensor = detect_landsat_sensor(image_collection)
        
        if landsat_sensor == 'Landsat_89':
            masked_collection = image_collection.map(mask_clouds_landsat_89)
        else:  # Landsat_457
            masked_collection = image_collection.map(mask_clouds_landsat_457)
    else:
        raise ValueError("sensor_type must be either 'Sentinel' or 'Landsat'")
    
    # Create a median composite from the masked collection
    # Median helps to further reduce any remaining cloud influence
    composite = masked_collection.median()
    
    return composite


def get_mean_composite(image_collection):
    """
    Creates a mean value composite from an image collection by averaging
    all pixel values across the time series.
    
    Args:
        image_collection (ee.ImageCollection): The input image collection
        
    Returns:
        ee.Image: A mean value composite image
    """
    
    # Calculate the mean across all images in the collection
    composite = image_collection.mean()
    
    return composite


def get_least_cloudy_image(image_collection, sensor_type):
    """
    Returns the single least cloudy image from an image collection.
    
    Args:
        image_collection (ee.ImageCollection): The input image collection
        sensor_type (str): 'Sentinel' or 'Landsat' to determine the cloud scoring approach
        
    Returns:
        ee.Image: The least cloudy image from the collection
    """
    # Function to add a cloud score property to Sentinel-2 images
    def add_cloud_score_sentinel(image):
        # For Sentinel-2, use the QA60 band for cloud scoring
        qa_band = image.select('QA60')
        
        # Count the number of pixels with clouds or cirrus
        cloud_bitmask = 1 << 10
        cirrus_bitmask = 1 << 11
        
        # Create a cloud mask (1 where there are clouds, 0 otherwise)
        cloud_mask = qa_band.bitwiseAnd(cloud_bitmask).neq(0).Or(
                       qa_band.bitwiseAnd(cirrus_bitmask).neq(0))
        
        # Calculate the percentage of cloudy pixels
        cloud_percentage = cloud_mask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=image.geometry(),
            scale=100,  # Adjust scale as needed
            maxPixels=1e9
        ).get('QA60')
        
        # Add the cloud percentage as a property
        return image.set('CLOUD_PERCENTAGE', cloud_percentage)
    
    # Function to add a cloud score property to Landsat 4-7 images
    def add_cloud_score_landsat_457(image):
        # Use the QA band for cloud scoring
        qa = image.select('pixel_qa')
        
        # Bits for clouds and shadows
        cloud_shadow = 1 << 7
        clouds = 1 << 5
        
        # Create a cloud mask (1 where there are clouds, 0 otherwise)
        cloud_mask = qa.bitwiseAnd(cloud_shadow).neq(0).Or(
                      qa.bitwiseAnd(clouds).neq(0))
        
        # Calculate the percentage of cloudy pixels
        cloud_percentage = cloud_mask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=image.geometry(),
            scale=30,  # Landsat resolution
            maxPixels=1e9
        ).get('pixel_qa')
        
        # Add the cloud percentage as a property
        return image.set('CLOUD_PERCENTAGE', cloud_percentage)
    
    # Function to add a cloud score property to Landsat 8-9 images
    def add_cloud_score_landsat_89(image):
        # Use the QA_PIXEL band for cloud scoring
        qa = image.select('QA_PIXEL')
        
        # Bits for clouds, shadows, and snow
        cloud_shadow = 1 << 3
        cloud = 1 << 5
        snow = 1 << 4
        
        # Create a cloud mask (1 where there are clouds/shadows/snow, 0 otherwise)
        cloud_mask = qa.bitwiseAnd(cloud_shadow).neq(0).Or(
                      qa.bitwiseAnd(cloud).neq(0)).Or(
                      qa.bitwiseAnd(snow).neq(0))
        
        # Calculate the percentage of cloudy pixels
        cloud_percentage = cloud_mask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=image.geometry(),
            scale=30,  # Landsat resolution
            maxPixels=1e9
        ).get('QA_PIXEL')
        
        # Add the cloud percentage as a property
        return image.set('CLOUD_PERCENTAGE', cloud_percentage)
    
    # Function to detect which Landsat sensor we're working with
    def detect_landsat_sensor(image_collection):
        # Get the first image to check which bands are available
        first_image = image_collection.first()
        band_names = first_image.bandNames().getInfo()
        
        # Check if QA_PIXEL exists (Landsat 8-9) or pixel_qa (Landsat 4-7)
        if 'QA_PIXEL' in band_names:
            return 'Landsat_89'
        elif 'pixel_qa' in band_names:
            return 'Landsat_457' 
        else:
            raise ValueError("Could not determine Landsat sensor type from band names")
    
    # Apply the appropriate cloud scoring function based on sensor type
    if sensor_type.lower() == 'sentinel':
        scored_collection = image_collection.map(add_cloud_score_sentinel)
    elif sensor_type.lower() == 'landsat':
        # Detect which Landsat sensor we're using
        landsat_sensor = detect_landsat_sensor(image_collection)
        
        if landsat_sensor == 'Landsat_89':
            scored_collection = image_collection.map(add_cloud_score_landsat_89)
        else:  # Landsat_457
            scored_collection = image_collection.map(add_cloud_score_landsat_457)
    else:
        raise ValueError("sensor_type must be either 'Sentinel' or 'Landsat'")
    
    # Sort by cloud percentage (ascending)
    sorted_collection = scored_collection.sort('CLOUD_PERCENTAGE')
    
    # Get the first image (least cloudy)
    least_cloudy_image = sorted_collection.first()
    
    return least_cloudy_image

