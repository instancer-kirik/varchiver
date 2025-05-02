"""Variable Calendar Widget for tracking and visualizing variables over time."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCalendarWidget,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QColorDialog, QDialog, QTextEdit, QScrollArea, QFrame, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QDateTime, QTimer
from PyQt6.QtGui import QColor, QPalette, QBrush, QTextCharFormat
from ..utils.variable_db import PostgresDatabase
from ..utils.config import Config
from .db_config_dialog import DatabaseConfigDialog

class VariableCalendarWidget(QWidget):
    """Main widget for variable calendar functionality."""
    
    # Signals
    variable_added = pyqtSignal(str, str, str)  # name, type, unit
    entry_added = pyqtSignal(str, object, object)  # variable_name, value, timestamp
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "calendar"  # or "list"
        
        # Load configuration
        self.config = Config()
        self.cal_config = self.config.get_variable_calendar_config()
        self.db_config = self.config.get_database_config()
        
        # Initialize database
        self.db = PostgresDatabase(
            dbname=self.db_config['dbname'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            host=self.db_config['host'],
            port=self.db_config['port']
        )
        
        # Try to connect to database
        try:
            self.db.connect()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(e)}")
        
        # Set up auto-refresh timer if enabled
        if self.cal_config['auto_refresh']:
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.update_views)
            self.refresh_timer.start(self.cal_config['refresh_interval'] * 1000)
        
        self.setup_ui()
        
        # Load initial data
        self.load_variables()
        self.update_views()
        
    def setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Top toolbar
        toolbar = QHBoxLayout()
        
        # View toggle button
        self.view_toggle = QPushButton("Toggle View")
        self.view_toggle.setCheckable(True)
        self.view_toggle.clicked.connect(self.toggle_view)
        toolbar.addWidget(self.view_toggle)
        
        # Variable selector
        self.variable_combo = QComboBox()
        self.variable_combo.addItem("Select Variable")
        toolbar.addWidget(self.variable_combo)
        
        # Add Variable button
        self.add_variable_btn = QPushButton("Add Variable")
        self.add_variable_btn.clicked.connect(self.show_add_variable_dialog)
        toolbar.addWidget(self.add_variable_btn)
        
        # Add Entry button
        self.add_entry_btn = QPushButton("Add Entry")
        self.add_entry_btn.clicked.connect(self.show_add_entry_dialog)
        toolbar.addWidget(self.add_entry_btn)
        
        # Context manager button
        self.context_btn = QPushButton("Manage Contexts")
        self.context_btn.clicked.connect(self.show_context_manager)
        toolbar.addWidget(self.context_btn)
        
        # Add database config button
        self.db_config_btn = QPushButton("Database Settings")
        self.db_config_btn.clicked.connect(self.show_db_config)
        toolbar.addWidget(self.db_config_btn)
        
        layout.addLayout(toolbar)
        
        # Initialize context tree widget (used in context manager dialog)
        # Although the dialog creates its own tree, having an instance member
        # might be intended for other uses or was a remnant. Let's ensure it exists.
        # If it's ONLY used in the dialog, this line isn't strictly needed there,
        # but helps prevent AttributeErrors if load_contexts is called early.
        self.context_tree = QTreeWidget() # Initialize the attribute
        
        # Stacked widget for different views
        self.stack = QStackedWidget()
        
        # Calendar view
        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.clicked.connect(self.on_date_selected)
        self.stack.addWidget(self.calendar_widget)
        
        # List view
        self.list_widget = QTreeWidget()
        self.list_widget.setHeaderLabels(["Date", "Variable", "Value", "Context", "Notes"])
        self.list_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.stack.addWidget(self.list_widget)
        
        layout.addWidget(self.stack)
        
        # Entry details section
        self.details_group = QGroupBox("Entry Details")
        details_layout = QVBoxLayout()
        
        # Table for showing entries
        self.entries_table = QTableWidget()
        self.entries_table.setColumnCount(4)
        self.entries_table.setHorizontalHeaderLabels(["Variable", "Value", "Context", "Notes"])
        self.entries_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        details_layout.addWidget(self.entries_table)
        
        self.details_group.setLayout(details_layout)
        layout.addWidget(self.details_group)
        
    def toggle_view(self):
        """Toggle between calendar and list view."""
        if self.stack.currentIndex() == 0:  # Calendar view
            self.stack.setCurrentIndex(1)  # Switch to list view
            self.view_toggle.setText("Show Calendar")
            self.update_list_view()
        else:
            self.stack.setCurrentIndex(0)  # Switch to calendar view
            self.view_toggle.setText("Show List")
            self.update_calendar_view()
            
    def show_add_variable_dialog(self):
        """Show dialog to add a new variable."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Variable")
        layout = QFormLayout(dialog)
        
        # Variable name
        name_input = QLineEdit()
        layout.addRow("Name:", name_input)
        
        # Variable type
        type_combo = QComboBox()
        type_combo.addItems(["numeric", "string", "boolean"])
        layout.addRow("Type:", type_combo)
        
        # Unit (optional)
        unit_input = QLineEdit()
        layout.addRow("Unit (optional):", unit_input)
        
        # Description
        desc_input = QTextEdit()
        desc_input.setMaximumHeight(100)
        layout.addRow("Description:", desc_input)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
        
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Add to database
                variable_id = self.db.add_variable(
                    name=name_input.text(),
                    type=type_combo.currentText(),
                    unit=unit_input.text(),
                    description=desc_input.toPlainText()
                )
                
                # Reload variables
                self.load_variables()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add variable: {str(e)}")
            
    def show_add_entry_dialog(self):
        """Show dialog to add a new entry."""
        if self.variable_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Warning", "Please select a variable first")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Entry")
        layout = QFormLayout(dialog)
        
        # Variable selector
        var_combo = QComboBox()
        var_combo.addItems([self.variable_combo.itemText(i) 
                           for i in range(1, self.variable_combo.count())])
        layout.addRow("Variable:", var_combo)
        
        # Value input (will change based on variable type)
        value_stack = QStackedWidget()
        
        # Numeric input
        num_input = QDoubleSpinBox()
        num_input.setRange(-1000000, 1000000)
        value_stack.addWidget(num_input)
        
        # String input
        str_input = QLineEdit()
        value_stack.addWidget(str_input)
        
        # Boolean input
        bool_combo = QComboBox()
        bool_combo.addItems(["True", "False"])
        value_stack.addWidget(bool_combo)
        
        layout.addRow("Value:", value_stack)
        
        # Context selector
        context_combo = QComboBox()
        context_combo.addItem("Select Context")
        layout.addRow("Context:", context_combo)
        
        # Notes
        notes_input = QTextEdit()
        notes_input.setMaximumHeight(100)
        layout.addRow("Notes:", notes_input)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
        
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Get variable ID
                var_name = var_combo.currentText()
                variables = self.db.get_variables()
                var_id = next(v['id'] for v in variables if v['name'] == var_name)
                
                # Get context ID if selected
                context_id = None
                if context_combo.currentIndex() > 0:
                    contexts = self.db.get_contexts()
                    context_id = next(c['id'] for c in contexts if c['name'] == context_combo.currentText())
                
                # Get value based on current input widget
                if value_stack.currentWidget() == num_input:
                    value = num_input.value()
                elif value_stack.currentWidget() == bool_combo:
                    value = bool_combo.currentText() == "True"
                else:
                    value = str_input.text()
                
                # Add to database
                self.db.add_entry(
                    variable_id=var_id,
                    timestamp=QDateTime.currentDateTime().toPyDateTime(),
                    value=value,
                    context_id=context_id,
                    notes=notes_input.toPlainText()
                )
                
                # Update views
                self.update_views()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add entry: {str(e)}")
            
    def show_context_manager(self):
        """Show dialog to manage contexts/labels."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Context Manager")
        layout = QVBoxLayout(dialog)
        
        # Re-use the instance member if desired, or create locally
        # If re-using, ensure it's cleared or managed appropriately
        # For simplicity of dialog, let's keep creating it locally in the dialog
        # and remove the load_contexts attempt to populate self.context_tree
        context_tree_local = QTreeWidget()
        context_tree_local.setHeaderLabels(["Name", "Color", "Description"])
        context_tree_local.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(context_tree_local)

        # Load contexts into the local tree for the dialog
        self._load_contexts_into_tree(context_tree_local)

        # Add context button
        # Pass the local tree to the add dialog so it can add items to it
        add_btn = QPushButton("Add Context")
        add_btn.clicked.connect(lambda: self.show_add_context_dialog(context_tree_local))
        layout.addWidget(add_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()
        # No need to reload contexts here unless add/delete modifies the DB
        # which they currently don't in the dialog's logic

    # Rename load_contexts to avoid confusion and make it dialog specific
    def _load_contexts_into_tree(self, tree_widget: QTreeWidget):
        """Load contexts from database into the provided tree widget."""
        try:
            contexts = self.db.get_contexts()
            tree_widget.clear()
            for ctx in contexts:
                item = QTreeWidgetItem(tree_widget)
                item.setText(0, ctx['name'])
                item.setText(1, ctx['color'] or '')
                item.setText(2, ctx['description'] or '')
                if ctx['color']:
                    item.setBackground(1, QBrush(QColor(ctx['color'])))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load contexts: {str(e)}")

    # Modify show_add_context_dialog to accept the tree and add to DB
    def show_add_context_dialog(self, target_tree: QTreeWidget):
        """Show dialog to add a new context."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Context")
        layout = QFormLayout(dialog)
        
        # Context name
        name_input = QLineEdit()
        layout.addRow("Name:", name_input)
        
        # Color picker
        color_btn = QPushButton("Select Color")
        selected_color = QColor("#FFFFFF") # Start with white
        color_btn.setStyleSheet(f"background-color: {selected_color.name()}")
        
        def pick_color():
            nonlocal selected_color # Modify the variable in outer scope
            color = QColorDialog.getColor(selected_color, dialog)
            if color.isValid():
                selected_color = color
                color_btn.setStyleSheet(f"background-color: {color.name()}")
                
        color_btn.clicked.connect(pick_color)
        layout.addRow("Color:", color_btn)
        
        # Description
        desc_input = QTextEdit()
        desc_input.setMaximumHeight(100)
        layout.addRow("Description:", desc_input)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
        
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            context_name = name_input.text()
            context_color = selected_color.name()
            context_desc = desc_input.toPlainText()
            
            if not context_name:
                 QMessageBox.warning(self, "Input Error", "Context name cannot be empty.")
                 return
                 
            try:
                # Add context to database
                context_id = self.db.add_context(
                    name=context_name,
                    color=context_color,
                    description=context_desc
                )
                
                # Add context to the dialog tree immediately
                item = QTreeWidgetItem(target_tree)
                item.setText(0, context_name)
                item.setText(1, context_color)
                item.setText(2, context_desc)
                item.setBackground(1, QBrush(selected_color))
                
                # We might need to refresh other parts of the UI that use contexts
                # For now, the context manager dialog is updated.
                # Consider emitting a signal if other widgets need updating.
                
            except Exception as e:
                 QMessageBox.critical(self, "Database Error", f"Failed to add context: {str(e)}")

    def on_date_selected(self, date):
        """Handle date selection in calendar."""
        self.update_entries_table(date)
        
    def update_entries_table(self, date):
        """Update entries table for selected date."""
        try:
            # Get entries for the selected date
            start_date = date.toPyDate()
            end_date = date.addDays(1).toPyDate()
            entries = self.db.get_entries(start_date, end_date)
            
            # Update table
            self.entries_table.setRowCount(len(entries))
            for i, entry in enumerate(entries):
                self.entries_table.setItem(i, 0, QTableWidgetItem(entry['variable_name']))
                self.entries_table.setItem(i, 1, QTableWidgetItem(str(entry['value'])))
                self.entries_table.setItem(i, 2, QTableWidgetItem(entry['context_name'] or ''))
                self.entries_table.setItem(i, 3, QTableWidgetItem(entry['notes'] or ''))
                
                # Set background color if context has color
                if entry['context_color']:
                    for col in range(4):
                        self.entries_table.item(i, col).setBackground(QBrush(QColor(entry['context_color'])))
                        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load entries: {str(e)}")
        
    def update_calendar_view(self):
        """Update calendar view with entry indicators."""
        try:
            # Get current month's entries
            current_date = self.calendar_widget.selectedDate()
            start_date = QDate(current_date.year(), current_date.month(), 1).toPyDate()
            end_date = QDate(current_date.year(), current_date.month() + 1, 1).addDays(-1).toPyDate()
            
            entries = self.db.get_entries(start_date, end_date)
            
            # Create a set of dates with entries
            dates_with_entries = set()
            for entry in entries:
                dates_with_entries.add(entry['timestamp'].date())
            
            # Update calendar format for dates with entries
            text_format = self.calendar_widget.dateTextFormat()
            for date in dates_with_entries:
                qdate = QDate(date.year, date.month, date.day)
                fmt = text_format.get(qdate, QTextCharFormat())
                fmt.setBackground(QBrush(QColor("#2196F3")))  # Light blue background
                fmt.setForeground(QBrush(QColor("#FFFFFF")))  # White text
                self.calendar_widget.setDateTextFormat(qdate, fmt)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update calendar: {str(e)}")
        
    def update_list_view(self):
        """Update list view with all entries."""
        try:
            # Get all entries for the current month
            current_date = QDate.currentDate()
            start_date = QDate(current_date.year(), current_date.month(), 1).toPyDate()
            end_date = QDate(current_date.year(), current_date.month() + 1, 1).addDays(-1).toPyDate()
            
            entries = self.db.get_entries(start_date, end_date)
            
            # Update list widget
            self.list_widget.clear()
            for entry in entries:
                item = QTreeWidgetItem(self.list_widget)
                item.setText(0, entry['timestamp'].strftime(self.cal_config['date_format']))
                item.setText(1, entry['variable_name'])
                item.setText(2, str(entry['value']))
                item.setText(3, entry['context_name'] or '')
                item.setText(4, entry['notes'] or '')
                
                # Set background color if context has color
                if entry['context_color']:
                    for col in range(5):
                        item.setBackground(col, QBrush(QColor(entry['context_color'])))
                        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update list: {str(e)}")
        
    def update_views(self):
        """Update both calendar and list views."""
        self.update_calendar_view()
        self.update_list_view()
        
    def load_variables(self):
        """Load variables from database."""
        try:
            variables = self.db.get_variables()
            self.variable_combo.clear()
            self.variable_combo.addItem("Select Variable")
            for var in variables:
                self.variable_combo.addItem(var['name'])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load variables: {str(e)}")

    def show_db_config(self):
        """Show database configuration dialog."""
        dialog = DatabaseConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reconnect to database with new settings
            try:
                if hasattr(self, 'db'):
                    self.db.disconnect()
                
                db_config = self.config.get_database_config()
                self.db = PostgresDatabase(
                    dbname=db_config['dbname'],
                    user=db_config['user'],
                    password=db_config['password'],
                    host=db_config['host'],
                    port=db_config['port']
                )
                self.db.connect()
                
                # Reload data
                self.load_variables()
                self.update_views()
                
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(e)}")

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        if hasattr(self, 'db'):
            self.db.disconnect() 