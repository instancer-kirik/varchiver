# SQLAlchemy models for inventory system
# Compatible with PostgreSQL (preferred) and SQLite (fallback)
# For PostgreSQL, ensure you have 'psycopg2' and use the 'postgresql+psycopg2://' URL
# For SQLite, use 'sqlite:///' URL

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
import sqlalchemy

Base = declarative_base()

# Use JSONB for PostgreSQL, fallback to JSON for SQLite
# Guard against potential errors if sqlalchemy.engine is not available during linting or partial loading
try:
    if sqlalchemy.engine.url.make_url('sqlite:///').get_backend_name() == 'postgresql':
        JSONType = JSONB
    else:
        from sqlalchemy import JSON as JSONType # type: ignore
except AttributeError: # Fallback for environments where sqlalchemy.engine might not be fully available
    try:
        from sqlalchemy import JSON as JSONType # type: ignore
    except ImportError:
        JSONType = String


# Association tables for many-to-many relationships
item_tags = Table(
    "item_tags", Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

item_materials = Table(
    "item_materials", Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id"), primary_key=True)
)

item_effects = Table(
    "item_effects", Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
    Column("effect_id", Integer, ForeignKey("effects.id"), primary_key=True)
)

item_compatibility_tags = Table(
    "item_compatibility_tags", Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
    Column("compatibility_tag_id", Integer, ForeignKey("compatibility_tags.id"), primary_key=True)
)

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    # items relationship defined in Item class via back_populates

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    # items relationship defined in Item class via back_populates

class Effect(Base):
    __tablename__ = "effects"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    # items relationship defined in Item class via back_populates

class CompatibilityTag(Base):
    __tablename__ = "compatibility_tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    # items relationship defined in Item class via back_populates

class Blueprint(Base):
    __tablename__ = "blueprints"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    recipe_json = Column(JSONType, nullable=True) # Contains the actual recipe steps/components
    manufacture_time = Column(Float, nullable=True) # Base time to craft

    # New fields for Blueprint (as requested by user)
    rarity = Column(String, nullable=True) # e.g., "common_schematic", "rare_data"
    crafting_time_modifier = Column(Float, nullable=True) # Multiplier for base time
    required_tools_or_facilities = Column(JSONType, nullable=True) # List of tool/facility IDs

    # Relationship: An item might be produced by this blueprint
    # This is implicitly handled if an Item has a blueprint_id linking to this.
    # items = relationship("Item", back_populates="blueprint") # This suggests a blueprint can make multiple DIFFERENT items, or one item can come from multiple BPs.
                                                            # The current Item.blueprint_id suggests one BP per item. Let's stick to Item.blueprint_id for now.

class UpgradePath(Base):
    __tablename__ = "upgrade_paths"
    id = Column(Integer, primary_key=True)
    source_item_id = Column(Integer, ForeignKey("items.id")) # Changed from source_id to be more explicit
    target_item_id = Column(Integer, ForeignKey("items.id")) # Changed from target_id
    method = Column(String, nullable=True)  # 'forge', 'combine', 'tech-lab'
    cost = Column(Float, nullable=True)
    required_blueprint_id = Column(Integer, ForeignKey("blueprints.id"), nullable=True) # An upgrade might require a blueprint

    source_item = relationship("Item", foreign_keys=[source_item_id], backref="upgrades_from")
    target_item = relationship("Item", foreign_keys=[target_item_id], backref="upgrades_to")
    required_blueprint = relationship("Blueprint") # Changed from 'blueprint' to 'required_blueprint'

class InventoryProperties(Base):
    __tablename__ = 'inventory_properties'
    id = Column(Integer, primary_key=True)
    stack_size = Column(Integer, default=1)
    max_stack_size = Column(Integer, default=1)
    slot_size = Column(JSONType, nullable=True)  # [width, height]
    slot_type = Column(String, default='standard', nullable=True)
    weight_kg = Column(Float, nullable=True)
    volume_l = Column(Float, nullable=True)
    item_id = Column(Integer, ForeignKey('items.id'), unique=True) # An item has one inv prop
    # item relationship defined in Item class via back_populates

class EnergyProfile(Base):
    __tablename__ = 'energy_profiles'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=True)
    input_energy = Column(String, nullable=True)
    output = Column(String, nullable=True)
    base_energy = Column(Float, nullable=True)
    energy_drain = Column(Float, nullable=True)
    peak_energy = Column(Float, nullable=True)
    energy_drain_per_ly = Column(Float, nullable=True)  # For FTL drives etc.
    energy_drain_per_second_active = Column(Float, nullable=True)  # Energy drain while device is active
    peak_energy_on_jump_initiation = Column(Float, nullable=True)  # For FTL drives etc.
    peak_energy_on_activation = Column(Float, nullable=True) # Energy surge on device activation
    modifiers = Column(JSONType, nullable=True)  # list of strings
    item_id = Column(Integer, ForeignKey('items.id'), unique=True) # An item has one energy profile
    # item relationship defined in Item class via back_populates

class ThermalProfile(Base):
    __tablename__ = 'thermal_profiles'
    id = Column(Integer, primary_key=True)
    sensitive = Column(Boolean, default=False)
    operating_range_c = Column(JSONType, nullable=True)  # [min, max]
    failure_temp_c = Column(Integer, nullable=True)
    cooling_required = Column(Boolean, default=False)
    item_id = Column(Integer, ForeignKey('items.id'), unique=True) # An item has one thermal profile
    # item relationship defined in Item class via back_populates

class ResonanceProfile(Base):
    __tablename__ = 'resonance_profiles'
    id = Column(Integer, primary_key=True)
    frequency_hz = Column(Float, nullable=True)
    resonance_type = Column(String, nullable=True)
    resonant_modes = Column(JSONType, nullable=True)  # list of strings
    item_id = Column(Integer, ForeignKey('items.id'), unique=True) # An item has one resonance profile
    # item relationship defined in Item class via back_populates

class ComputeModel(Base):
    __tablename__ = 'compute_models'
    id = Column(Integer, primary_key=True)
    function_id = Column(String, nullable=True)
    params = Column(JSONType, nullable=True)
    item_id = Column(Integer, ForeignKey('items.id'), unique=True) # An item has one compute model
    # item relationship defined in Item class via back_populates

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True) # Auto-incrementing primary key for the DB
    item_id = Column(String, index=True)  # User-defined unique ID from JSON, e.g., "resonator_t1"

    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    tech_tier = Column(String, nullable=True)
    energy_type = Column(String, nullable=True) # e.g. Resonant, Magitek
    category = Column(String, nullable=True) # e.g. Physical, Modular
    subcategory = Column(String, nullable=True) # e.g. Weapons, Cores
    type = Column(String, nullable=True) # e.g. tech_module, station_module (game-specific item typing)
    rarity = Column(String, nullable=True) # e.g. common, uncommon, rare
    durability = Column(Integer, nullable=True)
    manufacturing_cost = Column(Float, nullable=True)
    lore_notes = Column(Text, nullable=True)
    origin_faction = Column(String, nullable=True)
    function_script = Column(String, nullable=True) # e.g. "resonator_v1.lua"
    icon = Column(String, nullable=True)
    image_3d = Column(String, nullable=True)

    # === New fields start here ===
    # Worldbuilding & Lore
    historical_era = Column(String, nullable=True)
    cultural_significance = Column(JSONType, nullable=True) # String or list of strings
    discovery_location = Column(String, nullable=True)
    related_lore_entries = Column(JSONType, nullable=True) # List of strings (lore entry IDs)

    # Pack Planning & Ship Outfitting
    required_slots = Column(JSONType, nullable=True) # List of strings or objects
    power_draw_priority = Column(String, nullable=True) # String or int (stored as string for flexibility)
    crew_requirement = Column(JSONType, nullable=True) # Object: {"skill": "Eng", "level": 3, "count": 1}
    maintenance_schedule = Column(String, nullable=True)

    # Recipes & Blueprinting (fields directly on the item)
    # If an item itself IS a recipe/blueprint or has intrinsic crafting properties
    crafting_recipe_id = Column(String, nullable=True, index=True) # If this item unlocks/is a recipe
    deconstruct_yield = Column(JSONType, nullable=True) # List of objects: [{"item_id": "scrap_a", "qty": 2}]
    research_prerequisites = Column(JSONType, nullable=True) # List of strings (research IDs)

    # General Utility & Future-Proofing
    variant_of = Column(String, ForeignKey('items.item_id'), nullable=True) # Item_id of the base item it's a variant of
    status_effects = Column(JSONType, nullable=True) # List of objects applied on equip/use
    legal_status = Column(JSONType, nullable=True) # String or object: {"faction_X": "Illegal"}
    
    # Considerations from INVENTORY_HEADERS.md
    preferred_backpack_modes = Column(JSONType, nullable=True) # List of strings
    environmental_sensitivities = Column(JSONType, nullable=True) # List of strings e.g. ["high_radiation"]
    # === New fields end here ===

    # Relationships (One-to-One, cascade deletes if item is deleted)
    inventory_properties = relationship('InventoryProperties', uselist=False, backref="item", cascade="all, delete-orphan")
    energy_profile = relationship('EnergyProfile', uselist=False, backref="item", cascade="all, delete-orphan")
    thermal_profile = relationship('ThermalProfile', uselist=False, backref="item", cascade="all, delete-orphan")
    resonance_profile = relationship('ResonanceProfile', uselist=False, backref="item", cascade="all, delete-orphan")
    compute_model = relationship('ComputeModel', uselist=False, backref="item", cascade="all, delete-orphan")
    
    # Relationship (One-to-Many from Blueprint's perspective, or One-to-One from Item's perspective)
    # An item can be the result of one blueprint.
    blueprint_id = Column(Integer, ForeignKey('blueprints.id'), nullable=True)
    blueprint = relationship('Blueprint', backref="produced_items") # Changed backref

    # Relationships (Many-to-Many)
    tags = relationship('Tag', secondary=item_tags, backref="items")
    materials = relationship('Material', secondary=item_materials, backref="items")
    effects = relationship('Effect', secondary=item_effects, backref="items")
    compatibility_tags = relationship('CompatibilityTag', secondary=item_compatibility_tags, backref="items")

    # For UpgradePath (source_item and target_item relationships are defined in UpgradePath via backref)

    def __repr__(self):
        return f"<Item(item_id='{self.item_id}', name='{self.name}')>"
    
    __table_args__ = (
        UniqueConstraint('item_id', name='uq_items_item_id'),
    )

# Add back_populates to other sides of relationships if using bidirectional relationships explicitly.
# For simple backrefs as used above, SQLAlchemy handles the other side.
# Example: If Tag had `items = relationship("Item", secondary=item_tags, back_populates="tags")`
# then Item must have `tags = relationship("Tag", secondary=item_tags, back_populates="items")`
# Current setup uses backref on Item's relationships for many-to-many, and on child tables for one-to-one.
# This means Tag, Material, Effect, CompatibilityTag don't need explicit 'items' relationship if backref is sufficient.
# To be explicit for clarity (matching user's original style for Tag):
Tag.items = relationship("Item", secondary=item_tags, back_populates="tags")
Material.items = relationship("Item", secondary=item_materials, back_populates="materials")
Effect.items = relationship("Item", secondary=item_effects, back_populates="effects")
CompatibilityTag.items = relationship("Item", secondary=item_compatibility_tags, back_populates="compatibility_tags")

Item.tags = relationship('Tag', secondary=item_tags, back_populates="items")
Item.materials = relationship('Material', secondary=item_materials, back_populates="items")
Item.effects = relationship('Effect', secondary=item_effects, back_populates="items")
Item.compatibility_tags = relationship('CompatibilityTag', secondary=item_compatibility_tags, back_populates="items")

# Clean up UpgradePath relationships slightly
# Item.upgrade_paths_from is now source_item's backref
# Item.upgrade_paths_to is now target_item's backref
# Item.blueprint relationship is now Blueprint.produced_items

# One-to-one backrefs:
# InventoryProperties.item defined by Item.inventory_properties backref
# EnergyProfile.item defined by Item.energy_profile backref
# etc. for ThermalProfile, ResonanceProfile, ComputeModel.