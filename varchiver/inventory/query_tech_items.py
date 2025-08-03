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

    # Query different categories of tech items
    print("\n=== MOBILITY TECH ITEMS ===")
    mobility_items = session.query(Item).filter(Item.category == 'Mobility').all()
    display_items(mobility_items)

    print("\n=== TIME TECH ITEMS ===")
    time_items = session.query(Item).filter(Item.category == 'Time').all()
    display_items(time_items)

    print("\n=== TELEPORTATION TECH ITEMS ===")
    teleport_items = session.query(Item).filter(Item.category == 'Teleportation').all()
    display_items(teleport_items)

    # Query items with specific specialized fields
    print("\n=== ITEMS WITH RESONANCE SIGNATURE ===")
    resonance_items = session.query(Item).join(Item.resonance_profile).filter(
        ResonanceProfile.resonance_signature.isnot(None)
    ).all()
    display_items(resonance_items, show_resonance=True)

    print("\n=== ITEMS WITH PHASE STATES ===")
    phase_items = session.query(Item).join(Item.inventory_properties).filter(
        InventoryProperties.phase_state.isnot(None)
    ).all()
    display_items(phase_items, show_inventory=True)

    print("\n=== ITEMS WITH TIME WINDOW CAPABILITY ===")
    time_window_items = session.query(Item).join(Item.compute_model).filter(
        ComputeModel.time_window.isnot(None)
    ).all()
    display_items(time_window_items, show_compute=True)

def display_items(items, show_resonance=False, show_inventory=False, show_compute=False):
    """Display detailed information about items."""
    if not items:
        print("No items found.")
        return

    for item in items:
        print(f"\n{'-'*50}")
        print(f"ITEM: {item.name} (ID: {item.item_id})")
        print(f"Description: {item.description}")
        print(f"Tech Tier: {item.tech_tier} | Rarity: {item.rarity}")
        print(f"Energy Type: {item.energy_type} | Category: {item.category} | Subcategory: {item.subcategory}")
        
        # Print tags
        if item.tags:
            tag_names = [tag.name for tag in item.tags]
            print(f"Tags: {', '.join(tag_names)}")
        
        # Print effects
        if item.effects:
            effect_names = [effect.name for effect in item.effects]
            print(f"Effects: {', '.join(effect_names)}")
        
        # Show detailed resonance profile if requested
        if show_resonance and item.resonance_profile:
            print(f"\nResonance Profile:")
            print(f"  Frequency: {item.resonance_profile.frequency_hz} Hz")
            print(f"  Type: {item.resonance_profile.resonance_type}")
            if item.resonance_profile.resonant_modes:
                print(f"  Modes: {', '.join(item.resonance_profile.resonant_modes)}")
            if item.resonance_profile.resonance_signature:
                print(f"  Signature: {item.resonance_profile.resonance_signature}")
            if item.resonance_profile.harmonic_index:
                print(f"  Harmonic Index: {item.resonance_profile.harmonic_index}")
            if item.resonance_profile.frequency_matrix:
                print(f"  Frequency Matrix: {item.resonance_profile.frequency_matrix}")
        
        # Show detailed inventory properties if requested
        if show_inventory and item.inventory_properties:
            print(f"\nInventory Properties:")
            print(f"  Weight: {item.inventory_properties.weight_kg} kg")
            print(f"  Volume: {item.inventory_properties.volume_l} L")
            if item.inventory_properties.phase_state:
                print(f"  Phase State: {item.inventory_properties.phase_state}")
            if item.inventory_properties.storage_capacity:
                print(f"  Storage Capacity: {item.inventory_properties.storage_capacity}")
            if item.inventory_properties.efficiency:
                print(f"  Efficiency: {item.inventory_properties.efficiency}")
        
        # Show detailed compute model if requested
        if show_compute and item.compute_model:
            print(f"\nCompute Model:")
            print(f"  Function ID: {item.compute_model.function_id}")
            
            # Display specialized compute fields
            specialized_fields = [
                ('time_window', 'Time Window'),
                ('memory_payload', 'Memory Payload'),
                ('loop_cost', 'Loop Cost'),
                ('range_per_hop', 'Range Per Hop'),
                ('cooldown', 'Cooldown'),
                ('phase_sync', 'Phase Sync'),
                ('charge_limit', 'Charge Limit'),
                ('anchor_stability', 'Anchor Stability')
            ]
            
            for field, label in specialized_fields:
                value = getattr(item.compute_model, field, None)
                if value is not None:
                    print(f"  {label}: {value}")
            
            # Show params if available
            if item.compute_model.params:
                print("  Additional Parameters:")
                for key, value in item.compute_model.params.items():
                    print(f"    {key}: {value}")

if __name__ == "__main__":
    main()