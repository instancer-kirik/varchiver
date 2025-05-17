from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import json # For handling JSON stringification if needed

class InventoryTableModel(QStandardItemModel):
    """
    Table/Tree model for inventory items, supporting expandable rows for details.
    """
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.setHorizontalHeaderLabels([
            "Name", "Category", "Type", "Rarity", "Origin Faction", "Weight (kg)", "Volume (L)"
        ])
        self.populate_model()

    def populate_model(self):
        self.setRowCount(0)
        for item in self.items:
            row = [
                QStandardItem(item.get('name', 'Unknown')),
                QStandardItem(item.get('category', 'Unknown')),
                QStandardItem(item.get('type', 'Unknown')),
                QStandardItem(item.get('rarity', 'common')),
                QStandardItem(item.get('origin_faction', 'Unknown')),
                QStandardItem(str(item.get('inventory_properties', {}).get('weight_kg', 0))),
                QStandardItem(str(item.get('inventory_properties', {}).get('volume_l', 0))),
            ]
            parent_item_for_details = row[0] # Use the QStandardItem for Name to append children
            
            # Add details as child rows (expandable)
            details_to_add = []
            # Key from item dict, Label for UI
            detail_fields_map = {
                'description': "Description",
                'tech_tier': "Tech Tier",
                'energy_type': "Energy Type",
                'lore_notes': "Lore Notes",
                'historical_era': "Historical Era",
                'discovery_location': "Discovery Location",
                'maintenance_schedule': "Maintenance",
                'power_draw_priority': "Power Priority",
                'function_script': "Function Script",
                'crafting_recipe_id': "Crafting Recipe ID",
                'variant_of': "Variant Of",
                'legal_status': "Legal Status",
                'cultural_significance': "Cultural Significance",
                'crew_requirement': "Crew Requirement"
            }

            for field_key, field_label in detail_fields_map.items():
                value = item.get(field_key)
                if value is not None: # Check for None explicitly, empty strings are fine
                    if isinstance(value, (list, dict)):
                        details_to_add.append([QStandardItem(field_label), QStandardItem(json.dumps(value))])
                    else:
                        details_to_add.append([QStandardItem(field_label), QStandardItem(str(value))])
            
            # Special handling for nested properties if needed
            if item.get('energy_profile', {}).get('type'):
                # Check if already added via detail_fields_map to avoid duplication if 'energy_type' (top-level) was the same
                # This check is a bit simplistic as 'energy_type' in energy_profile might be different
                # A more robust check would be to see if a child with label "Energy Profile Type" already exists.
                # For now, let's assume direct mapping is primary
                if not any(detail[0].text() == "Energy Profile Type" for detail in details_to_add):
                     details_to_add.append([QStandardItem("Energy Profile Type"), QStandardItem(item['energy_profile']['type'])])

            if item.get('thermal_profile', {}).get('sensitive') is not None:
                if not any(detail[0].text() == "Thermal Sensitive" for detail in details_to_add):
                    details_to_add.append([QStandardItem("Thermal Sensitive"), QStandardItem(str(item['thermal_profile']['sensitive']))])
            
            # Display blueprint info if present
            blueprint_info = item.get('blueprint')
            if blueprint_info:
                details_to_add.append([QStandardItem("Blueprint Name"), QStandardItem(blueprint_info.get('name', 'N/A'))])
                details_to_add.append([QStandardItem("Blueprint Rarity"), QStandardItem(blueprint_info.get('rarity', 'N/A'))])

            for detail_row_items in details_to_add:
                parent_item_for_details.appendRow(detail_row_items)
            
            self.appendRow(row)

    def update_items(self, items):
        self.items = items
        self.populate_model() 