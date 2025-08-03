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

def process_item(session, item_data):
    """Process a single item from the JSON data."""
    item_id_from_json = item_data.get('id')
    if not item_id_from_json:
        print(f"Skipping item due to missing ID: {item_data.get('name')}")
        return

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

    # Handle inventory properties with specialized fields
    inv_props_data = item_data.get('inventory_properties')
    if inv_props_data:
        if item.inventory_properties:
            for key, value in inv_props_data.items():
                setattr(item.inventory_properties, key, value)
        else:
            item.inventory_properties = InventoryProperties(**inv_props_data)

    # Handle energy profile with specialized fields
    energy_data = item_data.get('energy_profile')
    if energy_data:
        if item.energy_profile:
            for key, value in energy_data.items():
                setattr(item.energy_profile, key, value)
        else:
            item.energy_profile = EnergyProfile(**energy_data)

    # Handle thermal profile with specialized fields
    thermal_data = item_data.get('thermal_profile')
    if thermal_data:
        if item.thermal_profile:
            for key, value in thermal_data.items():
                setattr(item.thermal_profile, key, value)
        else:
            item.thermal_profile = ThermalProfile(**thermal_data)

    # Handle resonance profile with specialized fields
    resonance_data = item_data.get('resonance_profile')
    if resonance_data:
        if item.resonance_profile:
            for key, value in resonance_data.items():
                setattr(item.resonance_profile, key, value)
        else:
            item.resonance_profile = ResonanceProfile(**resonance_data)

    # Handle compute model with specialized fields
    compute_data = item_data.get('compute_model')
    if compute_data:
        # Extract specialized compute fields from params if they exist
        if isinstance(compute_data, dict) and 'params' in compute_data and isinstance(compute_data['params'], dict):
            # Add all params as top-level attributes
            for param_key, param_value in compute_data['params'].items():
                if param_key not in compute_data:  # Don't overwrite if already exists at top level
                    compute_data[param_key] = param_value
        
        if item.compute_model:
            for key, value in compute_data.items():
                setattr(item.compute_model, key, value)
        else:
            item.compute_model = ComputeModel(**compute_data)
    
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