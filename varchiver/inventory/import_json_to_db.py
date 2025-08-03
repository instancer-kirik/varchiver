import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, make_transient
from models import (
    Base, Item, InventoryProperties, EnergyProfile, ThermalProfile, ResonanceProfile,
    Tag, Material, Effect, Blueprint, ComputeModel, CompatibilityTag
)

# --- CONFIGURE DATABASE URL HERE ---
# For PostgreSQL: 'postgresql+psycopg2://user:password@localhost/dbname'
# For SQLite fallback: 'sqlite:///inventory.db'
DATABASE_URL = os.environ.get('INVENTORY_DB_URL', 'sqlite:///inventory.db')

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Drop all tables (for development and schema updates if data loss is acceptable)
Base.metadata.drop_all(engine) # User intends to run script multiple times, so keep this commented.

# Create tables if they don't exist
Base.metadata.create_all(engine)

# Load JSON
json_path = os.path.join(os.path.dirname(__file__), 'data', 'sample_items_big.json')
with open(json_path, 'r') as f:
    data = json.load(f)

def get_or_create_tag(name):
    tag = session.query(Tag).filter_by(name=name).first()
    if not tag:
        tag = Tag(name=name)
        session.add(tag)
        session.flush() # Flush to get ID if needed by relationships later in same transaction
    return tag

def get_or_create_material(name):
    material = session.query(Material).filter_by(name=name).first()
    if not material:
        material = Material(name=name)
        session.add(material)
        session.flush()
    return material

def get_or_create_effect(name):
    effect = session.query(Effect).filter_by(name=name).first()
    if not effect:
        effect = Effect(name=name)
        session.add(effect)
        session.flush()
    return effect

def get_or_create_compatibility_tag(name):
    comp_tag = session.query(CompatibilityTag).filter_by(name=name).first()
    if not comp_tag:
        comp_tag = CompatibilityTag(name=name)
        session.add(comp_tag)
        session.flush()
    return comp_tag

# Store item data and variant_of relationships for second pass
all_item_objects = {} # To store item instances by their item_id
variant_of_relations = [] # To store (item_id, variant_of_item_id) tuples

for item_data in data['items']:
    item_id_from_json = item_data.get('id')
    if not item_id_from_json:
        print(f"Skipping item due to missing ID: {item_data.get('name')}")
        continue

    # Check if item already exists
    item = session.query(Item).filter_by(item_id=item_id_from_json).first()

    if item:  # Item exists, update it
        print(f"Updating existing item: {item_id_from_json}")
        # Clear existing many-to-many relationships to repopulate them accurately
        item.tags.clear()
        item.materials.clear()
        item.effects.clear()
        item.compatibility_tags.clear()
        # Note: One-to-one relationships (like inventory_properties) will be handled by attribute assignment below.
        # If they exist, they will be updated. If not, they will be created.
    else:  # Item does not exist, create a new one
        print(f"Creating new item: {item_id_from_json}")
        item = Item(item_id=item_id_from_json)
        session.add(item)

    # Populate/Update item attributes
    item.name=item_data.get('name')
    item.description=item_data.get('description')
    item.tech_tier=item_data.get('tech_tier')
    item.energy_type=item_data.get('energy_type')
    item.category=item_data.get('category')
    item.subcategory=item_data.get('subcategory')
    item.type=item_data.get('type')
    item.rarity=item_data.get('rarity', 'common')
    item.durability=item_data.get('durability', 100)
    item.manufacturing_cost=item_data.get('manufacturing_cost', 0.0)
    item.lore_notes=item_data.get('lore_notes')
    item.origin_faction=item_data.get('origin_faction')
    item.function_script=item_data.get('function_script')
    item.icon=item_data.get('icon')
    item.image_3d=item_data.get('image_3d')
    item.historical_era=item_data.get('historical_era')
    item.cultural_significance=item_data.get('cultural_significance')
    item.discovery_location=item_data.get('discovery_location')
    item.related_lore_entries=item_data.get('related_lore_entries')
    item.required_slots=item_data.get('required_slots')
    item.power_draw_priority=item_data.get('power_draw_priority')
    item.crew_requirement=item_data.get('crew_requirement')
    item.maintenance_schedule=item_data.get('maintenance_schedule')
    item.preferred_backpack_modes=item_data.get('preferred_backpack_modes')
    item.environmental_sensitivities=item_data.get('environmental_sensitivities')
    item.legal_status=item_data.get('legal_status')
    item.status_effects=item_data.get('status_effects')
    item.crafting_recipe_id=item_data.get('crafting_recipe_id')
    item.deconstruct_yield=item_data.get('deconstruct_yield')
    item.research_prerequisites=item_data.get('research_prerequisites')
    # item.variant_of=item_data.get('variant_of') # Defer this to second pass
    
    variant_of_id = item_data.get('variant_of')
    if variant_of_id:
        variant_of_relations.append((item.item_id, variant_of_id))

    # Add/Update relationships
    if item_data.get('tech_tags'):
        for tag_name in item_data['tech_tags']:
            tag_obj = get_or_create_tag(tag_name)
            if tag_obj not in item.tags:
                item.tags.append(tag_obj)
    
    if item_data.get('materials'):
        for material_name in item_data['materials']:
            material_obj = get_or_create_material(material_name)
            if material_obj not in item.materials:
                item.materials.append(material_obj)
    
    if item_data.get('effects'):
        for effect_name in item_data['effects']:
            effect_obj = get_or_create_effect(effect_name)
            if effect_obj not in item.effects:
                item.effects.append(effect_obj)
            
    if item_data.get('compatibility_tags'):
        for comp_tag_name in item_data['compatibility_tags']:
            comp_tag_obj = get_or_create_compatibility_tag(comp_tag_name)
            if comp_tag_obj not in item.compatibility_tags:
                item.compatibility_tags.append(comp_tag_obj)
    
    # Inventory Properties
    inv_props_data = item_data.get('inventory_properties')
    if inv_props_data:
        # Extract specialized inventory fields that might be nested
        if isinstance(inv_props_data, dict):
            # Handle specialized fields that might be in nested structures
            for specialized_field in [
                'phase_state', 'storage_capacity', 'efficiency', 'release_rate', 'momentum_conversion',
                'max_angular_velocity_dps', 'momentum_transfer_efficiency', 'inertia_modulation_factor',
                'ion_flow_rate_max_mol_s', 'max_supported_modules_simultaneously',
                'module_compatibility_database_version', 'module_hot_swap_protocol_timeout_ms',
                'swap_time_reduction_s', 'efficiency_bonus_percent_per_module_match'
            ]:
                # Check if the field might be in a nested structure
                if specialized_field not in inv_props_data and 'params' in inv_props_data and isinstance(inv_props_data['params'], dict):
                    if specialized_field in inv_props_data['params']:
                        inv_props_data[specialized_field] = inv_props_data['params'][specialized_field]
                        
        if item.inventory_properties:
            for key, value in inv_props_data.items():
                setattr(item.inventory_properties, key, value)
        else:
            item.inventory_properties = InventoryProperties(**inv_props_data)
    elif item.inventory_properties: # If data is removed from JSON, remove from DB
        session.delete(item.inventory_properties)
        item.inventory_properties = None

    # Energy Profile
    energy_data = item_data.get('energy_profile')
    if energy_data:
        # Extract specialized tech fields that might be nested
        if isinstance(energy_data, dict):
            # Handle specialized fields that might be in nested structures
            for specialized_field in [
                'power_output_gw', 'energy_conversion_efficiency_target', 'max_ftl_speed_c_equivalent',
                'charge_time_minutes', 'max_jump_range_ly_single', 'navigation_accuracy_error_margin_percent',
                'bubble_stability_threshold_min', 'max_force_newtons', 'range_m', 'beam_width_m',
                'max_beam_range_m', 'beam_focus_cone_angle_degrees', 'power_allocation_efficiency',
                'lift_capacity_kg', 'force_newtons', 'mana_efficiency', 'spell_stability',
                'conversion_ratio', 'field_strength', 'spatial_resolution', 'quantum_stability', 'field_range'
            ]:
                # Check if the field might be in a nested structure
                if specialized_field not in energy_data and 'params' in energy_data and isinstance(energy_data['params'], dict):
                    if specialized_field in energy_data['params']:
                        energy_data[specialized_field] = energy_data['params'][specialized_field]
                        
        if item.energy_profile:
            for key, value in energy_data.items():
                setattr(item.energy_profile, key, value)
        else:
            item.energy_profile = EnergyProfile(**energy_data)
    elif item.energy_profile:
        session.delete(item.energy_profile)
        item.energy_profile = None

    # Thermal Profile
    thermal_data = item_data.get('thermal_profile')
    if thermal_data:
        # Extract specialized thermal fields that might be nested
        if isinstance(thermal_data, dict):
            # Handle specialized fields that might be in nested structures
            for specialized_field in [
                'heat_dissipated_kj', 'min_temp_c', 'max_temp_c', 'thermal_efficiency_cop',
                'target_temperature_range_c', 'max_cooling_capacity_kw', 'max_heating_capacity_kw', 'cold_factor'
            ]:
                # Check if the field might be in a nested structure
                if specialized_field not in thermal_data and 'params' in thermal_data and isinstance(thermal_data['params'], dict):
                    if specialized_field in thermal_data['params']:
                        thermal_data[specialized_field] = thermal_data['params'][specialized_field]
                        
        if item.thermal_profile:
            for key, value in thermal_data.items():
                setattr(item.thermal_profile, key, value)
        else:
            item.thermal_profile = ThermalProfile(**thermal_data)
    elif item.thermal_profile:
        session.delete(item.thermal_profile)
        item.thermal_profile = None

    # Resonance Profile
    resonance_data = item_data.get('resonance_profile')
    if resonance_data:
        # Extract specialized resonance fields that might be nested
        if isinstance(resonance_data, dict):
            # Handle specialized fields that might be in nested structures
            for specialized_field in [
                'resonance_signature', 'harmonic_index', 'frequency_matrix', 'interference_map',
                'oscillation_frequency_target_hz', 'portal_stability_threshold_min', 
                'resonance_frequency_target_hz', 'harmonic_series', 'resonance_quality'
            ]:
                # Check if the field might be in a nested structure
                if specialized_field not in resonance_data and 'params' in resonance_data and isinstance(resonance_data['params'], dict):
                    if specialized_field in resonance_data['params']:
                        resonance_data[specialized_field] = resonance_data['params'][specialized_field]
                        
        if item.resonance_profile:
            for key, value in resonance_data.items():
                setattr(item.resonance_profile, key, value)
        else:
            item.resonance_profile = ResonanceProfile(**resonance_data)
    elif item.resonance_profile:
        session.delete(item.resonance_profile)
        item.resonance_profile = None

    # Compute Model
    compute_data = item_data.get('compute_model')
    if compute_data:
        # Extract specialized compute fields from params if they exist
        if isinstance(compute_data, dict) and 'params' in compute_data and isinstance(compute_data['params'], dict):
            # Add all params as top-level attributes for the specialized tech fields
            for param_key, param_value in compute_data['params'].items():
                if param_key not in compute_data:  # Don't overwrite if already exists at top level
                    compute_data[param_key] = param_value
            
            # Handle specific field categories and their specialized parameters
            specialized_fields = [
                # Locomotion/Mobility Tech
                'mass_limit', 'duration', 'stability_rating', 'range_per_hop', 'cooldown', 'phase_sync',
                # Time Tech
                'time_window', 'memory_payload', 'loop_cost', 'speed_multiplier', 'radius', 'drift_penalty',
                'entropy_output', 'subversion_depth',
                # Teleportation/Phasing
                'charge_limit', 'anchor_stability', 'reacquire_time', 'max_mass', 'distortion_index',
                'collapse_risk', 'target_lock', 'reflection_delay', 'decoherence_rate',
                # Meta/Exotic Systems
                'fork_count', 'merge_cost', 'risk_threshold', 'decay_rate', 'replica_strength', 'usage_limit',
                # Fishing Tech
                'target_species', 'signal_pattern', 'battery_life', 'entangle_rate', 'ethical_rating',
                'capture_radius', 'power_drain', 'ecological_disruption', 'projection_duration',
                'decoy_type', 'field_signature', 'release_cycle', 'biomass_capacity',
                # Trapping Tech
                'tension_threshold', 'species_filter', 'trap_window', 'gravity_field', 'scent_profile',
                'coverage_area', 'species_ids', 'camouflage_mode', 'behavior_tree', 'flight_time',
                # Hybrid Systems
                'node_count', 'ai_model', 'recovery_protocol', 'collection_type', 'biomass_rate',
                'preservation_quality', 'vibration_profile', 'depth_range', 'creature_type'
            ]
            
            # Ensure any specialized field in params gets promoted to the top level
            for field in specialized_fields:
                if field in compute_data['params'] and field not in compute_data:
                    compute_data[field] = compute_data['params'][field]
            
        if item.compute_model:
            for key, value in compute_data.items():
                setattr(item.compute_model, key, value)
        else:
            item.compute_model = ComputeModel(**compute_data)
    elif item.compute_model:
        session.delete(item.compute_model)
        item.compute_model = None
    
    # Blueprint
    blueprint_data = item_data.get('blueprint')
    if blueprint_data:
        bp_name = blueprint_data.get('name', f"{item.name or item.item_id} Blueprint")
        existing_blueprint = session.query(Blueprint).filter_by(name=bp_name).first()
        
        blueprint_attributes = {
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
            new_blueprint = Blueprint(name=bp_name, **blueprint_attributes)
            session.add(new_blueprint)
            item.blueprint = new_blueprint
            
    elif item.blueprint: # If blueprint data removed from JSON, disassociate and optionally delete blueprint
        # Decide if orphaned blueprints should be deleted or just disassociated.
        # For now, just disassociate. If blueprints are shared, deletion is more complex.
        print(f"Disassociating blueprint from item: {item.item_id}")
        # To delete an orphaned blueprint if it's no longer referenced by any other item:
        # if not item.blueprint.produced_items or (len(item.blueprint.produced_items) == 1 and item in item.blueprint.produced_items):
        #     print(f"Deleting orphaned blueprint: {item.blueprint.name}")
        #     session.delete(item.blueprint)
        item.blueprint = None

    all_item_objects[item.item_id] = item # Store created/updated item instance

session.commit() # Commit after first pass of item creation/updates

# Second pass: Establish variant_of relationships
print("\n--- Second Pass: Updating variant_of relationships ---")
for item_id, variant_of_target_id in variant_of_relations:
    item = all_item_objects.get(item_id)
    # The target for variant_of should also be an item_id from the JSON
    # No need to query Item table by primary key, but by item_id (which is unique)
    variant_target_item = all_item_objects.get(variant_of_target_id)
    
    if item and variant_target_item:
        print(f"Setting variant_of for item {item.item_id} to {variant_target_item.item_id}")
        item.variant_of = variant_target_item.item_id # Assign the item_id string
    elif item and not variant_target_item:
        print(f"Warning: Could not find variant_of target item with id '{variant_of_target_id}' for item '{item.item_id}'. Skipping.")
    elif not item:
        # This case should ideally not happen if all_item_objects is populated correctly
        print(f"Warning: Could not find source item with id '{item_id}' for variant_of relationship. Skipping.")

session.commit()
print('Import complete!') 