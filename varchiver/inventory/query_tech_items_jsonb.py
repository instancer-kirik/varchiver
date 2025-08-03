import json
import os
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import cast
from sqlalchemy.dialects.postgresql import JSONB
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

    # Query different categories of tech items by tech_category
    print("\n=== MOBILITY TECH ITEMS ===")
    mobility_items = session.query(Item).filter(Item.tech_category == 'Mobility').all()
    display_items(mobility_items)

    print("\n=== TIME TECH ITEMS ===")
    time_items = session.query(Item).filter(Item.tech_category == 'Time').all()
    display_items(time_items)

    print("\n=== TELEPORTATION TECH ITEMS ===")
    teleport_items = session.query(Item).filter(Item.tech_category == 'Teleportation').all()
    display_items(teleport_items)

    # Demonstrate JSONB queries
    # Note: These queries use PostgreSQL-specific JSONB operators and will need 
    # modification if using SQLite

    try:
        # Query items with resonance signature in tech_attributes
        print("\n=== ITEMS WITH RESONANCE SIGNATURE ===")
        resonance_items = session.query(Item).join(Item.resonance_profile).filter(
            ResonanceProfile.tech_attributes.isnot(None)
        ).all()
        display_items(resonance_items, show_resonance=True)

        # Query items with phase state in tech_attributes
        print("\n=== ITEMS WITH PHASE STATE ===")
        phase_items = session.query(Item).join(Item.inventory_properties).filter(
            InventoryProperties.tech_attributes.isnot(None)
        ).all()
        display_items(phase_items, show_inventory=True)

        # Query items with time window capability in tech_attributes
        print("\n=== ITEMS WITH TIME WINDOW CAPABILITY ===")
        time_window_items = session.query(Item).join(Item.compute_model).filter(
            ComputeModel.tech_attributes.isnot(None)
        ).all()
        display_items(time_window_items, show_compute=True)

    except Exception as e:
        print(f"Error with JSONB queries: {e}")
        print("This may happen if using SQLite instead of PostgreSQL.")
        print("Falling back to simpler queries...")
        
        # Fallback to simpler queries
        print("\n=== ALL TECH ITEMS WITH JSON ATTRIBUTES ===")
        all_tech_items = session.query(Item).filter(
            or_(
                Item.tech_category.isnot(None),
                Item.category.in_(['Mobility', 'Time', 'Teleportation'])
            )
        ).limit(10).all()
        display_items(all_tech_items, show_resonance=True, show_inventory=True, show_compute=True)

def display_items(items, show_resonance=False, show_inventory=False, show_compute=False, show_energy=False, show_thermal=False):
    """Display detailed information about items with tech_attributes."""
    if not items:
        print("No items found.")
        return

    for item in items:
        print(f"\n{'-'*50}")
        print(f"ITEM: {item.name} (ID: {item.item_id})")
        print(f"Description: {item.description}")
        print(f"Tech Tier: {item.tech_tier} | Rarity: {item.rarity}")
        print(f"Tech Category: {item.tech_category}")
        print(f"Energy Type: {item.energy_type} | Category: {item.category} | Subcategory: {item.subcategory}")
        
        # Print tags
        if item.tags:
            tag_names = [tag.name for tag in item.tags]
            print(f"Tags: {', '.join(tag_names)}")
        
        # Print effects
        if item.effects:
            effect_names = [effect.name for effect in item.effects]
            print(f"Effects: {', '.join(effect_names)}")
        
        # Show detailed resonance profile with tech_attributes if requested
        if show_resonance and item.resonance_profile:
            print(f"\nResonance Profile:")
            print(f"  Frequency: {item.resonance_profile.frequency_hz} Hz")
            print(f"  Type: {item.resonance_profile.resonance_type}")
            if item.resonance_profile.resonant_modes:
                print(f"  Modes: {', '.join(item.resonance_profile.resonant_modes)}")
            
            # Display tech_attributes for resonance profile
            if item.resonance_profile.tech_attributes:
                print("  Specialized Tech Attributes:")
                for key, value in item.resonance_profile.tech_attributes.items():
                    # Skip tech_type metadata field
                    if key != '_tech_type':
                        print(f"    {key}: {value}")
        
        # Show detailed inventory properties with tech_attributes if requested
        if show_inventory and item.inventory_properties:
            print(f"\nInventory Properties:")
            print(f"  Weight: {item.inventory_properties.weight_kg} kg")
            print(f"  Volume: {item.inventory_properties.volume_l} L")
            
            # Display tech_attributes for inventory properties
            if item.inventory_properties.tech_attributes:
                print("  Specialized Tech Attributes:")
                for key, value in item.inventory_properties.tech_attributes.items():
                    if key != '_tech_type':
                        print(f"    {key}: {value}")
        
        # Show detailed compute model with tech_attributes if requested
        if show_compute and item.compute_model:
            print(f"\nCompute Model:")
            print(f"  Function ID: {item.compute_model.function_id}")
            
            # Display tech_attributes for compute model
            if item.compute_model.tech_attributes:
                print("  Specialized Tech Attributes:")
                for key, value in item.compute_model.tech_attributes.items():
                    if key != '_tech_type':
                        print(f"    {key}: {value}")
            
            # Show params if available
            if item.compute_model.params:
                print("  Parameters:")
                for key, value in item.compute_model.params.items():
                    print(f"    {key}: {value}")
        
        # Show energy profile with tech_attributes if requested
        if show_energy and item.energy_profile:
            print(f"\nEnergy Profile:")
            print(f"  Type: {item.energy_profile.type}")
            print(f"  Input: {item.energy_profile.input_energy} | Output: {item.energy_profile.output}")
            print(f"  Base Energy: {item.energy_profile.base_energy} | Peak: {item.energy_profile.peak_energy}")
            
            # Display tech_attributes for energy profile
            if item.energy_profile.tech_attributes:
                print("  Specialized Tech Attributes:")
                for key, value in item.energy_profile.tech_attributes.items():
                    if key != '_tech_type':
                        print(f"    {key}: {value}")
        
        # Show thermal profile with tech_attributes if requested
        if show_thermal and item.thermal_profile:
            print(f"\nThermal Profile:")
            print(f"  Operating Range: {item.thermal_profile.operating_range_c}°C")
            print(f"  Failure Temp: {item.thermal_profile.failure_temp_c}°C")
            print(f"  Cooling Required: {item.thermal_profile.cooling_required}")
            
            # Display tech_attributes for thermal profile
            if item.thermal_profile.tech_attributes:
                print("  Specialized Tech Attributes:")
                for key, value in item.thermal_profile.tech_attributes.items():
                    if key != '_tech_type':
                        print(f"    {key}: {value}")

if __name__ == "__main__":
    main()