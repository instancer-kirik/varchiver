print("Loading release_manager module")

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLineEdit, QLabel, QComboBox, QProgressBar, QMessageBox, QDialog,
                            QFileDialog, QGroupBox, QFormLayout)
from PyQt6.QtCore import QThread, pyqtSignal, QSettings, pyqtSlot
import subprocess
import os
import re
import json
from pathlib import Path

print("Imports completed in release_manager module")

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Release Manager Configuration")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Project configuration
        project_group = QGroupBox("Project Configuration")
        project_layout = QFormLayout()
        project_group.setLayout(project_layout)
        
        # Project directory
        project_dir_layout = QHBoxLayout()
        self.project_path = QLineEdit()
        self.project_path.setPlaceholderText("Path to project repository")
        browse_project = QPushButton("Browse")
        browse_project.clicked.connect(self.browse_project)
        project_dir_layout.addWidget(self.project_path)
        project_dir_layout.addWidget(browse_project)
        project_layout.addRow("Project Directory:", project_dir_layout)
        
        layout.addWidget(project_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def browse_project(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if path:
            self.project_path.setText(path)

    def load_settings(self):
        settings = QSettings("Varchiver", "ReleaseManager")
        self.project_path.setText(settings.value("project_path", ""))

    def save_and_close(self):
        settings = QSettings("Varchiver", "ReleaseManager")
        settings.setValue("project_path", self.project_path.text())
        self.accept()

class ReleaseManager(QWidget):
    def __init__(self):
        print("Initializing ReleaseManager")  # Debug print
        super().__init__()
        self.settings = QSettings("Varchiver", "ReleaseManager")
        
        # Initialize UI elements
        self.project_dir_label = QLabel()
        self.config_dialog = None
        
        # Set up UI
        self.init_ui()
        
        print("ReleaseManager initialized")  # Debug print

    def show_config(self):
        """Show configuration dialog"""
        print("show_config called")  # Debug print
        if not self.config_dialog:
            print("Creating new config dialog")  # Debug print
            self.config_dialog = ConfigDialog(self)
        result = self.config_dialog.exec()
        print(f"Dialog result: {result}")  # Debug print
        if result == QDialog.DialogCode.Accepted:
            self.update_ui_from_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Project directory display
        self.project_dir_label.setText(self.settings.value("project_path", "Not configured"))
        layout.addWidget(self.project_dir_label)
        
        # Configure button
        config_button = QPushButton("Configure")
        config_button.clicked.connect(self.show_config)
        layout.addWidget(config_button)
        
        self.setLayout(layout)
        self.setWindowTitle("Release Manager")

    def update_ui_from_settings(self):
        """Update UI elements based on current settings"""
        project_path = self.settings.value("project_path", "Not configured")
        self.project_dir_label.setText(project_path) 

    def _build_packages(self):
        self.progress.emit("Building packages...")
        if not self.build_command:
            raise Exception("Build command not configured")
            
        if self.project_type == "Python":
            # For Python projects, use specific build commands
            commands = [
                ["python", "-m", "build", "--wheel", "--sdist"],  # Build distributions
                ["uv", "pip", "install", "-e", "."]  # Install in editable mode
            ]
            for cmd in commands:
                result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Build failed: {result.stderr}")
        else:
            # For other project types, use the configured build command
            cmd_parts = self.build_command.split()
            result = subprocess.run(cmd_parts, cwd=self.project_dir, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Build failed: {result.stderr}") 