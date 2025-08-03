"""Database migration script for inventory system."""

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy
import os

# Import Base from models
from .models import Base

# Database URL from environment or default to SQLite
DATABASE_URL = os.environ.get('INVENTORY_DB_URL', 'sqlite:///inventory.db')
engine = create_engine(DATABASE_URL)

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
    # Create all tables defined in models.py using Base.metadata
    Base.metadata.create_all(engine)

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
            ADD COLUMN IF NOT EXISTS slot_type VARCHAR,
            ADD COLUMN IF NOT EXISTS tech_attributes JSONB
        """)
            ADD COLUMN IF NOT EXISTS phase_state VARCHAR,
            ADD COLUMN IF NOT EXISTS storage_capacity FLOAT,
            ADD COLUMN IF NOT EXISTS efficiency FLOAT,
            ADD COLUMN IF NOT EXISTS release_rate FLOAT,
            ADD COLUMN IF NOT EXISTS momentum_conversion FLOAT,
            ADD COLUMN IF NOT EXISTS max_angular_velocity_dps FLOAT,
            ADD COLUMN IF NOT EXISTS momentum_transfer_efficiency FLOAT,
            ADD COLUMN IF NOT EXISTS inertia_modulation_factor FLOAT,
            ADD COLUMN IF NOT EXISTS ion_flow_rate_max_mol_s FLOAT,
            ADD COLUMN IF NOT EXISTS max_supported_modules_simultaneously INTEGER,
            ADD COLUMN IF NOT EXISTS module_compatibility_database_version VARCHAR,
            ADD COLUMN IF NOT EXISTS module_hot_swap_protocol_timeout_ms INTEGER,
            ADD COLUMN IF NOT EXISTS swap_time_reduction_s FLOAT,
            ADD COLUMN IF NOT EXISTS efficiency_bonus_percent_per_module_match FLOAT
        """)
        
        # Add new columns to energy_profiles
        conn.execute("""
            ALTER TABLE energy_profiles
            ADD COLUMN IF NOT EXISTS base_energy FLOAT,
            ADD COLUMN IF NOT EXISTS energy_drain FLOAT,
            ADD COLUMN IF NOT EXISTS peak_energy FLOAT,
            ADD COLUMN IF NOT EXISTS tech_attributes JSONB
        """)
            ADD COLUMN IF NOT EXISTS power_output_gw FLOAT,
            ADD COLUMN IF NOT EXISTS energy_conversion_efficiency_target FLOAT,
            ADD COLUMN IF NOT EXISTS max_ftl_speed_c_equivalent FLOAT,
            ADD COLUMN IF NOT EXISTS charge_time_minutes FLOAT,
            ADD COLUMN IF NOT EXISTS max_jump_range_ly_single FLOAT,
            ADD COLUMN IF NOT EXISTS navigation_accuracy_error_margin_percent FLOAT,
            ADD COLUMN IF NOT EXISTS bubble_stability_threshold_min FLOAT,
            ADD COLUMN IF NOT EXISTS max_force_newtons FLOAT,
            ADD COLUMN IF NOT EXISTS range_m FLOAT,
            ADD COLUMN IF NOT EXISTS beam_width_m FLOAT,
            ADD COLUMN IF NOT EXISTS max_beam_range_m FLOAT,
            ADD COLUMN IF NOT EXISTS beam_focus_cone_angle_degrees FLOAT,
            ADD COLUMN IF NOT EXISTS power_allocation_efficiency FLOAT,
            ADD COLUMN IF NOT EXISTS lift_capacity_kg FLOAT,
            ADD COLUMN IF NOT EXISTS force_newtons FLOAT,
            ADD COLUMN IF NOT EXISTS mana_efficiency FLOAT,
            ADD COLUMN IF NOT EXISTS spell_stability FLOAT,
            ADD COLUMN IF NOT EXISTS conversion_ratio FLOAT,
            ADD COLUMN IF NOT EXISTS field_strength FLOAT,
            ADD COLUMN IF NOT EXISTS spatial_resolution FLOAT,
            ADD COLUMN IF NOT EXISTS quantum_stability FLOAT,
            ADD COLUMN IF NOT EXISTS field_range FLOAT
        """)
        
        # Add new columns to thermal_profiles
        conn.execute("""
            ALTER TABLE thermal_profiles
            ADD COLUMN IF NOT EXISTS heat_dissipated_kj FLOAT,
            ADD COLUMN IF NOT EXISTS min_temp_c FLOAT,
            ADD COLUMN IF NOT EXISTS max_temp_c FLOAT,
            ADD COLUMN IF NOT EXISTS thermal_efficiency_cop FLOAT,
            ADD COLUMN IF NOT EXISTS target_temperature_range_c JSONB,
            ADD COLUMN IF NOT EXISTS max_cooling_capacity_kw FLOAT,
            ADD COLUMN IF NOT EXISTS max_heating_capacity_kw FLOAT,
            ADD COLUMN IF NOT EXISTS cold_factor FLOAT
        """)
        
        # Add new columns to resonance_profiles
        conn.execute("""
            ALTER TABLE resonance_profiles
            ADD COLUMN IF NOT EXISTS resonance_signature JSONB,
            ADD COLUMN IF NOT EXISTS harmonic_index FLOAT,
            ADD COLUMN IF NOT EXISTS frequency_matrix JSONB,
            ADD COLUMN IF NOT EXISTS interference_map JSONB,
            ADD COLUMN IF NOT EXISTS oscillation_frequency_target_hz FLOAT,
            ADD COLUMN IF NOT EXISTS portal_stability_threshold_min FLOAT,
            ADD COLUMN IF NOT EXISTS resonance_frequency_target_hz FLOAT,
            ADD COLUMN IF NOT EXISTS harmonic_series JSONB,
            ADD COLUMN IF NOT EXISTS resonance_quality FLOAT
        """)
        
        # Add new columns to compute_models
        conn.execute("""
            ALTER TABLE compute_models
            ADD COLUMN IF NOT EXISTS mass_limit FLOAT,
            ADD COLUMN IF NOT EXISTS duration FLOAT,
            ADD COLUMN IF NOT EXISTS stability_rating FLOAT,
            ADD COLUMN IF NOT EXISTS range_per_hop FLOAT,
            ADD COLUMN IF NOT EXISTS cooldown FLOAT,
            ADD COLUMN IF NOT EXISTS phase_sync FLOAT,
            ADD COLUMN IF NOT EXISTS time_window FLOAT,
            ADD COLUMN IF NOT EXISTS memory_payload INTEGER,
            ADD COLUMN IF NOT EXISTS loop_cost FLOAT,
            ADD COLUMN IF NOT EXISTS speed_multiplier FLOAT,
            ADD COLUMN IF NOT EXISTS radius FLOAT,
            ADD COLUMN IF NOT EXISTS drift_penalty FLOAT,
            ADD COLUMN IF NOT EXISTS entropy_output FLOAT,
            ADD COLUMN IF NOT EXISTS subversion_depth FLOAT,
            ADD COLUMN IF NOT EXISTS charge_limit INTEGER,
            ADD COLUMN IF NOT EXISTS anchor_stability FLOAT,
            ADD COLUMN IF NOT EXISTS reacquire_time FLOAT,
            ADD COLUMN IF NOT EXISTS max_mass FLOAT,
            ADD COLUMN IF NOT EXISTS distortion_index FLOAT,
            ADD COLUMN IF NOT EXISTS collapse_risk FLOAT,
            ADD COLUMN IF NOT EXISTS target_lock FLOAT,
            ADD COLUMN IF NOT EXISTS reflection_delay FLOAT,
            ADD COLUMN IF NOT EXISTS decoherence_rate FLOAT,
            ADD COLUMN IF NOT EXISTS fork_count INTEGER,
            ADD COLUMN IF NOT EXISTS merge_cost FLOAT,
            ADD COLUMN IF NOT EXISTS risk_threshold FLOAT,
            ADD COLUMN IF NOT EXISTS decay_rate FLOAT,
            ADD COLUMN IF NOT EXISTS replica_strength FLOAT,
            ADD COLUMN IF NOT EXISTS usage_limit INTEGER,
            ADD COLUMN IF NOT EXISTS target_species JSONB,
            ADD COLUMN IF NOT EXISTS signal_pattern JSONB,
            ADD COLUMN IF NOT EXISTS battery_life FLOAT,
            ADD COLUMN IF NOT EXISTS entangle_rate FLOAT,
            ADD COLUMN IF NOT EXISTS ethical_rating FLOAT,
            ADD COLUMN IF NOT EXISTS capture_radius FLOAT,
            ADD COLUMN IF NOT EXISTS power_drain FLOAT,
            ADD COLUMN IF NOT EXISTS ecological_disruption FLOAT,
            ADD COLUMN IF NOT EXISTS projection_duration FLOAT,
            ADD COLUMN IF NOT EXISTS decoy_type VARCHAR,
            ADD COLUMN IF NOT EXISTS field_signature JSONB,
            ADD COLUMN IF NOT EXISTS release_cycle FLOAT,
            ADD COLUMN IF NOT EXISTS biomass_capacity FLOAT,
            ADD COLUMN IF NOT EXISTS tension_threshold FLOAT,
            ADD COLUMN IF NOT EXISTS species_filter JSONB,
            ADD COLUMN IF NOT EXISTS trap_window FLOAT,
            ADD COLUMN IF NOT EXISTS gravity_field FLOAT,
            ADD COLUMN IF NOT EXISTS scent_profile JSONB,
            ADD COLUMN IF NOT EXISTS coverage_area FLOAT,
            ADD COLUMN IF NOT EXISTS species_ids JSONB,
            ADD COLUMN IF NOT EXISTS camouflage_mode VARCHAR,
            ADD COLUMN IF NOT EXISTS behavior_tree JSONB,
            ADD COLUMN IF NOT EXISTS flight_time FLOAT,
            ADD COLUMN IF NOT EXISTS node_count INTEGER,
            ADD COLUMN IF NOT EXISTS ai_model VARCHAR,
            ADD COLUMN IF NOT EXISTS recovery_protocol VARCHAR,
            ADD COLUMN IF NOT EXISTS collection_type VARCHAR,
            ADD COLUMN IF NOT EXISTS biomass_rate FLOAT,
            ADD COLUMN IF NOT EXISTS preservation_quality FLOAT,
            ADD COLUMN IF NOT EXISTS vibration_profile JSONB,
            ADD COLUMN IF NOT EXISTS depth_range FLOAT,
            ADD COLUMN IF NOT EXISTS creature_type VARCHAR
        """)
        
        # Add tech_attributes to thermal_profiles
        conn.execute("""
            ALTER TABLE thermal_profiles
            ADD COLUMN IF NOT EXISTS tech_attributes JSONB
        """)
        
        # Add tech_attributes to resonance_profiles
        conn.execute("""
            ALTER TABLE resonance_profiles
            ADD COLUMN IF NOT EXISTS tech_attributes JSONB
        """)
        
        # Add tech_attributes to compute_models
        conn.execute("""
            ALTER TABLE compute_models
            ADD COLUMN IF NOT EXISTS tech_attributes JSONB
        """)
        
        # Add tech_category to items
        conn.execute("""
            ALTER TABLE items
            ADD COLUMN IF NOT EXISTS tech_category VARCHAR
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