"""Database configuration dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QSpinBox, QMessageBox, QLabel,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from ..utils.config import Config
from ..utils.variable_db import PostgresDatabase

class DatabaseConfigDialog(QDialog):
    """Dialog for configuring database connection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Database Configuration")
        layout = QVBoxLayout(self)
        
        # Form layout for inputs
        form = QFormLayout()
        
        # Host input
        self.host_input = QLineEdit()
        form.addRow("Host:", self.host_input)
        
        # Port input
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(5432)
        form.addRow("Port:", self.port_input)
        
        # Database name input
        self.dbname_input = QLineEdit()
        form.addRow("Database:", self.dbname_input)
        
        # Username input
        self.user_input = QLineEdit()
        form.addRow("Username:", self.user_input)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.password_input)
        
        layout.addLayout(form)
        
        # Add test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_config)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Add status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
    def load_config(self):
        """Load current configuration."""
        db_config = self.config.get_database_config()
        self.host_input.setText(db_config['host'])
        self.port_input.setValue(db_config['port'])
        self.dbname_input.setText(db_config['dbname'])
        self.user_input.setText(db_config['user'])
        self.password_input.setText(db_config['password'])
        
    def save_config(self):
        """Save configuration and close dialog."""
        try:
            # Test connection first
            if not self.test_connection(silent=True):
                reply = QMessageBox.question(
                    self,
                    "Connection Failed",
                    "The database connection failed. Do you want to save anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Save configuration
            self.config.set_database_config(
                host=self.host_input.text(),
                port=self.port_input.value(),
                dbname=self.dbname_input.text(),
                user=self.user_input.text(),
                password=self.password_input.text()
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
        
    def test_connection(self, silent=False):
        """Test database connection with current settings."""
        try:
            # Create test connection
            db = PostgresDatabase(
                dbname=self.dbname_input.text(),
                user=self.user_input.text(),
                password=self.password_input.text(),
                host=self.host_input.text(),
                port=self.port_input.value()
            )
            
            # Try to connect
            db.connect()
            db.disconnect()
            
            if not silent:
                self.status_label.setText("Connection successful!")
                self.status_label.setStyleSheet("color: green")
                
            return True
            
        except Exception as e:
            if not silent:
                self.status_label.setText(f"Connection failed: {str(e)}")
                self.status_label.setStyleSheet("color: red")
            return False 