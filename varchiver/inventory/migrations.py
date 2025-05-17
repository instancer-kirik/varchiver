"""Database migration script for inventory system."""

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy
import os

# Database URL from environment or default to SQLite
DATABASE_URL = os.environ.get('INVENTORY_DB_URL', 'sqlite:///inventory.db')
engine = create_engine(DATABASE_URL)
metadata = MetaData()

def migrate():
    """Run database migrations."""
    # Create new tables
    create_new_tables()
    
    # Migrate existing data
    migrate_existing_data()
    
    # Drop old columns
    drop_old_columns()

def create_new_tables():
    """Create new tables for the enhanced schema."""
    # Create base tables first
    Table('items', metadata,
        Column('id', Integer, primary_key=True),
        Column('item_id', String, unique=True),
        Column('name', String),
        Column('description', Text),
        Column('tech_tier', String),
        Column('energy_type', String),
        Column('category', String),
        Column('subcategory', String),
        Column('type', String),
        Column('rarity', String),
        Column('durability', Integer),
        Column('manufacturing_cost', Float),
        Column('lore_notes', Text),
        Column('origin_faction', String),
        Column('function_script', String)
    )
    
    Table('tags', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True)
    )
    
    Table('materials', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True)
    )
    
    Table('effects', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True),
        Column('description', Text)
    )
    
    Table('blueprints', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String, unique=True),
        Column('recipe_json', JSONB if sqlalchemy.engine.url.make_url(DATABASE_URL).get_backend_name() == 'postgresql' else String),
        Column('manufacture_time', Float)
    )
    
    # Create profile tables
    Table('inventory_properties', metadata,
        Column('id', Integer, primary_key=True),
        Column('stack_size', Integer),
        Column('max_stack_size', Integer),
        Column('slot_size', String),  # JSON stored as string
        Column('slot_type', String),
        Column('weight_kg', Float),
        Column('volume_l', Float),
        Column('item_id', Integer, ForeignKey('items.id'))
    )
    
    Table('energy_profiles', metadata,
        Column('id', Integer, primary_key=True),
        Column('type', String),
        Column('input_energy', String),
        Column('output', String),
        Column('base_energy', Float),
        Column('energy_drain', Float),
        Column('peak_energy', Float),
        Column('modifiers', String),  # JSON stored as string
        Column('item_id', Integer, ForeignKey('items.id'))
    )
    
    Table('thermal_profiles', metadata,
        Column('id', Integer, primary_key=True),
        Column('sensitive', Boolean),
        Column('operating_range_c', String),  # JSON stored as string
        Column('failure_temp_c', Integer),
        Column('cooling_required', Boolean),
        Column('item_id', Integer, ForeignKey('items.id'))
    )
    
    Table('resonance_profiles', metadata,
        Column('id', Integer, primary_key=True),
        Column('frequency_hz', Float),
        Column('resonance_type', String),
        Column('resonant_modes', String),  # JSON stored as string
        Column('item_id', Integer, ForeignKey('items.id'))
    )
    
    Table('compute_models', metadata,
        Column('id', Integer, primary_key=True),
        Column('processing_power', Float),
        Column('memory_capacity', Float),
        Column('network_bandwidth', Float),
        Column('item_id', Integer, ForeignKey('items.id'))
    )
    
    # Create association tables after all base tables exist
    Table('item_tags', metadata,
        Column('item_id', Integer, ForeignKey('items.id'), primary_key=True),
        Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
    )
    
    Table('item_materials', metadata,
        Column('item_id', Integer, ForeignKey('items.id'), primary_key=True),
        Column('material_id', Integer, ForeignKey('materials.id'), primary_key=True)
    )
    
    Table('item_effects', metadata,
        Column('item_id', Integer, ForeignKey('items.id'), primary_key=True),
        Column('effect_id', Integer, ForeignKey('effects.id'), primary_key=True)
    )
    
    Table('upgrade_paths', metadata,
        Column('id', Integer, primary_key=True),
        Column('source_id', Integer, ForeignKey('items.id')),
        Column('target_id', Integer, ForeignKey('items.id')),
        Column('method', String),
        Column('cost', Float),
        Column('blueprint_id', Integer, ForeignKey('blueprints.id'))
    )
    
    # Create all tables
    metadata.create_all(engine)

def migrate_existing_data():
    """Migrate data from old schema to new schema."""
    # Get database connection
    conn = engine.connect()
    
    try:
        # Migrate tech_tags to tags
        conn.execute("""
            INSERT INTO tags (name)
            SELECT DISTINCT unnest(tech_tags::text[])
            FROM items
            WHERE tech_tags IS NOT NULL
            ON CONFLICT (name) DO NOTHING
        """)
        
        # Create item-tag relationships
        conn.execute("""
            INSERT INTO item_tags (item_id, tag_id)
            SELECT i.id, t.id
            FROM items i, tags t
            WHERE t.name = ANY(i.tech_tags::text[])
            ON CONFLICT DO NOTHING
        """)
        
        # Similar migrations for materials and effects
        conn.execute("""
            INSERT INTO materials (name)
            SELECT DISTINCT unnest(materials::text[])
            FROM items
            WHERE materials IS NOT NULL
            ON CONFLICT (name) DO NOTHING
        """)
        
        conn.execute("""
            INSERT INTO item_materials (item_id, material_id)
            SELECT i.id, m.id
            FROM items i, materials m
            WHERE m.name = ANY(i.materials::text[])
            ON CONFLICT DO NOTHING
        """)
        
        conn.execute("""
            INSERT INTO effects (name)
            SELECT DISTINCT unnest(effects::text[])
            FROM items
            WHERE effects IS NOT NULL
            ON CONFLICT (name) DO NOTHING
        """)
        
        conn.execute("""
            INSERT INTO item_effects (item_id, effect_id)
            SELECT i.id, e.id
            FROM items i, effects e
            WHERE e.name = ANY(i.effects::text[])
            ON CONFLICT DO NOTHING
        """)
        
        # Add new columns to items table
        conn.execute("""
            ALTER TABLE items
            ADD COLUMN IF NOT EXISTS rarity VARCHAR,
            ADD COLUMN IF NOT EXISTS durability INTEGER,
            ADD COLUMN IF NOT EXISTS manufacturing_cost FLOAT,
            ADD COLUMN IF NOT EXISTS lore_notes TEXT,
            ADD COLUMN IF NOT EXISTS origin_faction VARCHAR,
            ADD COLUMN IF NOT EXISTS function_script VARCHAR,
            ADD COLUMN IF NOT EXISTS blueprint_id INTEGER REFERENCES blueprints(id)
        """)
        
        # Add new columns to inventory_properties
        conn.execute("""
            ALTER TABLE inventory_properties
            ADD COLUMN IF NOT EXISTS slot_type VARCHAR
        """)
        
        # Add new columns to energy_profiles
        conn.execute("""
            ALTER TABLE energy_profiles
            ADD COLUMN IF NOT EXISTS base_energy FLOAT,
            ADD COLUMN IF NOT EXISTS energy_drain FLOAT,
            ADD COLUMN IF NOT EXISTS peak_energy FLOAT
        """)
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def drop_old_columns():
    """Drop old columns that have been migrated."""
    conn = engine.connect()
    
    try:
        # Drop old JSON columns from items table
        conn.execute("""
            ALTER TABLE items
            DROP COLUMN IF EXISTS tech_tags,
            DROP COLUMN IF EXISTS effects,
            DROP COLUMN IF EXISTS materials,
            DROP COLUMN IF EXISTS icon,
            DROP COLUMN IF EXISTS image_3d
        """)
    except Exception as e:
        print(f"Error dropping old columns: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate() 