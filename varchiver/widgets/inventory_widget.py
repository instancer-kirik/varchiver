from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGridLayout, QScrollArea, QFrame,
    QComboBox, QLineEdit, QGroupBox, QCheckBox,
 QDialog, QDialogButtonBox, QFormLayout,
    QTabWidget, QTextEdit, QTreeView
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor
import json
import yaml

import os
from .inventory_table_model import InventoryTableModel
from .pack_editor_dialog import PackEditorDialog
# Add SQLAlchemy imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from varchiver.inventory.models import Item, InventoryProperties, EnergyProfile, ThermalProfile, ResonanceProfile, Blueprint, CompatibilityTag, ComputeModel, Tag, Material, Effect

# Set up SQLAlchemy session (reuse import_json_to_db.py logic)
DATABASE_URL = os.environ.get('INVENTORY_DB_URL', 'sqlite:///inventory.db')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class ItemDetailsDialog(QDialog):
    """Dialog for displaying detailed item information."""
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setWindowTitle(f"Item Details: {item_data.get('name', 'Unknown')}")
        self.setMinimumWidth(600)
        self.setup_ui()
        
    def _format_display_data(self, data):
        """Helper to format data (str, list, dict) for display in QLabel or QTextEdit."""
        if isinstance(data, (list, dict)):
            return json.dumps(data, indent=2)
        return str(data) if data is not None else "N/A"

    def _add_row_to_form(self, layout, label_text, data_value):
        """Helper to add a row to a QFormLayout, handling None values."""
        layout.addRow(label_text, QLabel(self._format_display_data(data_value)))
    
    def _add_multiline_row_to_form(self, layout, label_text, data_value):
        """Helper to add a potentially multiline row (using QTextEdit) to a QFormLayout."""
        text_edit = QTextEdit()
        text_edit.setPlainText(self._format_display_data(data_value))
        text_edit.setReadOnly(True)
        text_edit.setMaximumHeight(100) # Optional: constrain height
        layout.addRow(label_text, text_edit)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        tab_widget = QTabWidget()

        # Basic Info Tab (enhanced)
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        self._add_row_to_form(basic_layout, "Name:", self.item_data.get('name', 'Unknown'))
        self._add_multiline_row_to_form(basic_layout, "Description:", self.item_data.get('description', ''))
        self._add_row_to_form(basic_layout, "Tech Tier:", self.item_data.get('tech_tier', 'Unknown'))
        self._add_row_to_form(basic_layout, "Category:", self.item_data.get('category', 'Unknown'))
        self._add_row_to_form(basic_layout, "Subcategory:", self.item_data.get('subcategory', 'Unknown'))
        self._add_row_to_form(basic_layout, "Type:", self.item_data.get('type', 'Unknown'))
        self._add_row_to_form(basic_layout, "Rarity:", self.item_data.get('rarity', 'common'))
        self._add_row_to_form(basic_layout, "Durability:", self.item_data.get('durability'))
        self._add_row_to_form(basic_layout, "Manufacturing Cost:", self.item_data.get('manufacturing_cost'))
        self._add_row_to_form(basic_layout, "Icon:", self.item_data.get('icon'))
        self._add_row_to_form(basic_layout, "3D Image:", self.item_data.get('image_3d'))
        self._add_row_to_form(basic_layout, "Function Script:", self.item_data.get('function_script'))
        tab_widget.addTab(basic_tab, "Basic Info")
        
        # Inventory Properties Tab
        inventory_tab = QWidget()
        inventory_layout = QFormLayout(inventory_tab)
        inventory_props = self.item_data.get('inventory_properties', {})
        self._add_row_to_form(inventory_layout, "Stack Size:", f"{inventory_props.get('stack_size', 1)}/{inventory_props.get('max_stack_size', 1)}")
        slot_size_val = inventory_props.get('slot_size', [1, 1])
        self._add_row_to_form(inventory_layout, "Slot Size:", f"{slot_size_val[0]}x{slot_size_val[1]}" if isinstance(slot_size_val, list) and len(slot_size_val) == 2 else self._format_display_data(slot_size_val))
        self._add_row_to_form(inventory_layout, "Slot Type:", inventory_props.get('slot_type', 'standard'))
        self._add_row_to_form(inventory_layout, "Weight:", f"{inventory_props.get('weight_kg', 0)} kg")
        self._add_row_to_form(inventory_layout, "Volume:", f"{inventory_props.get('volume_l', 0)} L")
        tab_widget.addTab(inventory_tab, "Inventory")

        # Energy Profile Tab (enhanced)
        energy_tab = QWidget()
        energy_layout = QFormLayout(energy_tab)
        energy_profile = self.item_data.get('energy_profile', {})
        self._add_row_to_form(energy_layout, "Profile Type:", energy_profile.get('type', 'Unknown')) # Note: item_data also has a top-level 'energy_type'
        self._add_row_to_form(energy_layout, "Input Energy:", energy_profile.get('input_energy', 'Unknown'))
        self._add_row_to_form(energy_layout, "Output:", energy_profile.get('output', 'Unknown'))
        self._add_row_to_form(energy_layout, "Base Energy:", energy_profile.get('base_energy'))
        self._add_row_to_form(energy_layout, "Energy Drain:", energy_profile.get('energy_drain'))
        self._add_row_to_form(energy_layout, "Peak Energy:", energy_profile.get('peak_energy'))
        self._add_multiline_row_to_form(energy_layout, "Modifiers:", energy_profile.get('modifiers', []))
        tab_widget.addTab(energy_tab, "Energy")
        
        # Thermal Profile Tab
        thermal_tab = QWidget()
        thermal_layout = QFormLayout(thermal_tab)
        thermal_profile = self.item_data.get('thermal_profile', {})
        self._add_row_to_form(thermal_layout, "Sensitivity:", "Sensitive" if thermal_profile.get('sensitive', False) else "Insensitive")
        op_range = thermal_profile.get('operating_range_c', [0,0])
        self._add_row_to_form(thermal_layout, "Operating Range:", f"{op_range[0]}°C to {op_range[1]}°C" if isinstance(op_range, list) and len(op_range) == 2 else self._format_display_data(op_range))
        self._add_row_to_form(thermal_layout, "Failure Temperature:", f"{thermal_profile.get('failure_temp_c', 0)}°C")
        self._add_row_to_form(thermal_layout, "Cooling Required:", "Yes" if thermal_profile.get('cooling_required', False) else "No")
        tab_widget.addTab(thermal_tab, "Thermal")
        
        # Resonance Profile Tab
        resonance_tab = QWidget()
        resonance_layout = QFormLayout(resonance_tab)
        resonance_profile = self.item_data.get('resonance_profile', {})
        self._add_row_to_form(resonance_layout, "Frequency:", f"{resonance_profile.get('frequency_hz', 0)} Hz")
        self._add_row_to_form(resonance_layout, "Resonance Type:", resonance_profile.get('resonance_type', 'Unknown'))
        self._add_multiline_row_to_form(resonance_layout, "Resonant Modes:", resonance_profile.get('resonant_modes', []))
        tab_widget.addTab(resonance_tab, "Resonance")

        # Compute Model Tab
        compute_tab = QWidget()
        compute_layout = QFormLayout(compute_tab)
        compute_model = self.item_data.get('compute_model', {})
        self._add_row_to_form(compute_layout, "Function ID:", compute_model.get('function_id'))
        self._add_multiline_row_to_form(compute_layout, "Parameters:", compute_model.get('params'))
        tab_widget.addTab(compute_tab, "Compute")

        # Lore & Origin Tab (New)
        lore_tab = QWidget()
        lore_layout = QFormLayout(lore_tab)
        self._add_row_to_form(lore_layout, "Historical Era:", self.item_data.get('historical_era'))
        self._add_multiline_row_to_form(lore_layout, "Cultural Significance:", self.item_data.get('cultural_significance'))
        self._add_row_to_form(lore_layout, "Discovery Location:", self.item_data.get('discovery_location'))
        self._add_row_to_form(lore_layout, "Origin Faction:", self.item_data.get('origin_faction'))
        self._add_multiline_row_to_form(lore_layout, "Lore Notes:", self.item_data.get('lore_notes'))
        self._add_multiline_row_to_form(lore_layout, "Related Lore Entries:", self.item_data.get('related_lore_entries'))
        tab_widget.addTab(lore_tab, "Lore & Origin")

        # Logistics & Usage Tab (New)
        logistics_tab = QWidget()
        logistics_layout = QFormLayout(logistics_tab)
        self._add_multiline_row_to_form(logistics_layout, "Required Slots:", self.item_data.get('required_slots'))
        self._add_row_to_form(logistics_layout, "Power Draw Priority:", self.item_data.get('power_draw_priority'))
        self._add_multiline_row_to_form(logistics_layout, "Crew Requirement:", self.item_data.get('crew_requirement'))
        self._add_row_to_form(logistics_layout, "Maintenance Schedule:", self.item_data.get('maintenance_schedule'))
        self._add_multiline_row_to_form(logistics_layout, "Preferred Backpack Modes:", self.item_data.get('preferred_backpack_modes'))
        self._add_multiline_row_to_form(logistics_layout, "Environmental Sensitivities:", self.item_data.get('environmental_sensitivities'))
        self._add_multiline_row_to_form(logistics_layout, "Legal Status:", self.item_data.get('legal_status'))
        self._add_multiline_row_to_form(logistics_layout, "Status Effects:", self.item_data.get('status_effects'))
        tab_widget.addTab(logistics_tab, "Logistics & Usage")

        # Crafting & Variants Tab (New)
        crafting_tab = QWidget()
        crafting_layout = QFormLayout(crafting_tab)
        self._add_row_to_form(crafting_layout, "Is/Unlocks Recipe ID:", self.item_data.get('crafting_recipe_id'))
        self._add_multiline_row_to_form(crafting_layout, "Deconstruct Yield:", self.item_data.get('deconstruct_yield'))
        self._add_multiline_row_to_form(crafting_layout, "Research Prerequisites:", self.item_data.get('research_prerequisites'))
        self._add_row_to_form(crafting_layout, "Variant Of (Item ID):", self.item_data.get('variant_of'))
        
        blueprint_details = self.item_data.get('blueprint_details', {})
        if blueprint_details: # Only add blueprint section if details exist
            bp_group = QGroupBox("Produced by Blueprint")
            bp_layout = QFormLayout(bp_group)
            self._add_row_to_form(bp_layout, "Blueprint Name:", blueprint_details.get('name'))
            self._add_row_to_form(bp_layout, "Blueprint Rarity:", blueprint_details.get('rarity'))
            self._add_row_to_form(bp_layout, "Manufacture Time:", blueprint_details.get('manufacture_time'))
            self._add_row_to_form(bp_layout, "Crafting Time Modifier:", blueprint_details.get('crafting_time_modifier'))
            self._add_multiline_row_to_form(bp_layout, "Required Tools/Facilities:", blueprint_details.get('required_tools_or_facilities'))
            self._add_multiline_row_to_form(bp_layout, "Recipe:", blueprint_details.get('recipe_json'))
            crafting_layout.addRow(bp_group)
        tab_widget.addTab(crafting_tab, "Crafting & Variants")

        # Tags & Compatibility Tab (New)
        tags_compatibility_tab = QWidget()
        tags_compatibility_layout = QFormLayout(tags_compatibility_tab)
        self._add_multiline_row_to_form(tags_compatibility_layout, "Tech Tags:", self.item_data.get('tech_tags'))
        self._add_multiline_row_to_form(tags_compatibility_layout, "Materials:", self.item_data.get('materials'))
        self._add_multiline_row_to_form(tags_compatibility_layout, "Effects:", self.item_data.get('effects'))
        self._add_multiline_row_to_form(tags_compatibility_layout, "Compatibility Tags:", self.item_data.get('compatibility_tags'))
        tab_widget.addTab(tags_compatibility_tab, "Tags & Compatibility")

        # Add tabs to widget
        layout.addWidget(tab_widget)
        
        # Add close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

class InventorySlot(QFrame):
    """A single inventory slot that can hold an item."""
    item_dropped = pyqtSignal(object)  # Signal emitted when an item is dropped here
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.setAcceptDrops(True)
        self.setMinimumSize(64, 64)
        self.setMaximumSize(64, 64)
        self.item = None
        
        # Create layout for the slot
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-inventory-item"):
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-inventory-item"):
            item_data = event.mimeData().data("application/x-inventory-item")
            self.item_dropped.emit(item_data)
            event.acceptProposedAction()

class InventoryItem(QFrame):
    """A draggable inventory item."""
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        
        # Set size based on slot_size
        slot_size = item_data.get('inventory_properties', {}).get('slot_size', [1, 1])
        self.setMinimumSize(60 * slot_size[0], 60 * slot_size[1])
        self.setMaximumSize(60 * slot_size[0], 60 * slot_size[1])
        
        # Set background color based on tech tier
        tech_tier_colors = {
            "Tier 1": "#4CAF50",  # Green
            "Tier 2": "#2196F3",  # Blue
            "Tier 3": "#9C27B0",  # Purple
            "Tier 4": "#FF9800"   # Orange
        }
        self.setStyleSheet(f"background-color: {tech_tier_colors.get(item_data.get('tech_tier', 'Tier 1'))};")
        
        # Create item display
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # Item name
        name_label = QLabel(item_data.get('name', 'Unknown'))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(name_label)
        
        # Tech tags if present
        if 'tech_tags' in item_data:
            tags_label = QLabel(', '.join(item_data['tech_tags']))
            tags_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tags_label.setStyleSheet("color: white; font-size: 8pt;")
            layout.addWidget(tags_label)
            
        # Stack size if stackable
        if item_data.get('inventory_properties', {}).get('stack_size', 1) > 1:
            stack_label = QLabel(str(item_data['inventory_properties']['stack_size']))
            stack_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
            stack_label.setStyleSheet("color: white; font-weight: bold;")
            layout.addWidget(stack_label)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setData("application/x-inventory-item", str(self.item_data).encode())
            drag.setMimeData(mime_data)
            
            # Create drag pixmap
            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            
            drag.exec()
            
    def mouseDoubleClickEvent(self, event):
        """Show item details dialog from double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = ItemDetailsDialog(self.item_data, self.parent())
            dialog.exec()

class InventoryWidget(QWidget):
    """The main inventory management widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = self.load_config()
        self.items = self.load_items_from_db()
        self.setup_ui()
        
    def load_config(self):
        """Load inventory configuration from YAML file."""
        # Path relative to this file (varchiver/widgets/inventory_widget.py)
        # Correct path should go up one level, then into 'inventory' directory
        config_path = os.path.join(os.path.dirname(__file__), '..', 'inventory', 'inventory_config.yaml')
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
            
    def load_items_from_db(self):
        """Load items from the database and convert to dicts for UI."""
        items = []
        # Eager load related entities to prevent N+1 query problems in a loop
        db_items = session.query(Item).options(
            joinedload(Item.inventory_properties),
            joinedload(Item.energy_profile),
            joinedload(Item.thermal_profile),
            joinedload(Item.resonance_profile),
            joinedload(Item.compute_model),
            joinedload(Item.tags),
            joinedload(Item.materials),
            joinedload(Item.effects),
            joinedload(Item.compatibility_tags), # Eager load new compatibility tags
            joinedload(Item.blueprint) # Eager load related blueprint
        ).all()

        for obj in db_items:
            item = {
                'id': obj.item_id,
                'name': obj.name,
                'description': obj.description,
                'tech_tier': obj.tech_tier,
                'energy_type': obj.energy_type,
                'category': obj.category,
                'subcategory': obj.subcategory,
                'type': obj.type,
                'rarity': obj.rarity,
                'durability': obj.durability,
                'manufacturing_cost': obj.manufacturing_cost,
                'lore_notes': obj.lore_notes,
                'origin_faction': obj.origin_faction,
                'function_script': obj.function_script,
                'icon': obj.icon,
                'image_3d': obj.image_3d,

                # Worldbuilding & Lore
                'historical_era': obj.historical_era,
                'cultural_significance': obj.cultural_significance,
                'discovery_location': obj.discovery_location,
                'related_lore_entries': obj.related_lore_entries,

                # Pack Planning & Ship Outfitting
                'required_slots': obj.required_slots,
                'power_draw_priority': obj.power_draw_priority,
                'crew_requirement': obj.crew_requirement,
                'maintenance_schedule': obj.maintenance_schedule,

                # Recipes & Blueprinting (fields directly on the item)
                'crafting_recipe_id': obj.crafting_recipe_id,
                'deconstruct_yield': obj.deconstruct_yield,
                'research_prerequisites': obj.research_prerequisites,

                # General Utility & Future-Proofing
                'variant_of': obj.variant_of,
                'status_effects': obj.status_effects,
                'legal_status': obj.legal_status,
                
                # Considerations from INVENTORY_HEADERS.md
                'preferred_backpack_modes': obj.preferred_backpack_modes,
                'environmental_sensitivities': obj.environmental_sensitivities,

                # Relationships (Many-to-Many)
                'tech_tags': [tag.name for tag in obj.tags] if obj.tags else [],
                'materials': [material.name for material in obj.materials] if obj.materials else [],
                'effects': [effect.name for effect in obj.effects] if obj.effects else [],
                'compatibility_tags': [ct.name for ct in obj.compatibility_tags] if obj.compatibility_tags else [],
            }
            
            # Inventory Properties
            if obj.inventory_properties:
                item['inventory_properties'] = {
                    'stack_size': obj.inventory_properties.stack_size,
                    'max_stack_size': obj.inventory_properties.max_stack_size,
                    'slot_size': obj.inventory_properties.slot_size, # This is JSON in DB
                    'slot_type': obj.inventory_properties.slot_type,
                    'weight_kg': obj.inventory_properties.weight_kg,
                    'volume_l': obj.inventory_properties.volume_l,
                }
            else:
                item['inventory_properties'] = {} # Ensure key exists
            
            # Energy Profile
            if obj.energy_profile:
                item['energy_profile'] = {
                    'type': obj.energy_profile.type,
                    'input_energy': obj.energy_profile.input_energy,
                    'output': obj.energy_profile.output,
                    'base_energy': obj.energy_profile.base_energy,
                    'energy_drain': obj.energy_profile.energy_drain,
                    'peak_energy': obj.energy_profile.peak_energy,
                    'modifiers': obj.energy_profile.modifiers or [],
                }
            else:
                item['energy_profile'] = {} # Ensure key exists
            
            # Thermal Profile
            if obj.thermal_profile:
                item['thermal_profile'] = {
                    'sensitive': obj.thermal_profile.sensitive,
                    'operating_range_c': obj.thermal_profile.operating_range_c, # This is JSON in DB
                    'failure_temp_c': obj.thermal_profile.failure_temp_c,
                    'cooling_required': obj.thermal_profile.cooling_required,
                }
            else:
                item['thermal_profile'] = {} # Ensure key exists
            
            # Resonance Profile
            if obj.resonance_profile:
                item['resonance_profile'] = {
                    'frequency_hz': obj.resonance_profile.frequency_hz,
                    'resonance_type': obj.resonance_profile.resonance_type,
                    'resonant_modes': obj.resonance_profile.resonant_modes or [],
                }
            else:
                item['resonance_profile'] = {} # Ensure key exists

            # Compute Model
            if obj.compute_model:
                item['compute_model'] = {
                    'function_id': obj.compute_model.function_id,
                    'params': obj.compute_model.params,
                }
            else:
                item['compute_model'] = {} # Ensure key exists

            # Blueprint Details (if item has an associated blueprint)
            if obj.blueprint:
                item['blueprint_details'] = {
                    'name': obj.blueprint.name,
                    'recipe_json': obj.blueprint.recipe_json,
                    'manufacture_time': obj.blueprint.manufacture_time,
                    'rarity': obj.blueprint.rarity,
                    'crafting_time_modifier': obj.blueprint.crafting_time_modifier,
                    'required_tools_or_facilities': obj.blueprint.required_tools_or_facilities
                }
            else:
                item['blueprint_details'] = {} # Ensure key exists
            
            items.append(item)
        return items
        
    def setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Add Pack Editor button
        self.pack_editor_btn = QPushButton("Pack Editor")
        self.pack_editor_btn.clicked.connect(self.open_pack_editor)
        toolbar.addWidget(self.pack_editor_btn)
        
        # Filter controls
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)
        
        # Tech tier filter
        self.tech_tier_combo = QComboBox()
        self.tech_tier_combo.addItems(['All Tiers'] + [tier['name'] for tier in self.config.get('tech_tiers', [])])
        filter_layout.addWidget(QLabel("Tech Tier:"))
        filter_layout.addWidget(self.tech_tier_combo)
        
        # Energy type filter
        self.energy_type_combo = QComboBox()
        self.energy_type_combo.addItems(['All Types'] + [type['name'] for type in self.config.get('energy_types', [])])
        filter_layout.addWidget(QLabel("Energy Type:"))
        filter_layout.addWidget(self.energy_type_combo)
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItems(['All Categories'] + [cat['name'] for cat in self.config.get('item_categories', [])])
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_combo)
        
        # Thermal profile filter
        self.thermal_combo = QComboBox()
        self.thermal_combo.addItems(['All'] + self.config.get('item_properties', {}).get('thermal_profiles', {}).get('sensitivity_levels', []))
        filter_layout.addWidget(QLabel("Thermal:"))
        filter_layout.addWidget(self.thermal_combo)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search items...")
        filter_layout.addWidget(self.search_box)
        
        toolbar.addWidget(filter_group)
        layout.addLayout(toolbar)
        
        # Tab widget for grid/table view
        self.view_tabs = QTabWidget()
        
        # Inventory grid (existing)
        self.inventory_scroll = QScrollArea()
        self.inventory_scroll.setWidgetResizable(True)
        self.inventory_grid = QWidget()
        self.grid_layout = QGridLayout(self.inventory_grid)
        self.grid_layout.setSpacing(2)
        grid_size = self.config.get('inventory_settings', {}).get('grid_size', {'rows': 8, 'columns': 8})
        self.create_inventory_grid(grid_size['rows'], grid_size['columns'])
        self.inventory_scroll.setWidget(self.inventory_grid)
        self.view_tabs.addTab(self.inventory_scroll, "Grid View")
        
        # Inventory table/tree view (new)
        self.table_view = QTreeView()
        self.table_model = InventoryTableModel(self.items)
        self.table_view.setModel(self.table_model)
        self.table_view.setRootIsDecorated(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.doubleClicked.connect(self.open_item_details_from_table)
        self.view_tabs.addTab(self.table_view, "Table View")
        
        layout.addWidget(self.view_tabs)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Connect filter signals
        self.tech_tier_combo.currentTextChanged.connect(self.apply_filters)
        self.energy_type_combo.currentTextChanged.connect(self.apply_filters)
        self.category_combo.currentTextChanged.connect(self.apply_filters)
        self.thermal_combo.currentTextChanged.connect(self.apply_filters)
        self.search_box.textChanged.connect(self.apply_filters)
        
        # Load sample items
        self.load_items()
        
    def create_inventory_grid(self, rows, cols):
        """Create a grid of inventory slots."""
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Create new grid
        for row in range(rows):
            for col in range(cols):
                slot = InventorySlot()
                slot.item_dropped.connect(self.handle_item_drop)
                self.grid_layout.addWidget(slot, row, col)
                
    def handle_item_drop(self, item_data):
        """Handle when an item is dropped into a slot."""
        # TODO: Implement item drop handling
        self.status_label.setText(f"Item dropped: {item_data}")
        
    def add_item(self, item_data):
        """Add an item to the inventory."""
        # Find first empty slot
        for i in range(self.grid_layout.count()):
            slot = self.grid_layout.itemAt(i).widget()
            if isinstance(slot, InventorySlot) and not slot.item:
                item = InventoryItem(item_data)
                slot.item = item
                slot.layout.addWidget(item)
                return True
        return False
        
    def load_items(self):
        """Load items into the inventory."""
        for item in self.items:
            self.add_item(item)
            
    def open_item_details_from_table(self, index):
        """Open item details dialog from table/tree view double-click."""
        row = index.row()
        # Only open for top-level items (not child/detail rows)
        if index.parent().isValid():
            return
        item_data = self.items[row]
        dialog = ItemDetailsDialog(item_data, self)
        dialog.exec()
            
    def apply_filters(self):
        """Apply current filters to the inventory."""
        # Get current filter values
        tech_tier = self.tech_tier_combo.currentText()
        energy_type = self.energy_type_combo.currentText()
        category = self.category_combo.currentText()
        thermal = self.thermal_combo.currentText()
        search_text = self.search_box.text().lower()
        
        filtered_items = []
        for item in self.items:
            # Apply filters
            if tech_tier != 'All Tiers' and item.get('tech_tier') != tech_tier:
                continue
            if energy_type != 'All Types' and item.get('energy_type') != energy_type:
                continue
            if category != 'All Categories' and item.get('category') != category:
                continue
            if thermal != 'All' and item.get('thermal_profile', {}).get('sensitive', False) != (thermal == 'sensitive'):
                continue
            if search_text and search_text not in item.get('name', '').lower():
                continue
            filtered_items.append(item)
        
        # Update grid view
        for i in range(self.grid_layout.count()):
            slot = self.grid_layout.itemAt(i).widget()
            if isinstance(slot, InventorySlot):
                while slot.layout.count():
                    item = slot.layout.takeAt(0).widget()
                    if item:
                        item.deleteLater()
                slot.item = None
        
        for item in filtered_items:
            self.add_item(item) 
        
        # Update table/tree view
        self.table_model.update_items(filtered_items) 

    def open_pack_editor(self):
        dialog = PackEditorDialog(self.items, self)
        dialog.exec() 