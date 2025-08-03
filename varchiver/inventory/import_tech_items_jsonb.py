import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (
    Base, Item, InventoryProperties, EnergyProfile, ThermalProfile, ResonanceProfile,
    Tag, Material, Effect, Blueprint, ComputeModel, CompatibilityTag
)

# --- CONFIGURE DATABASE URL HERE ---
# For PostgreSQL: 'postgresql+psycopg2://user:password@localhost/dbname'
# For SQLite fallback: 'sqlite:///inventory.db'
DATABASE_URL = os.environ.get('INVENTORY_DB_URL', 'sqlite:///inventory.db')

def main():
    # Create database engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Ensure tables exist
    Base.metadata.create_all(engine)

    # Load the new tech items JSON
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'new_tech_items.json')
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Process each item
    for item_data in data['items']:
        process_item(session, item_data)

    # Commit all changes to the database
    session.commit()
    print("New tech items successfully imported!")

def get_or_create(session, model, **kwargs):
    """Get an existing record or create a new one if it doesn't exist."""
    instance = session.query(model).filter_by(**kwargs).first()
    if not instance:
        instance = model(**kwargs)
        session.add(instance)
        session.flush()
    return instance

def extract_tech_attributes(data_dict, tech_type=None):
    """
    Extract specialized tech attributes from a data dictionary.
    
    Args:
        data_dict: Dictionary containing potential tech attributes
        tech_type: Optional tech category to help organize attributes
        
    Returns:
        Dictionary of tech attributes
    """
    if not data_dict:
        return None
        
    # Common attributes that should not be extracted as tech attributes
    common_attrs = {
        # Common inventory attributes
        'stack_size', 'max_stack_size', 'slot_size', 'slot_type', 'weight_kg', 'volume_l',
        # Common energy attributes
        'type', 'input_energy', 'output', 'base_energy', 'energy_drain', 'peak_energy', 'modifiers',
        # Common thermal attributes
        'sensitive', 'operating_range_c', 'failure_temp_c', 'cooling_required',
        # Common resonance attributes
        'frequency_hz', 'resonance_type', 'resonant_modes',
        # Common compute attributes 
        'function_id', 'params'
    }
    
    # Extract all non-common attributes as tech attributes
    tech_attrs = {}
    for key, value in data_dict.items():
        if key not in common_attrs:
            tech_attrs[key] = value
            
    # If params is a dict, extract nested specialized parameters
    if 'params' in data_dict and isinstance(data_dict['params'], dict):
        for key, value in data_dict['params'].items():
            if key not in tech_attrs and key not in common_attrs:  # Don't overwrite existing keys
                tech_attrs[key] = value
    
    # Include tech type information if provided
    if tech_type and tech_attrs:
        tech_attrs['_tech_type'] = tech_type
        
    return tech_attrs if tech_attrs else None

def process_item(session, item_data):
    """Process a single item from the JSON data."""
    item_id_from_json = item_data.get('id')
    if not item_id_from_json:
        print(f"Skipping item due to missing ID: {item_data.get('name')}")
        return

    # Determine the tech category based on the item data
    tech_category = item_data.get('category', 'unknown')
    
    # Check if item already exists
    item = session.query(Item).filter_by(item_id=item_id_from_json).first()

    if item:
        print(f"Updating existing item: {item_id_from_json}")
        # Clear existing many-to-many relationships
        item.tags.clear()
        item.materials.clear()
        item.effects.clear()
        item.compatibility_tags.clear()
    else:
        print(f"Creating new item: {item_id_from_json}")
        item = Item(item_id=item_id_from_json)
        session.add(item)

    # Populate basic item attributes
    for attr in [
        'name', 'description', 'tech_tier', 'energy_type', 'category', 'subcategory',
        'type', 'rarity', 'durability', 'manufacturing_cost', 'lore_notes',
        'origin_faction', 'function_script', 'icon', 'image_3d', 'historical_era',
        'cultural_significance', 'discovery_location', 'related_lore_entries',
        'required_slots', 'power_draw_priority', 'crew_requirement',
        'maintenance_schedule', 'preferred_backpack_modes', 'environmental_sensitivities',
        'legal_status', 'status_effects', 'crafting_recipe_id', 'deconstruct_yield',
        'research_prerequisites'
    ]:
        setattr(item, attr, item_data.get(attr))
    
    # Set the tech_category
    item.tech_category = tech_category

    # Handle tags
    if item_data.get('tech_tags'):
        for tag_name in item_data['tech_tags']:
            tag = get_or_create(session, Tag, name=tag_name)
            item.tags.append(tag)
    
    # Handle materials
    if item_data.get('materials'):
        for material_name in item_data['materials']:
            material = get_or_create(session, Material, name=material_name)
            item.materials.append(material)
    
    # Handle effects
    if item_data.get('effects'):
        for effect_name in item_data['effects']:
            effect = get_or_create(session, Effect, name=effect_name)
            item.effects.append(effect)
    
    # Handle compatibility tags
    if item_data.get('compatibility_tags'):
        for tag_name in item_data['compatibility_tags']:
            tag = get_or_create(session, CompatibilityTag, name=tag_name)
            item.compatibility_tags.append(tag)
    
    # Handle variant_of relationship
    variant_of_id = item_data.get('variant_of')
    if variant_of_id:
        item.variant_of = variant_of_id

    # Handle inventory properties with tech_attributes
    inv_props_data = item_data.get('inventory_properties')
    if inv_props_data:
        tech_attrs = extract_tech_attributes(inv_props_data, tech_category)
        
        # Common inventory properties
        common_props = {k: v for k, v in inv_props_data.items() 
                      if k in ['stack_size', 'max_stack_size', 'slot_size', 'slot_type', 'weight_kg', 'volume_l']}
        
        if item.inventory_properties:
            # Update common properties
            for key, value in common_props.items():
                setattr(item.inventory_properties, key, value)
            # Update tech attributes
            item.inventory_properties.tech_attributes = tech_attrs
        else:
            # Create new inventory properties with tech attributes
            props = InventoryProperties(**common_props, tech_attributes=tech_attrs)
            item.inventory_properties = props

    # Handle energy profile with tech_attributes
    energy_data = item_data.get('energy_profile')
    if energy_data:
        tech_attrs = extract_tech_attributes(energy_data, tech_category)
        
        # Common energy properties
        common_props = {k: v for k, v in energy_data.items() 
                      if k in ['type', 'input_energy', 'output', 'base_energy', 
                              'energy_drain', 'peak_energy', 'modifiers']}
        
        if item.energy_profile:
            # Update common properties
            for key, value in common_props.items():
                setattr(item.energy_profile, key, value)
            # Update tech attributes
            item.energy_profile.tech_attributes = tech_attrs
        else:
            # Create new energy profile with tech attributes
            profile = EnergyProfile(**common_props, tech_attributes=tech_attrs)
            item.energy_profile = profile

    # Handle thermal profile with tech_attributes
    thermal_data = item_data.get('thermal_profile')
    if thermal_data:
        tech_attrs = extract_tech_attributes(thermal_data, tech_category)
        
        # Common thermal properties
        common_props = {k: v for k, v in thermal_data.items() 
                      if k in ['sensitive', 'operating_range_c', 'failure_temp_c', 'cooling_required']}
        
        if item.thermal_profile:
            # Update common properties
            for key, value in common_props.items():
                setattr(item.thermal_profile, key, value)
            # Update tech attributes
            item.thermal_profile.tech_attributes = tech_attrs
        else:
            # Create new thermal profile with tech attributes
            profile = ThermalProfile(**common_props, tech_attributes=tech_attrs)
            item.thermal_profile = profile

    # Handle resonance profile with tech_attributes
    resonance_data = item_data.get('resonance_profile')
    if resonance_data:
        tech_attrs = extract_tech_attributes(resonance_data, tech_category)
        
        # Common resonance properties
        common_props = {k: v for k, v in resonance_data.items() 
                      if k in ['frequency_hz', 'resonance_type', 'resonant_modes']}
        
        if item.resonance_profile:
            # Update common properties
            for key, value in common_props.items():
                setattr(item.resonance_profile, key, value)
            # Update tech attributes
            item.resonance_profile.tech_attributes = tech_attrs
        else:
            # Create new resonance profile with tech attributes
            profile = ResonanceProfile(**common_props, tech_attributes=tech_attrs)
            item.resonance_profile = profile

    # Handle compute model with tech_attributes
    compute_data = item_data.get('compute_model')
    if compute_data:
        tech_attrs = extract_tech_attributes(compute_data, tech_category)
        
        # Common compute properties
        common_props = {k: v for k, v in compute_data.items() 
                      if k in ['function_id', 'params']}
        
        if item.compute_model:
            # Update common properties
            for key, value in common_props.items():
                setattr(item.compute_model, key, value)
            # Update tech attributes
            item.compute_model.tech_attributes = tech_attrs
        else:
            # Create new compute model with tech attributes
            model = ComputeModel(**common_props, tech_attributes=tech_attrs)
            item.compute_model = model
    
    # Handle blueprint
    blueprint_data = item_data.get('blueprint')
    if blueprint_data:
        bp_name = blueprint_data.get('name', f"{item.name or item.item_id} Blueprint")
        existing_blueprint = session.query(Blueprint).filter_by(name=bp_name).first()
        
        blueprint_attributes = {
            'name': bp_name,
            'recipe_json': blueprint_data.get('recipe_json'),
            'manufacture_time': blueprint_data.get('manufacture_time', 0.0),
            'rarity': blueprint_data.get('rarity'),
            'crafting_time_modifier': blueprint_data.get('crafting_time_modifier'),
            'required_tools_or_facilities': blueprint_data.get('required_tools_or_facilities')
        }

        if existing_blueprint:
            print(f"Updating existing blueprint: {bp_name} for item {item.item_id}")
            for key, value in blueprint_attributes.items():
                setattr(existing_blueprint, key, value)
            item.blueprint = existing_blueprint
        else:
            print(f"Creating new blueprint: {bp_name} for item {item.item_id}")
            new_blueprint = Blueprint(**blueprint_attributes)
            session.add(new_blueprint)
            item.blueprint = new_blueprint

if __name__ == "__main__":
    main()