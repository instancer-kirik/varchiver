from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QWidget, QGridLayout, QFrame, QDialogButtonBox,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
import os

class PackEditorDialog(QDialog):
    def __init__(self, inventory_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pack Editor")
        self.setMinimumSize(1100, 700)
        self.inventory_items = inventory_items
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        main_layout = QHBoxLayout()

        # Inventory QTreeWidget (left)
        self.inventory_tree = QTreeWidget()
        self.inventory_tree.setHeaderLabels(["Item", "Type", "Tier"])
        self.populate_inventory_tree()
        self.inventory_tree.setColumnWidth(0, 220)
        self.inventory_tree.setColumnWidth(1, 80)
        self.inventory_tree.setColumnWidth(2, 60)
        main_layout.addWidget(self.inventory_tree, 2)

        # Packs/layers (right)
        self.packs_tabs = QTabWidget()
        for i in range(2):  # Example: 2 packs/layers
            pack_widget = QWidget()
            pack_layout = QVBoxLayout(pack_widget)
            pack_list = QListWidget()
            # TODO: Populate pack list with items (drag target)
            pack_layout.addWidget(pack_list)
            self.packs_tabs.addTab(pack_widget, f"Pack {i+1}")
        main_layout.addWidget(self.packs_tabs, 3)

        layout.addLayout(main_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def populate_inventory_tree(self):
        for item in self.inventory_items:
            icon = self.load_icon(item.get('icon'))
            tree_item = QTreeWidgetItem([
                item.get('name', 'Unknown'),
                item.get('type', ''),
                item.get('tech_tier', '')
            ])
            if icon:
                tree_item.setIcon(0, icon)
            # Expandable children: ingredients/resources/recipes/sourcecodeurl/localdir
            if item.get('materials'):
                mat_item = QTreeWidgetItem(["Ingredients/Resources"])
                for mat in item['materials']:
                    mat_item.addChild(QTreeWidgetItem([mat]))
                tree_item.addChild(mat_item)
            if item.get('effects'):
                eff_item = QTreeWidgetItem(["Effects"])
                for eff in item['effects']:
                    eff_item.addChild(QTreeWidgetItem([eff]))
                tree_item.addChild(eff_item)
            if item.get('recipe'):
                rec_item = QTreeWidgetItem(["Recipe/BP"])
                for ingr in item['recipe']:
                    rec_item.addChild(QTreeWidgetItem([ingr]))
                tree_item.addChild(rec_item)
            if item.get('sourcecodeurl'):
                src_item = QTreeWidgetItem([f"Source: {item['sourcecodeurl']}"])
                tree_item.addChild(src_item)
            if item.get('localdir'):
                dir_item = QTreeWidgetItem([f"Local: {item['localdir']}"])
                tree_item.addChild(dir_item)
            self.inventory_tree.addTopLevelItem(tree_item)

    def load_icon(self, icon_path):
        if not icon_path:
            return None
        # Try PNG first, then SVG
        for ext in (".png", ".svg"):
            path = icon_path if icon_path.endswith(ext) else icon_path.replace(".svg", ext).replace(".png", ext)
            if os.path.exists(path):
                return QIcon(path)
        return None 