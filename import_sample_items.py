#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path

# Add the parent directory to Python path to find the inventory modules
parent_dir = str(Path(__file__).resolve().parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from varchiver.inventory.models import (
    Base, Item, InventoryProperties, EnergyProfile, ThermalProfile, ResonanceProfile,
    Tag, Material, Effect, Blueprint, ComputeModel, CompatibilityTag
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def main():
    # Configure database URL
    DATABASE_URL = os.environ.get('INVENTORY_DB_URL', 'sqlite:///inventory.db')
    
    # Create database engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Ensure tables exist
    Base.metadata.create_all(engine)
    
    # Load the sample items JSON
    json_path = os.path.join(parent_dir, 'varchiver', 'inventory', 'data', 'sample_items.json')
    print(f"Loading items from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Process each item
    for item_data in data['items']:
        item_id = item_data['id']
        print(f"Processing item: {item_id}")
        
        # Check if item already exists
        existing_item = session.query(Item).filter_by(item_id=item_id).first()
        if existing_item:
            print(f"Item {item_id} already exists, skipping...")
            continue
        
        # Create new item
        item = Item(
            item_id=item_id,
            name=item_data.get('name'),
            description=item_data.get('description'),
            tech_tier=item_data.get('tech_tier'),
            energy_type=item_data.get('energy_type'),
            category=item_data.get('category'),
            subcategory=item_data.get('subcategory'),
            type=item_data.get('type')
        )
        session.add(item)
        session.flush()  # Generate the ID
        
        # Add inventory properties
        inv_data = item_data.get('inventory_properties', {})
        if inv_data:
            item.inventory_properties = InventoryProperties(
                stack_size=inv_data.get('stack_size', 1),
                max_stack_size=inv_data.get('max_stack_size', 1),
                slot_size=inv_data.get('slot_size'),
                weight_kg=inv_data.get('weight_kg'),
                volume_l=inv_data.get('volume_l'),
                item_id=item.id
            )
        
        # Add tags
        for tag_name in item_data.get('tech_tags', []):
            tag = session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                session.add(tag)
            item.tags.append(tag)
        
        # Add effects
        for effect_name in item_data.get('effects', []):
            effect = session.query(Effect).filter_by(name=effect_name).first()
            if not effect:
                effect = Effect(name=effect_name)
                session.add(effect)
            item.effects.append(effect)
    
    # Commit all changes
    session.commit()
    print("Sample items successfully imported!")

if __name__ == '__main__':
    main()