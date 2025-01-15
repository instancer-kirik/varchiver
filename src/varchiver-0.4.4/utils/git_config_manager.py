"""Git configuration management utilities with user-friendly interface."""

from pathlib import Path
import subprocess
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QGroupBox, QCheckBox, QMessageBox,
                            QComboBox, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal

class GitConfigManager(QWidget):
    """User-friendly interface for managing Git configurations."""
    
    config_changed = pyqtSignal()  # Signal emitted when configuration changes

    # Common patterns for .gitattributes
    COMMON_PATTERNS = {
        'archives': {
            'description': 'Archive files (exclude from releases)',
            'patterns': ['*.tar.gz', '*.zip', '*.rar', '*.7z', '*.pkg.tar.zst']
        },
        'build_artifacts': {
            'description': 'Build artifacts and temporary files',
            'patterns': ['build/', 'dist/', '*.pyc', '__pycache__/', '.venv/', 'node_modules/']
        },
        'ide_files': {
            'description': 'IDE and editor files',
            'patterns': ['.vscode/', '.idea/', '*.swp', '*.swo', '*~']
        },
        'test_files': {
            'description': 'Test files and directories',
            'patterns': ['tests/', 'test/', '*.test.*', '*.spec.*']
        }
    }

    # Git tips for better repository management
    GIT_TIPS = """
# Git Best Practices and Tips

## .gitattributes Tips
- Use `export-ignore` to exclude files from archives/releases
- Use `text=auto` for automatic line ending conversion
- Use `binary` for binary files to prevent line ending conversion
- Use `diff=python` for better Python diffs

## General Git Tips
- Keep releases clean by excluding build artifacts
- Use meaningful commit messages
- Tag releases with version numbers
- Use branches for features and fixes
- Keep sensitive data out of the repository

## Common Patterns
- `*.tar.gz export-ignore` - Exclude archives from releases
- `*.pyc export-ignore` - Exclude Python bytecode
- `tests/ export-ignore` - Exclude test directories
- `docs/ export-ignore` - Exclude documentation (if not needed in releases)
"""

    def __init__(self, repo_path: Path):
        super().__init__()
        self.repo_path = repo_path
        self.gitattributes_path = repo_path / '.gitattributes'
        self.setup_ui()
        self.load_current_config()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Pattern selection section
        patterns_group = QGroupBox("Common Patterns")
        patterns_layout = QVBoxLayout()
        patterns_group.setLayout(patterns_layout)

        self.pattern_checkboxes = {}
        for key, info in self.COMMON_PATTERNS.items():
            checkbox = QCheckBox(info['description'])
            checkbox.stateChanged.connect(self.on_pattern_changed)
            self.pattern_checkboxes[key] = checkbox
            patterns_layout.addWidget(checkbox)

        layout.addWidget(patterns_group)

        # Custom patterns section
        custom_group = QGroupBox("Custom Patterns")
        custom_layout = QVBoxLayout()
        custom_group.setLayout(custom_layout)

        self.custom_patterns = QTextEdit()
        self.custom_patterns.setPlaceholderText("Enter custom patterns (one per line)\nExample: *.log export-ignore")
        custom_layout.addWidget(self.custom_patterns)

        layout.addWidget(custom_group)

        # Tips section
        tips_group = QGroupBox("Git Tips")
        tips_layout = QVBoxLayout()
        tips_group.setLayout(tips_layout)

        tips_text = QTextEdit()
        tips_text.setMarkdown(self.GIT_TIPS)
        tips_text.setReadOnly(True)
        tips_layout.addWidget(tips_text)

        layout.addWidget(tips_group)

        # Action buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Configuration")
        save_button.clicked.connect(self.save_configuration)
        button_layout.addWidget(save_button)
        
        preview_button = QPushButton("Preview Changes")
        preview_button.clicked.connect(self.preview_changes)
        button_layout.addWidget(preview_button)

        layout.addLayout(button_layout)

    def load_current_config(self):
        """Load current .gitattributes configuration."""
        try:
            if self.gitattributes_path.exists():
                content = self.gitattributes_path.read_text()
                
                # Check common patterns
                for key, info in self.COMMON_PATTERNS.items():
                    patterns_found = all(
                        any(line.strip().startswith(pattern) for line in content.splitlines())
                        for pattern in info['patterns']
                    )
                    self.pattern_checkboxes[key].setChecked(patterns_found)
                
                # Load custom patterns
                custom_patterns = []
                for line in content.splitlines():
                    if not any(
                        pattern in line 
                        for patterns in self.COMMON_PATTERNS.values() 
                        for pattern in patterns['patterns']
                    ):
                        custom_patterns.append(line)
                
                self.custom_patterns.setPlainText('\n'.join(custom_patterns))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load configuration: {e}")

    def generate_config_content(self) -> str:
        """Generate .gitattributes content based on current settings."""
        lines = ["# Generated by Varchiver Git Config Manager"]
        
        # Add selected common patterns
        for key, checkbox in self.pattern_checkboxes.items():
            if checkbox.isChecked():
                lines.append(f"\n# {self.COMMON_PATTERNS[key]['description']}")
                for pattern in self.COMMON_PATTERNS[key]['patterns']:
                    lines.append(f"{pattern} export-ignore")
        
        # Add custom patterns
        custom = self.custom_patterns.toPlainText().strip()
        if custom:
            lines.append("\n# Custom patterns")
            lines.extend(custom.splitlines())
        
        return '\n'.join(lines)

    def preview_changes(self):
        """Show a preview of the changes to be made."""
        preview = QMessageBox(self)
        preview.setWindowTitle("Configuration Preview")
        preview.setText("New .gitattributes configuration:")
        preview.setDetailedText(self.generate_config_content())
        preview.exec()

    def save_configuration(self):
        """Save the configuration to .gitattributes."""
        try:
            content = self.generate_config_content()
            self.gitattributes_path.write_text(content)
            self.config_changed.emit()
            QMessageBox.information(self, "Success", "Git configuration saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

    def on_pattern_changed(self):
        """Handle pattern checkbox state changes."""
        # This method can be extended to provide real-time feedback or validation
        pass

def setup_git_config(repo_path: Path) -> None:
    """Helper function to set up initial Git configuration."""
    if not (repo_path / '.git').exists():
        raise ValueError(f"Not a Git repository: {repo_path}")
    
    # Ensure .gitattributes exists
    gitattributes_path = repo_path / '.gitattributes'
    if not gitattributes_path.exists():
        gitattributes_path.write_text("# Generated by Varchiver Git Config Manager\n") 