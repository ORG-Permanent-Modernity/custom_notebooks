all_templates = {
        "3 NEW": {
            "Tech": {
                # Higher education
                'university': 'Higher Education',
                'college': 'Higher Education',
                'education': 'Higher Education',
                'language_school': 'Higher Education',
                
                # Tech-related services
                'internet_cafe': 'Tech Services',
                'coworking_space': 'Tech Services',
                'telephone': 'Tech Services',
                'studio': 'Tech Services'
            },
            
            "Urban Living": {
                # Base education
                'school': 'Base Education',
                'kindergarten': 'Base Education',
                'childcare': 'Base Education',
                'dancing_school': 'Base Education',
                'music_school': 'Base Education',
                
                # Community
                'community_centre': 'Community',
                
                # Library
                'library': 'Library',
                
                # Food and beverage
                'restaurant': 'Food & Beverage',
                'cafe': 'Food & Beverage',
                'fast_food': 'Food & Beverage',
                'ice_cream': 'Food & Beverage',
                'food_court': 'Food & Beverage',
                'confectionery': 'Food & Beverage',
                'pastry': 'Food & Beverage',
                'bakery': 'Food & Beverage',
                'seafood': 'Food & Beverage',
                'coffee': 'Food & Beverage',
                'tea': 'Food & Beverage',
                'deli': 'Food & Beverage',
                
                # Healthcare and wellness
                'hospital': 'Healthcare & Wellness',
                'clinic': 'Healthcare & Wellness',
                'dentist': 'Healthcare & Wellness',
                'doctors': 'Healthcare & Wellness',
                'pharmacy': 'Healthcare & Wellness',
                'optician': 'Healthcare & Wellness',
                'massage': 'Healthcare & Wellness',
                'beauty': 'Healthcare & Wellness',
                'cosmetics': 'Healthcare & Wellness',
                'perfumery': 'Healthcare & Wellness',
                'hairdresser': 'Healthcare & Wellness',
                'medical_supply': 'Healthcare & Wellness',
                'veterinary': 'Healthcare & Wellness',
                'hairdresser_supply': 'Healthcare & Wellness',
                'chemist': 'Healthcare & Wellness',
                'nutrition_supplements': 'Healthcare & Wellness',
                
                # Transportation
                'parking': 'Transportation',
                'parking_entrance': 'Transportation',
                'car_rental': 'Transportation',
                'bicycle_parking': 'Transportation',
                'bicycle_rental': 'Transportation',
                'bus_station': 'Transportation',
                'charging_station': 'Transportation',
                'car_pooling': 'Transportation',
                'fuel': 'Transportation',
                'taxi': 'Transportation',
                
                # Nightlife
                'bar': 'Nightlife',
                'pub': 'Nightlife',
                'nightclub': 'Nightlife',
                'hookah_lounge': 'Nightlife',
                'karaoke_box': 'Nightlife',
                'biergarten': 'Nightlife',
                'wine': 'Nightlife',
                'party': 'Nightlife',
                
                # Groceries
                'supermarket': 'Groceries',
                'convenience': 'Groceries',
                'greengrocer': 'Groceries',
                'butcher': 'Groceries',
                'alcohol': 'Groceries',
                'dairy': 'Groceries',
                'cheese': 'Groceries',
                'spices': 'Groceries',
                'beverages': 'Groceries',
                'marketplace': 'Groceries',
                'health_food': 'Groceries',
                'honey': 'Groceries',
                'nuts': 'Groceries',
                
                # Government
                'townhall': 'Government',
                'police': 'Government',
                'courthouse': 'Government',
                'shelter': 'Government',
                
                # Recreation
                'games': 'Recreation',
                'public_bath': 'Recreation',
                
                # Services (non-tech related but part of urban living)
                'bank': 'Services',
                'bureau_de_change': 'Services',
                'laundry': 'Services',
                'post_office': 'Services',
                'money_transfer': 'Services',
                'dry_cleaning': 'Services'
            },
            
            "Industry through design": {
                # Culture
                'theatre': 'Culture',
                'cinema': 'Culture',
                'arts_centre': 'Culture',
                'museum': 'Culture',
                
                # Retail
                'clothes': 'Retail',
                'shoes': 'Retail',
                'mobile_phone': 'Retail',
                'electronics': 'Retail',
                'computer': 'Retail',
                'jewelry': 'Retail',
                'furniture': 'Retail',
                'toys': 'Retail',
                'books': 'Retail',
                'gift': 'Retail',
                'department_store': 'Retail',
                'boutique': 'Retail',
                'carpet': 'Retail',
                'curtain': 'Retail',
                'bed': 'Retail',
                'houseware': 'Retail',
                'stationery': 'Retail',
                'bag': 'Retail',
                'clock': 'Retail',
                'watches': 'Retail',
                'accessories': 'Retail',
                'fashion_accessories': 'Retail',
                'antiques': 'Retail',
                'second_hand': 'Retail',
                'art': 'Retail',
                'craft': 'Retail',
                'photo': 'Retail',
                'music': 'Retail',
                'video_games': 'Retail',
                'sports': 'Retail',
                'baby_goods': 'Retail',
                'florist': 'Retail',
                'hardware': 'Retail',
                'musical_instrument': 'Retail',
                'pet': 'Retail',
                'tobacco': 'Retail',
                'e-cigarette': 'Retail',
                'kiosk': 'Retail',
                'doityourself': 'Retail',
                'appliance': 'Retail',
                'hifi': 'Retail',
                'newsagent': 'Retail',
                'variety_store': 'Retail',
                'fabric': 'Retail',
                'anime': 'Retail',
                'window_blind': 'Retail',
                'flooring': 'Retail',
                'lighting': 'Retail',
                'interior_decoration': 'Retail',
                'frame': 'Retail',
                'household_linen': 'Retail',
                'pottery': 'Retail',
                'paint': 'Retail',
                'garden_centre': 'Retail',
                'mall': 'Retail',
                'shoe_repair': 'Retail',
                
                # Design-related services
                'copyshop': 'Design Services',
                'tailor': 'Design Services',
                'sewing': 'Design Services',
                'tattoo': 'Design Services',
                'locksmith': 'Design Services'
            },
            
            "Other": {
                # Religion
                'place_of_worship': 'Religion',
                
                # Agriculture and animals
                'farm': 'Agriculture & Animals',
                'animal_boarding': 'Agriculture & Animals',
                
                # Infrastructure
                'water_point': 'Infrastructure',
                'photo_booth': 'Infrastructure',
                
                # Automotive
                'car_wash': 'Automotive',
                'car_repair': 'Automotive',
                'car_parts': 'Automotive',
                'car': 'Automotive',
                'motorcycle': 'Automotive',
                'motorcycle_parts': 'Automotive',
                'bicycle': 'Automotive',
                'tyres': 'Automotive',
                'radiotechnics': 'Automotive',
                
                # Miscellaneous services
                'travel_agency': 'Miscellaneous Services',
                'pawnbroker': 'Miscellaneous Services',
                'ticket': 'Miscellaneous Services',
                'bookmaker': 'Miscellaneous Services',
                'post_box': 'Miscellaneous Services',
                'parcel_locker': 'Miscellaneous Services',
                'outpost': 'Miscellaneous Services',
                'rental': 'Miscellaneous Services',
                'payment_centre': 'Miscellaneous Services',
                
                # Specialty retail
                'electrical': 'Specialty Retail',
                'weapons': 'Specialty Retail',
                'hunting': 'Specialty Retail',
                'collector': 'Specialty Retail'
            }
        },

        "ORIGINAL": {
            "higher_education": {
                'university': 'higher_education',
                'college': 'higher_education',
                'education': 'higher_education',
                'language_school': 'higher_education'
            },
            
            "base_education": {
                'school': 'base_education',
                'kindergarten': 'base_education',
                'childcare': 'base_education',
                'dancing_school': 'base_education',
                'music_school': 'base_education'
            },
            
            "culture": {
                'theatre': 'culture',
                'cinema': 'culture',
                'arts_centre': 'culture',
                'museum': 'culture'
            },
            
            "community": {
                'community_centre': 'community'
            },
            
            "library": {
                'library': 'library'
            },
            
            "food_and_beverage": {
                'restaurant': 'food_and_beverage',
                'cafe': 'food_and_beverage',
                'fast_food': 'food_and_beverage',
                'ice_cream': 'food_and_beverage',
                'food_court': 'food_and_beverage',
                'confectionery': 'food_and_beverage',
                'pastry': 'food_and_beverage',
                'bakery': 'food_and_beverage',
                'seafood': 'food_and_beverage',
                'coffee': 'food_and_beverage',
                'tea': 'food_and_beverage',
                'deli': 'food_and_beverage'
            },
            
            "retail": {
                'clothes': 'retail',
                'shoes': 'retail',
                'mobile_phone': 'retail',
                'electronics': 'retail',
                'computer': 'retail',
                'jewelry': 'retail',
                'furniture': 'retail',
                'toys': 'retail',
                'books': 'retail',
                'gift': 'retail',
                'department_store': 'retail',
                'boutique': 'retail',
                'carpet': 'retail',
                'curtain': 'retail',
                'bed': 'retail',
                'houseware': 'retail',
                'stationery': 'retail',
                'bag': 'retail',
                'clock': 'retail',
                'watches': 'retail',
                'accessories': 'retail',
                'fashion_accessories': 'retail',
                'antiques': 'retail',
                'second_hand': 'retail',
                'art': 'retail',
                'craft': 'retail',
                'photo': 'retail',
                'music': 'retail',
                'video_games': 'retail',
                'sports': 'retail',
                'baby_goods': 'retail',
                'florist': 'retail',
                'hardware': 'retail',
                'musical_instrument': 'retail',
                'pet': 'retail',
                'tobacco': 'retail',
                'e-cigarette': 'retail',
                'kiosk': 'retail',
                'doityourself': 'retail',
                'appliance': 'retail',
                'hifi': 'retail',
                'newsagent': 'retail',
                'variety_store': 'retail',
                'fabric': 'retail',
                'anime': 'retail',
                'window_blind': 'retail',
                'flooring': 'retail',
                'lighting': 'retail',
                'interior_decoration': 'retail',
                'frame': 'retail',
                'household_linen': 'retail',
                'pottery': 'retail',
                'paint': 'retail',
                'electrical': 'retail',
                'garden_centre': 'retail',
                'weapons': 'retail',
                'hunting': 'retail',
                'collector': 'retail',
                'mall': 'retail'
            },
            
            "services": {
                'bank': 'services',
                'bureau_de_change': 'services',
                'car_wash': 'services',
                'car_repair': 'services',
                'car_parts': 'services',
                'copyshop': 'services',
                'laundry': 'services',
                'post_office': 'services',
                'tailor': 'services',
                'shoe_repair': 'services',
                'travel_agency': 'services',
                'pawnbroker': 'services',
                'ticket': 'services',
                'bookmaker': 'services',
                'internet_cafe': 'services',
                'telephone': 'services',
                'post_box': 'services',
                'parcel_locker': 'services',
                'money_transfer': 'services',
                'outpost': 'services',
                'studio': 'services',
                'coworking_space': 'services',
                'locksmith': 'services',
                'dry_cleaning': 'services',
                'rental': 'services',
                'sewing': 'services',
                'tattoo': 'services',
                'payment_centre': 'services'
            },
            
            "healthcare_wellness": {
                'hospital': 'healthcare_wellness',
                'clinic': 'healthcare_wellness',
                'dentist': 'healthcare_wellness',
                'doctors': 'healthcare_wellness',
                'pharmacy': 'healthcare_wellness',
                'optician': 'healthcare_wellness',
                'massage': 'healthcare_wellness',
                'beauty': 'healthcare_wellness',
                'cosmetics': 'healthcare_wellness',
                'perfumery': 'healthcare_wellness',
                'hairdresser': 'healthcare_wellness',
                'medical_supply': 'healthcare_wellness',
                'veterinary': 'healthcare_wellness',
                'hairdresser_supply': 'healthcare_wellness',
                'chemist': 'healthcare_wellness',
                'nutrition_supplements': 'healthcare_wellness'
            },
            
            "transportation": {
                'parking': 'transportation',
                'parking_entrance': 'transportation',
                'car_rental': 'transportation',
                'bicycle_parking': 'transportation',
                'bicycle_rental': 'transportation',
                'bus_station': 'transportation',
                'charging_station': 'transportation',
                'car_pooling': 'transportation',
                'fuel': 'transportation',
                'car': 'transportation',
                'motorcycle': 'transportation',
                'motorcycle_parts': 'transportation',
                'bicycle': 'transportation',
                'tyres': 'transportation',
                'radiotechnics': 'transportation',
                'taxi': 'transportation'
            },
            
            "nightlife": {
                'bar': 'nightlife',
                'pub': 'nightlife',
                'nightclub': 'nightlife',
                'hookah_lounge': 'nightlife',
                'karaoke_box': 'nightlife',
                'biergarten': 'nightlife',
                'wine': 'nightlife',
                'party': 'nightlife'
            },
            
            "groceries": {
                'supermarket': 'groceries',
                'convenience': 'groceries',
                'greengrocer': 'groceries',
                'butcher': 'groceries',
                'alcohol': 'groceries',
                'dairy': 'groceries',
                'cheese': 'groceries',
                'spices': 'groceries',
                'beverages': 'groceries',
                'marketplace': 'groceries',
                'health_food': 'groceries',
                'honey': 'groceries',
                'nuts': 'groceries'
            },
            
            "religion": {
                'place_of_worship': 'religion'
            },
            
            "government": {
                'townhall': 'government',
                'police': 'government',
                'courthouse': 'government',
                'shelter': 'government'
            },
            
            "agriculture_animals": {
                'farm': 'agriculture_animals',
                'animal_boarding': 'agriculture_animals'
            },
            
            "recreation": {
                'games': 'recreation',
                'public_bath': 'recreation'
            },
            
            "infrastructure": {
                'water_point': 'infrastructure',
                'photo_booth': 'infrastructure'
            }
        },
    }