# Contains all the OSM tags and their respective values that are used in the OSM data

osm_features = {
    'aerialway': [
        'cable_car', 'gondola', 'mixed_lift', 'chair_lift', 'drag_lift',
        't-bar', 'j-bar', 'platter', 'rope_tow', 'magic_carpet',
        'zip_line', 'goods', 'pylon', 'station'
    ],
    
    'aeroway': [
        'aerodrome', 'aircraft_crossing', 'apron', 'gate', 'hangar',
        'helipad', 'heliport', 'navigationaid', 'runway', 'spaceport',
        'taxiway', 'terminal', 'windsock'
    ],
    
    'amenity': [
        # Sustenance
        'bar', 'biergarten', 'cafe', 'fast_food', 'food_court', 'ice_cream',
        'pub', 'restaurant',
        
        # Education
        'college', 'dancing_school', 'driving_school', 'first_aid_school',
        'kindergarten', 'language_school', 'library', 'surf_school',
        'toy_library', 'research_institute', 'training', 'music_school',
        'school', 'traffic_park', 'university',
        
        # Transportation
        'bicycle_parking', 'bicycle_repair_station', 'bicycle_rental',
        'bicycle_wash', 'boat_rental', 'boat_sharing', 'bus_station',
        'car_rental', 'car_sharing', 'car_wash', 'compressed_air',
        'vehicle_inspection', 'charging_station', 'driver_training',
        'ferry_terminal', 'fuel', 'grit_bin', 'motorcycle_parking',
        'parking', 'parking_entrance', 'parking_space', 'taxi', 'weighbridge',
        
        # Financial
        'atm', 'payment_terminal', 'bank', 'bureau_de_change',
        'money_transfer', 'payment_centre',
        
        # Healthcare
        'baby_hatch', 'clinic', 'dentist', 'doctors', 'hospital',
        'nursing_home', 'pharmacy', 'social_facility', 'veterinary',
        
        # Entertainment, Arts & Culture
        'arts_centre', 'brothel', 'casino', 'cinema', 'community_centre',
        'conference_centre', 'events_venue', 'exhibition_centre', 'fountain',
        'gambling', 'love_hotel', 'music_venue', 'nightclub', 'planetarium',
        'public_bookcase', 'social_centre', 'stage', 'stripclub', 'studio',
        'swingerclub', 'theatre',
        
        # Public Service
        'courthouse', 'fire_station', 'police', 'post_box', 'post_depot',
        'post_office', 'prison', 'ranger_station', 'townhall',
        
        # Facilities
        'bbq', 'bench', 'dog_toilet', 'dressing_room', 'drinking_water',
        'give_box', 'lounge', 'mailroom', 'parcel_locker', 'shelter',
        'shower', 'telephone', 'toilets', 'water_point', 'watering_place',
        'sanitary_dump_station',
        
        # Waste Management
        'recycling', 'waste_basket', 'waste_disposal', 'waste_transfer_station',
        
        # Others
        'animal_boarding', 'animal_breeding', 'animal_shelter',
        'animal_training', 'baking_oven', 'clock', 'crematorium', 'dive_centre',
        'funeral_hall', 'grave_yard', 'hunting_stand', 'internet_cafe',
        'kitchen', 'kneipp_water_cure', 'lounger', 'marketplace', 'monastery',
        'mortuary', 'photo_booth', 'place_of_mourning', 'place_of_worship',
        'public_bath', 'public_building', 'refugee_site', 'vending_machine'
    ],
    
    'barrier': [
        # Linear barriers
        'cable_barrier', 'city_wall', 'ditch', 'fence', 'guard_rail',
        'handrail', 'hedge', 'kerb', 'retaining_wall', 'wall',
        
        # Access control on highways
        'block', 'bollard', 'border_control', 'bump_gate', 'bus_trap',
        'cattle_grid', 'chain', 'cycle_barrier', 'debris', 'entrance',
        'full-height_turnstile', 'gate', 'hampshire_gate', 'height_restrictor',
        'horse_stile', 'jersey_barrier', 'kissing_gate', 'lift_gate',
        'log', 'motorcycle_barrier', 'rope', 'sally_port', 'spikes',
        'stile', 'sump_buster', 'swing_gate', 'toll_booth', 'turnstile',
        'yes'
    ],
    
    'boundary': [
        'aboriginal_lands', 'administrative', 'border_zone', 'census',
        'forest', 'forest_compartment', 'hazard', 'health', 'historic',
        'local_authority', 'low_emission_zone', 'maritime', 'marker',
        'national_park', 'place', 'political', 'postal_code',
        'protected_area', 'religious_administration', 'special_economic_zone',
        'statistical', 'disputed', 'timezone'
    ],
    
    'building': [
        # Accommodation
        'apartments', 'barracks', 'bungalow', 'cabin', 'detached',
        'annexe', 'dormitory', 'farm', 'ger', 'hotel', 'house',
        'houseboat', 'residential', 'semidetached_house', 'static_caravan',
        'stilt_house', 'terrace', 'tree_house', 'trullo',
        
        # Commercial
        'commercial', 'industrial', 'kiosk', 'office', 'retail',
        'supermarket', 'warehouse',
        
        # Religious
        'religious', 'cathedral', 'chapel', 'church', 'kingdom_hall',
        'monastery', 'mosque', 'presbytery', 'shrine', 'synagogue',
        'temple',
        
        # Civic/amenity
        'bakehouse', 'bridge', 'civic', 'college', 'fire_station',
        'government', 'gatehouse', 'hospital', 'kindergarten',
        'museum', 'public', 'school', 'toilets', 'train_station',
        'transportation', 'university',
        
        # Agricultural/plant production
        'barn', 'conservatory', 'cowshed', 'farm_auxiliary',
        'greenhouse', 'slurry_tank', 'stable', 'sty', 'livestock',
        
        # Sports
        'grandstand', 'pavilion', 'riding_hall', 'sports_hall',
        'sports_centre', 'stadium',
        
        # Storage
        'allotment_house', 'boathouse', 'hangar', 'hut', 'shed',
        
        # Cars
        'carport', 'garage', 'garages', 'parking',
        
        # Power/technical buildings
        'digester', 'service', 'tech_cab', 'transformer_tower',
        'water_tower', 'storage_tank', 'silo',
        
        # Other buildings
        'beach_hut', 'bunker', 'castle', 'construction', 'container',
        'guardhouse', 'military', 'outbuilding', 'pagoda', 'quonset_hut',
        'roof', 'ruins', 'ship', 'tent', 'tower', 'triumphal_arch',
        'windmill', 'yes'
    ],
    
    'craft': [
        'agricultural_engines', 'atelier', 'bag_repair', 'bakery',
        'basket_maker', 'beekeeper', 'blacksmith', 'boatbuilder',
        'bookbinder', 'brewery', 'builder', 'cabinet_maker',
        'candlemaker', 'car_painter', 'carpenter', 'carpet_cleaner',
        'carpet_layer', 'caterer', 'chimney_sweeper', 'cleaning',
        'clockmaker', 'clothes_mending', 'confectionery', 'cooper',
        'dental_technician', 'distillery', 'door_construction',
        'dressmaker', 'electrician', 'electronics_repair', 'elevator',
        'embroiderer', 'engraver', 'fence_maker', 'floorer', 'gardener',
        'glassblower', 'glaziery', 'goldsmith', 'grinding_mill',
        'handicraft', 'hvac', 'insulation', 'interior_decorator',
        'interior_work', 'jeweller', 'joiner', 'key_cutter',
        'laboratory', 'lapidary', 'leather', 'locksmith', 'luthier',
        'metal_construction', 'mint', 'musical_instrument', 'oil_mill',
        'optician', 'organ_builder', 'painter', 'paperhanger',
        'parquet_layer', 'paver', 'pest_control', 'photographer',
        'photographic_laboratory', 'photovoltaic', 'piano_tuner',
        'plasterer', 'plumber', 'pottery', 'printer', 'printmaker',
        'restoration', 'rigger', 'roofer', 'saddler', 'sailmaker',
        'sawmill', 'scaffolder', 'sculptor', 'shoemaker', 'signmaker',
        'stand_builder', 'stonemason', 'stove_fitter', 'sun_protection',
        'tailor', 'tatami', 'tiler', 'tinsmith', 'toolmaker', 'turner',
        'upholsterer', 'watchmaker', 'water_well_drilling', 'weaver',
        'welder', 'window_construction', 'winery'
    ],
    
    'emergency': [
        # Medical rescue
        'ambulance_station', 'defibrillator', 'landing_site',
        'emergency_ward_entrance',
        
        # Firefighters
        'fire_service_inlet', 'fire_alarm_box', 'fire_extinguisher',
        'fire_hose', 'fire_hydrant', 'water_tank', 'suction_point',
        
        # Lifeguards
        'lifeguard', 'life_ring',
        
        # Assembly point
        'assembly_point',
        
        # Other structure
        'phone', 'siren', 'drinking_water'
    ],
    
    'geological': [
        'moraine', 'outcrop', 'volcanic_caldera_rim', 'fault',
        'fold', 'palaeontological_site', 'volcanic_lava_field',
        'volcanic_vent', 'glacial_erratic', 'rock_glacier',
        'giants_kettle', 'meteor_crater', 'hoodoo',
        'columnar_jointing', 'dyke', 'monocline', 'tor',
        'unconformity', 'cone', 'sinkhole', 'pingo', 'inselberg',
        'limestone_pavement'
    ],
    
    'healthcare': [
        'alternative', 'audiologist', 'birthing_centre', 'blood_bank',
        'blood_donation', 'counselling', 'dialysis', 'hospice',
        'laboratory', 'midwife', 'nurse', 'occupational_therapist',
        'optometrist', 'physiotherapist', 'podiatrist', 'psychotherapist',
        'rehabilitation', 'sample_collection', 'speech_therapist',
        'vaccination_centre'
    ],
    
    'highway': [
        # Roads
        'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
        'unclassified', 'residential',
        
        # Link roads
        'motorway_link', 'trunk_link', 'primary_link', 'secondary_link',
        'tertiary_link',
        
        # Special road types
        'living_street', 'service', 'pedestrian', 'track', 'bus_guideway',
        'escape', 'raceway', 'road', 'busway',
        
        # Paths
        'footway', 'bridleway', 'steps', 'corridor', 'path', 'via_ferrata',
        
        # Other highway features
        'bus_stop', 'crossing', 'cyclist_waiting_aid', 'elevator',
        'emergency_bay', 'emergency_access_point', 'give_way',
        'ladder', 'milestone', 'mini_roundabout', 'motorway_junction',
        'passing_place', 'platform', 'rest_area', 'services',
        'speed_camera', 'speed_display', 'stop', 'street_lamp',
        'toll_gantry', 'traffic_mirror', 'traffic_signals', 'trailhead',
        'turning_circle', 'turning_loop'
    ],
    
    'historic': [
        'aircraft', 'anchor', 'aqueduct', 'archaeological_site',
        'battlefield', 'bomb_crater', 'boundary_stone', 'building',
        'bullaun_stone', 'cannon', 'castle', 'castle_wall',
        'cattle_crush', 'charcoal_pile', 'church', 'city_gate',
        'citywalls', 'creamery', 'district', 'epigraph', 'farm',
        'fort', 'gallows', 'house', 'high_cross', 'highwater_mark',
        'lavoir', 'lime_kiln', 'locomotive', 'machine', 'manor',
        'memorial', 'milestone', 'millstone', 'mine', 'minecart',
        'monastery', 'monument', 'mosque', 'ogham_stone',
        'optical_telegraph', 'pa', 'pillory', 'pound', 'railway_car',
        'road', 'round_tower', 'ruins', 'rune_stone', 'shieling',
        'ship', 'stećak', 'stone', 'tank', 'temple', 'tomb', 'tower',
        'vehicle', 'wayside_cross', 'wayside_shrine', 'wreck', 'yes'
    ],
    
    'landuse': [
        # Developed land
        'commercial', 'construction', 'education', 'fairground',
        'industrial', 'residential', 'retail', 'institutional',
        
        # Rural and agricultural land
        'aquaculture', 'allotments', 'farmland', 'farmyard', 'paddy',
        'animal_keeping', 'flowerbed', 'forest', 'logging',
        'greenhouse_horticulture', 'meadow', 'orchard', 'plant_nursery',
        'vineyard',
        
        # Waterbody
        'basin', 'reservoir', 'salt_pond',
        
        # Other landuse
        'brownfield', 'cemetery', 'conservation', 'depot', 'garages',
        'grass', 'greenfield', 'landfill', 'military', 'port',
        'quarry', 'railway', 'recreation_ground', 'religious',
        'village_green', 'greenery', 'winter_sports'
    ],
    
    'leisure': [
        'adult_gaming_centre', 'amusement_arcade', 'beach_resort',
        'bandstand', 'bird_hide', 'common', 'dance', 'disc_golf_course',
        'dog_park', 'escape_game', 'firepit', 'fishing', 'fitness_centre',
        'fitness_station', 'garden', 'hackerspace', 'horse_riding',
        'ice_rink', 'marina', 'miniature_golf', 'nature_reserve',
        'park', 'picnic_table', 'pitch', 'playground', 'slipway',
        'sports_centre', 'stadium', 'summer_camp', 'swimming_area',
        'swimming_pool', 'track', 'water_park'
    ],
    
    'man_made': [
        'adit', 'beacon', 'breakwater', 'bridge', 'bunker_silo',
        'carpet_hanger', 'chimney', 'column', 'communications_tower',
        'crane', 'cross', 'cutline', 'clearcut', 'dovecote',
        'dyke', 'embankment', 'flagpole', 'gasometer', 'goods_conveyor',
        'groyne', 'guard_stone', 'kiln', 'lighthouse', 'mast',
        'mineshaft', 'monitoring_station', 'obelisk', 'observatory',
        'offshore_platform', 'petroleum_well', 'pier', 'pipeline',
        'pump', 'pumping_station', 'reservoir_covered', 'sewer_vent',
        'silo', 'snow_fence', 'snow_net', 'storage_tank', 'street_cabinet',
        'stupa', 'surveillance', 'survey_point', 'tailings_pond',
        'telescope', 'tower', 'video_wall', 'wastewater_plant',
        'watermill', 'water_tower', 'water_well', 'water_tap',
        'water_works', 'wildlife_crossing', 'windmill', 'works', 'yes'
    ],
    
    'military': [
        'academy', 'airfield', 'base', 'bunker', 'barracks',
        'checkpoint', 'danger_area', 'nuclear_explosion_site',
        'obstacle_course', 'office', 'range', 'school', 'training_area',
        'trench'
    ],
    
    'natural': [
        # Vegetation
        'fell', 'grassland', 'heath', 'moor', 'scrub', 'shrubbery',
        'tree', 'tree_row', 'tundra', 'wood',
        
        # Water related
        'bay', 'beach', 'blowhole', 'cape', 'coastline', 'crevasse',
        'geyser', 'glacier', 'hot_spring', 'isthmus', 'mud', 'peninsula',
        'reef', 'shingle', 'shoal', 'spring', 'strait', 'water', 'wetland',
        
        # Geology related
        'arch', 'arete', 'bare_rock', 'blockfield', 'cave_entrance',
        'cliff', 'dune', 'earth_bank', 'fumarole', 'hill', 'peak',
        'ridge', 'rock', 'saddle', 'sand', 'scree', 'sinkhole',
        'stone', 'valley', 'volcano'
    ],
    
    'office': [
        'accountant', 'administrative', 'advertising_agency', 'airline',
        'architect', 'association', 'chamber', 'charity', 'company',
        'construction_company', 'consulting', 'courier', 'coworking',
        'diplomatic', 'educational_institution', 'employment_agency',
        'energy_supplier', 'engineer', 'estate_agent', 'event_management',
        'financial', 'financial_advisor', 'forestry', 'foundation',
        'geodesist', 'government', 'graphic_design', 'guide', 'harbour_master',
        'insurance', 'it', 'lawyer', 'logistics', 'moving_company',
        'newspaper', 'ngo', 'notary', 'politician', 'political_party',
        'property_management', 'publisher', 'quango', 'religion',
        'research', 'security', 'surveyor', 'tax_advisor',
        'telecommunication', 'transport', 'travel_agent', 'tutoring',
        'union', 'university', 'visa', 'water_utility', 'yes'
    ],
    
    'place': [
        # Administratively declared places
        'country', 'state', 'region', 'province', 'district', 'county',
        'subdistrict', 'municipality',
        
        # Populated settlements, urban
        'city', 'borough', 'suburb', 'quarter', 'neighbourhood',
        'city_block', 'plot',
        
        # Populated settlements, urban and rural
        'town', 'village', 'hamlet', 'isolated_dwelling', 'farm', 'allotments',
        
        # Other places
        'continent', 'archipelago', 'island', 'islet', 'square', 'locality',
        'polder', 'sea', 'ocean'
    ],
    
    'power': [
        'cable', 'catenary_mast', 'compensator', 'connection', 'converter',
        'generator', 'heliostat', 'insulator', 'inverter', 'line',
        'minor_line', 'plant', 'pole', 'portal', 'substation',
        'switch', 'switchgear', 'terminal', 'tower', 'transformer'
    ],
    
    'public_transport': [
        'stop_position', 'platform', 'station', 'stop_area', 'stop_area_group'
    ],
    
    'railway': [
        # Tracks
        'abandoned', 'construction', 'proposed', 'disused', 'funicular',
        'light_rail', 'miniature', 'monorail', 'narrow_gauge', 'preserved',
        'rail', 'subway', 'tram',
        
        # Stations and stops
        'halt', 'platform', 'station', 'stop', 'subway_entrance', 'tram_stop',
        
        # Infrastructure
        'buffer_stop', 'crossing', 'derail', 'level_crossing',
        'railway_crossing', 'roundhouse', 'signal', 'switch',
        'tram_level_crossing', 'traverser', 'turntable', 'ventilation_shaft',
        'wash', 'water_crane'
    ],
    
    'route': [
        'bicycle', 'bus', 'canoe', 'detour', 'ferry', 'foot',
        'hiking', 'horse', 'inline_skates', 'light_rail', 'mtb',
        'piste', 'railway', 'road', 'running', 'ski', 'subway',
        'train', 'tracks', 'tram', 'trolleybus'
    ],
    
    'shop': [
        # Food, beverages
        'alcohol', 'bakery', 'beverages', 'brewing_supplies', 'butcher',
        'cheese', 'chocolate', 'coffee', 'confectionery', 'convenience',
        'dairy', 'deli', 'farm', 'food', 'frozen_food', 'greengrocer',
        'health_food', 'ice_cream', 'nuts', 'pasta', 'pastry', 'seafood',
        'spices', 'tea', 'tortilla', 'water', 'wine',
        
        # General store, department store, mall
        'department_store', 'general', 'kiosk', 'mall', 'supermarket', 'wholesale',
        
        # Clothing, shoes, accessories
        'baby_goods', 'bag', 'boutique', 'clothes', 'fabric', 'fashion',
        'fashion_accessories', 'jewelry', 'leather', 'sewing', 'shoes',
        'shoe_repair', 'tailor', 'watches', 'wool',
        
        # Discount store, charity
        'charity', 'second_hand', 'variety_store',
        
        # Health and beauty
        'beauty', 'chemist', 'cosmetics', 'erotic', 'hairdresser',
        'hairdresser_supply', 'hearing_aids', 'herbalist', 'massage',
        'medical_supply', 'nutrition_supplements', 'optician', 'perfumery',
        'tattoo',
        
        # Do-it-yourself, household, building materials, gardening
        'agrarian', 'appliance', 'bathroom_furnishing', 'country_store',
        'doityourself', 'electrical', 'energy', 'fireplace', 'florist',
        'garden_centre', 'garden_furniture', 'gas', 'glaziery',
        'groundskeeping', 'hardware', 'houseware', 'locksmith', 'paint',
        'pottery', 'security', 'tool_hire', 'trade',
        
        # Furniture and interior
        'antiques', 'bed', 'candles', 'carpet', 'curtain', 'doors',
        'flooring', 'furniture', 'household_linen', 'interior_decoration',
        'kitchen', 'lighting', 'tiles', 'window_blind',
        
        # Electronics
        'computer', 'electronics', 'hifi', 'mobile_phone', 'printer_ink',
        'radiotechnics', 'telecommunication', 'vacuum_cleaner',
        
        # Outdoors and sport, vehicles
        'atv', 'bicycle', 'boat', 'car', 'car_parts', 'car_repair',
        'caravan', 'fishing', 'fuel', 'golf', 'hunting', 'military_surplus',
        'motorcycle', 'motorcycle_repair', 'outdoor', 'scuba_diving',
        'ski', 'snowmobile', 'sports', 'surf', 'swimming_pool', 'trailer',
        'truck', 'tyres',
        
        # Art, music, hobbies
        'art', 'camera', 'collector', 'craft', 'frame', 'games',
        'model', 'music', 'musical_instrument', 'photo', 'trophy',
        'video', 'video_games',
        
        # Stationery, gifts, books, newspapers
        'anime', 'books', 'gift', 'lottery', 'newsagent', 'stationery',
        'ticket',
        
        # Others
        'bookmaker', 'cannabis', 'copyshop', 'dry_cleaning', 'e-cigarette',
        'funeral_directors', 'laundry', 'money_lender', 'outpost', 'party',
        'pawnbroker', 'pest_control', 'pet', 'pet_grooming', 'pyrotechnics',
        'religion', 'rental', 'storage_rental', 'tobacco', 'toys',
        'travel_agency', 'vacant', 'weapons', 'yes'
    ],
    
    'sport': [
        '9pin', '10pin', 'aerobics', 'american_football', 'aikido',
        'archery', 'athletics', 'australian_football', 'badminton',
        'bandy', 'baseball', 'basketball', 'beachvolleyball', 'biathlon',
        'billiards', 'bmx', 'bobsleigh', 'boules', 'bowls', 'boxing',
        'bullfighting', 'canadian_football', 'canoe', 'chess', 'cliff_diving',
        'climbing', 'climbing_adventure', 'cockfighting', 'cricket',
        'crossfit', 'croquet', 'curling', 'cycle_polo', 'cycling',
        'darts', 'dog_agility', 'dog_racing', 'dragon_boat', 'equestrian',
        'fencing', 'field_hockey', 'fitness', 'five-a-side', 'floorball',
        'four_square', 'free_flying', 'futsal', 'gaelic_games', 'gaga',
        'golf', 'gymnastics', 'handball', 'hapkido', 'hiking', 'horseshoes',
        'horse_racing', 'ice_hockey', 'ice_skating', 'ice_stock', 'judo',
        'karate', 'karting', 'kickboxing', 'kitesurfing', 'korfball',
        'krachtbal', 'lacrosse', 'laser_tag', 'martial_arts', 'miniature_golf',
        'model_aerodrome', 'motocross', 'motor', 'multi', 'netball',
        'obstacle_course', 'orienteering', 'paddle_tennis', 'padel',
        'paintball', 'parachuting', 'parkour', 'pelota', 'pesäpallo',
        'pickleball', 'pilates', 'dance', 'pole_dance', 'racquet',
        'rc_car', 'roller_skating', 'rowing', 'rugby_league', 'rugby_union',
        'running', 'sailing', 'scuba_diving', 'shooting', 'shot-put',
        'skateboard', 'ski_jumping', 'skiing', 'snooker', 'soccer',
        'softball', 'speedway', 'squash', 'sumo', 'surfing', 'swimming',
        'table_tennis', 'table_soccer', 'taekwondo', 'tennis', 'teqball',
        'toboggan', 'trugo', 'ultimate', 'volleyball', 'wakeboarding',
        'water_polo', 'water_ski', 'weightlifting', 'windsurfing',
        'wrestling', 'yoga', 'zurkhaneh_sport'
    ],
    
    'telecom': [
        'exchange', 'connection_point', 'distribution_point', 'service_device',
        'data_center', 'line'
    ],
    
    'tourism': [
        'alpine_hut', 'apartment', 'aquarium', 'artwork', 'attraction',
        'camp_pitch', 'camp_site', 'caravan_site', 'chalet', 'gallery',
        'guest_house', 'hostel', 'hotel', 'information', 'motel',
        'museum', 'picnic_site', 'theme_park', 'viewpoint', 'wilderness_hut',
        'zoo', 'yes'
    ],
    
    'water': [
        'river', 'oxbow', 'canal', 'ditch', 'lock', 'fish_pass',
        'lake', 'reservoir', 'pond', 'basin', 'lagoon', 'stream_pool',
        'reflecting_pool', 'moat', 'wastewater'
    ],
    
    'waterway': [
        # Natural watercourses
        'river', 'riverbank', 'stream', 'tidal_channel',
        
        # Man-made waterways
        'canal', 'drain', 'ditch', 'pressurised', 'fairway',
        
        # Facilities
        'dock', 'boatyard',

        # Barriers
        'dam', 'weir', 'waterfall', 'lock_gate',

        # Other waterway features
        'soakhole', 'turning_point', 'water_point', 'fuel']

}