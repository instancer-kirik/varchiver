"""Git configuration management functionality."""

from pathlib import Path
import os
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QMessageBox,
    QTabWidget, QHBoxLayout, QCheckBox, QGroupBox, QComboBox,
    QLabel, QGridLayout, QDialog, QDialogButtonBox, QMenu
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QAction

class GitConfigHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Git config files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Formatting for different elements
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#2E86C1"))  # Blue
        
        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("#27AE60"))  # Green
        
        self.section_format = QTextCharFormat()
        self.section_format.setForeground(QColor("#8E44AD"))  # Purple
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#95A5A6"))  # Gray
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        # Highlight comments
        if text.lstrip().startswith('#'):
            self.setFormat(0, len(text), self.comment_format)
            return
            
        # Highlight sections [section]
        if text.startswith('[') and ']' in text:
            end = text.index(']') + 1
            self.setFormat(0, end, self.section_format)
            return
            
        # Highlight key=value pairs
        if '=' in text:
            key, value = text.split('=', 1)
            self.setFormat(0, len(key), self.key_format)
            self.setFormat(len(key) + 1, len(value), self.value_format)

class GitAttributesHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for .gitattributes files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Formatting for different elements
        self.pattern_format = QTextCharFormat()
        self.pattern_format.setForeground(QColor("#2E86C1"))  # Blue
        
        self.attribute_format = QTextCharFormat()
        self.attribute_format.setForeground(QColor("#27AE60"))  # Green
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#95A5A6"))  # Gray
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        # Highlight comments
        if text.lstrip().startswith('#'):
            self.setFormat(0, len(text), self.comment_format)
            return
            
        # Highlight pattern and attributes
        parts = text.split(None, 1)
        if len(parts) > 0:
            # Pattern
            self.setFormat(0, len(parts[0]), self.pattern_format)
            if len(parts) > 1:
                # Attributes
                self.setFormat(len(parts[0]) + 1, len(parts[1]), self.attribute_format)

class GitIgnoreHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for .gitignore files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Formatting for different elements
        self.pattern_format = QTextCharFormat()
        self.pattern_format.setForeground(QColor("#2E86C1"))  # Blue
        
        self.negation_format = QTextCharFormat()
        self.negation_format.setForeground(QColor("#E74C3C"))  # Red
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#95A5A6"))  # Gray
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        # Highlight comments
        if text.lstrip().startswith('#'):
            self.setFormat(0, len(text), self.comment_format)
            return
            
        # Highlight negation patterns
        if text.startswith('!'):
            self.setFormat(0, len(text), self.negation_format)
        else:
            self.setFormat(0, len(text), self.pattern_format)

class TemplateDialog(QDialog):
    """Dialog for selecting and customizing templates."""
    
    GITIGNORE_TEMPLATES = {
        "Python": [
            "*.py[cod]",
            "__pycache__/",
            "*.so",
            "build/",
            "dist/",
            "*.egg-info/",
            ".env/",
            ".venv/",
            "venv/",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/"
        ],
        "Node.js": [
            "node_modules/",
            "npm-debug.log",
            "yarn-debug.log",
            "yarn-error.log",
            ".env",
            ".env.local",
            "dist/",
            "build/",
            "coverage/"
        ],
        "C++": [
            "*.o",
            "*.obj",
            "*.exe",
            "*.out",
            "*.app",
            "*.dll",
            "*.so",
            "*.dylib",
            "build/",
            "CMakeFiles/",
            "CMakeCache.txt"
        ]
    }
    
    GITATTRIBUTES_TEMPLATES = {
        "Basic": [
            "* text=auto",
            "*.txt text",
            "*.md text",
            "*.png binary",
            "*.jpg binary",
            "*.gif binary"
        ],
        "Python": [
            "* text=auto",
            "*.py text diff=python",
            "*.pyw text diff=python",
            "*.ipynb text",
            "*.pyd binary",
            "*.pyo binary",
            "*.pyc binary"
        ],
        "Web": [
            "* text=auto",
            "*.html text diff=html",
            "*.css text diff=css",
            "*.js text",
            "*.json text",
            "*.png binary",
            "*.jpg binary",
            "*.gif binary",
            "*.woff binary",
            "*.woff2 binary"
        ]
    }
    
    def __init__(self, template_type: str, parent=None):
        super().__init__(parent)
        self.template_type = template_type
        self.selected_template = []
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle(f"Select {self.template_type} Template")
        layout = QVBoxLayout(self)
        
        # Template selection
        templates = self.GITIGNORE_TEMPLATES if self.template_type == "gitignore" else self.GITATTRIBUTES_TEMPLATES
        
        template_group = QGroupBox("Available Templates")
        template_layout = QVBoxLayout()
        
        self.template_combo = QComboBox()
        self.template_combo.addItems(templates.keys())
        self.template_combo.currentTextChanged.connect(self.preview_template)
        template_layout.addWidget(self.template_combo)
        
        # Preview area
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        template_layout.addWidget(self.preview)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Show initial preview
        self.preview_template(self.template_combo.currentText())
        
    def preview_template(self, template_name: str):
        """Preview the selected template."""
        templates = self.GITIGNORE_TEMPLATES if self.template_type == "gitignore" else self.GITATTRIBUTES_TEMPLATES
        content = templates.get(template_name, [])
        self.preview.setPlainText('\n'.join(content))
        self.selected_template = content
        
    @classmethod
    def get_template(cls, template_type: str, parent=None) -> list[str]:
        """Show dialog and return selected template."""
        dialog = cls(template_type, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_template
        return []

class GitConfigManager(QWidget):
    """Widget for managing Git configuration."""
    
    # Common ignore pattern groups
    IGNORE_PATTERNS = {
        "build": [
            "build/",
            "dist/",
            "*.o",
            "*.pyc",
            "__pycache__/",
            "*.so",
            "*.dylib",
            "*.dll",
            "*.exe",
            "*.out",
            "*.app"
        ],
        "ide": [
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            ".project",
            ".classpath",
            ".settings/",
            "*.sublime-workspace",
            "*.sublime-project",
            ".vs/",
            "*.user",
            "*.suo"
        ],
        "env": [
            ".env",
            ".env.local",
            ".env.*",
            "*.env",
            ".venv/",
            "venv/",
            "ENV/",
            "env.bak/",
            "venv.bak/"
        ],
        "logs": [
            "*.log",
            "logs/",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            "pip-log.txt",
            "pip-delete-this-directory.txt"
        ]
    }
    
    # Common attribute patterns
    ATTRIBUTE_PATTERNS = {
        "text_auto": [
            "* text=auto",
            "*.txt text",
            "*.md text",
            "*.rst text"
        ],
        "eol_lf": [
            "* text eol=lf",
            "*.sh text eol=lf",
            "*.py text eol=lf",
            "*.pl text eol=lf",
            "*.rb text eol=lf"
        ],
        "eol_crlf": [
            "* text eol=crlf",
            "*.bat text eol=crlf",
            "*.cmd text eol=crlf",
            "*.ps1 text eol=crlf"
        ],
        "binary": [
            "*.png binary",
            "*.jpg binary",
            "*.gif binary",
            "*.ico binary",
            "*.zip binary",
            "*.pdf binary",
            "*.woff binary",
            "*.woff2 binary"
        ]
    }
    
    def __init__(self, repo_path: Path, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        self.settings = QSettings("Varchiver", "GitManager")
        self._is_loading = False  # Flag to prevent save during loading
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Git Config tab
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        # Common settings toggles
        settings_group = QGroupBox("Common Settings")
        settings_layout = QGridLayout()
        
        # Auto CRLF with tri-state
        self.auto_crlf = QCheckBox("Auto CRLF")
        self.auto_crlf.setTristate(True)
        self.auto_crlf.stateChanged.connect(lambda state: self.toggle_setting(
            "core.autocrlf",
            "true" if state == Qt.CheckState.Checked else
            "input" if state == Qt.CheckState.PartiallyChecked else
            "false"
        ))
        settings_layout.addWidget(self.auto_crlf, 0, 0)
        
        # Safe CRLF with tri-state
        self.safe_crlf = QCheckBox("Safe CRLF")
        self.safe_crlf.setTristate(True)
        self.safe_crlf.stateChanged.connect(lambda state: self.toggle_setting(
            "core.safecrlf",
            "true" if state == Qt.CheckState.Checked else
            "warn" if state == Qt.CheckState.PartiallyChecked else
            "false"
        ))
        settings_layout.addWidget(self.safe_crlf, 0, 1)
        
        # File mode
        self.filemode = QCheckBox("File Mode")
        self.filemode.stateChanged.connect(lambda state: self.toggle_setting(
            "core.filemode", "true" if state == Qt.CheckState.Checked else "false"
        ))
        settings_layout.addWidget(self.filemode, 1, 0)
        
        # Ignore case
        self.ignorecase = QCheckBox("Ignore Case")
        self.ignorecase.stateChanged.connect(lambda state: self.toggle_setting(
            "core.ignorecase", "true" if state == Qt.CheckState.Checked else "false"
        ))
        settings_layout.addWidget(self.ignorecase, 1, 1)
        
        settings_group.setLayout(settings_layout)
        config_layout.addWidget(settings_group)
        
        # Advanced config editor
        self.config_editor = QTextEdit()
        self.config_editor.setPlaceholderText("Git configuration will appear here...")
        self.config_highlighter = GitConfigHighlighter(self.config_editor.document())
        config_layout.addWidget(self.config_editor)
        
        config_buttons = QHBoxLayout()
        refresh_config_btn = QPushButton("Refresh Config")
        refresh_config_btn.clicked.connect(self.load_config)
        config_buttons.addWidget(refresh_config_btn)
        
        save_config_btn = QPushButton("Save Config")
        save_config_btn.clicked.connect(self.save_config)
        config_buttons.addWidget(save_config_btn)
        
        config_layout.addLayout(config_buttons)
        self.tab_widget.addTab(config_tab, "Git Config")
        
        # Git Attributes tab
        attributes_tab = QWidget()
        attributes_layout = QVBoxLayout(attributes_tab)
        
        # Common attributes toggles
        attr_group = QGroupBox("Common Attributes")
        attr_layout = QGridLayout()
        
        # Text handling group
        text_group = QGroupBox("Text Handling")
        text_layout = QVBoxLayout()
        
        self.text_auto = QCheckBox("text=auto (All Files)")
        self.text_auto.stateChanged.connect(lambda state: self.toggle_attribute_group(
            "text_auto" if state == Qt.CheckState.Checked else None
        ))
        text_layout.addWidget(self.text_auto)
        
        # EOL handling group
        eol_group = QGroupBox("EOL Handling")
        eol_layout = QVBoxLayout()
        
        self.eol_lf = QCheckBox("LF (Unix)")
        self.eol_lf.stateChanged.connect(lambda state: self.toggle_attribute_group(
            "eol_lf" if state == Qt.CheckState.Checked else None
        ))
        eol_layout.addWidget(self.eol_lf)
        
        self.eol_crlf = QCheckBox("CRLF (Windows)")
        self.eol_crlf.stateChanged.connect(lambda state: self.toggle_attribute_group(
            "eol_crlf" if state == Qt.CheckState.Checked else None
        ))
        eol_layout.addWidget(self.eol_crlf)
        
        eol_group.setLayout(eol_layout)
        text_layout.addWidget(eol_group)
        
        text_group.setLayout(text_layout)
        attr_layout.addWidget(text_group, 0, 0)
        
        # Binary files group
        binary_group = QGroupBox("Binary Files")
        binary_layout = QVBoxLayout()
        
        self.binary_files = QCheckBox("Common Binary Files")
        self.binary_files.stateChanged.connect(lambda state: self.toggle_attribute_group(
            "binary" if state == Qt.CheckState.Checked else None
        ))
        binary_layout.addWidget(self.binary_files)
        
        binary_group.setLayout(binary_layout)
        attr_layout.addWidget(binary_group, 0, 1)
        
        attr_group.setLayout(attr_layout)
        attributes_layout.addWidget(attr_group)
        
        self.attributes_editor = QTextEdit()
        self.attributes_editor.setPlaceholderText("Git attributes will appear here...")
        self.attributes_highlighter = GitAttributesHighlighter(self.attributes_editor.document())
        attributes_layout.addWidget(self.attributes_editor)
        
        attributes_buttons = QHBoxLayout()
        refresh_attr_btn = QPushButton("Refresh Attributes")
        refresh_attr_btn.clicked.connect(self.load_attributes)
        attributes_buttons.addWidget(refresh_attr_btn)
        
        save_attr_btn = QPushButton("Save Attributes")
        save_attr_btn.clicked.connect(self.save_attributes)
        attributes_buttons.addWidget(save_attr_btn)
        
        template_attr_btn = QPushButton("Load Template...")
        template_attr_btn.clicked.connect(lambda: self.load_template("gitattributes"))
        attributes_buttons.addWidget(template_attr_btn)
        
        attributes_layout.addLayout(attributes_buttons)
        self.tab_widget.addTab(attributes_tab, "Git Attributes")
        
        # Git Ignore tab
        ignore_tab = QWidget()
        ignore_layout = QVBoxLayout(ignore_tab)
        
        # Common patterns
        ignore_group = QGroupBox("Common Patterns")
        ignore_layout_grid = QGridLayout()
        
        # Build artifacts with nested options
        build_group = QGroupBox("Build")
        build_layout = QVBoxLayout()
        
        self.ignore_build = QCheckBox("Build Artifacts")
        self.ignore_build.stateChanged.connect(lambda state: self.toggle_ignore_group(
            "build" if state == Qt.CheckState.Checked else None
        ))
        build_layout.addWidget(self.ignore_build)
        
        build_group.setLayout(build_layout)
        ignore_layout_grid.addWidget(build_group, 0, 0)
        
        # IDE files with nested options
        ide_group = QGroupBox("IDE")
        ide_layout = QVBoxLayout()
        
        self.ignore_ide = QCheckBox("IDE Files")
        self.ignore_ide.stateChanged.connect(lambda state: self.toggle_ignore_group(
            "ide" if state == Qt.CheckState.Checked else None
        ))
        ide_layout.addWidget(self.ignore_ide)
        
        ide_group.setLayout(ide_layout)
        ignore_layout_grid.addWidget(ide_group, 0, 1)
        
        # Environment files with nested options
        env_group = QGroupBox("Environment")
        env_layout = QVBoxLayout()
        
        self.ignore_env = QCheckBox("Environment Files")
        self.ignore_env.stateChanged.connect(lambda state: self.toggle_ignore_group(
            "env" if state == Qt.CheckState.Checked else None
        ))
        env_layout.addWidget(self.ignore_env)
        
        env_group.setLayout(env_layout)
        ignore_layout_grid.addWidget(env_group, 1, 0)
        
        # Log files with nested options
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout()
        
        self.ignore_logs = QCheckBox("Log Files")
        self.ignore_logs.stateChanged.connect(lambda state: self.toggle_ignore_group(
            "logs" if state == Qt.CheckState.Checked else None
        ))
        log_layout.addWidget(self.ignore_logs)
        
        log_group.setLayout(log_layout)
        ignore_layout_grid.addWidget(log_group, 1, 1)
        
        ignore_group.setLayout(ignore_layout_grid)
        ignore_layout.addWidget(ignore_group)
        
        self.ignore_editor = QTextEdit()
        self.ignore_editor.setPlaceholderText("Git ignore patterns will appear here...")
        self.ignore_highlighter = GitIgnoreHighlighter(self.ignore_editor.document())
        ignore_layout.addWidget(self.ignore_editor)
        
        ignore_buttons = QHBoxLayout()
        refresh_ignore_btn = QPushButton("Refresh Ignore")
        refresh_ignore_btn.clicked.connect(self.load_ignore)
        ignore_buttons.addWidget(refresh_ignore_btn)
        
        save_ignore_btn = QPushButton("Save Ignore")
        save_ignore_btn.clicked.connect(self.save_ignore)
        ignore_buttons.addWidget(save_ignore_btn)
        
        template_ignore_btn = QPushButton("Load Template...")
        template_ignore_btn.clicked.connect(lambda: self.load_template("gitignore"))
        ignore_buttons.addWidget(template_ignore_btn)
        
        ignore_layout.addLayout(ignore_buttons)
        self.tab_widget.addTab(ignore_tab, "Git Ignore")
        
        layout.addWidget(self.tab_widget)
        
        # Load initial content
        self.load_config()
        self.load_attributes()
        self.load_ignore()
        
    def toggle_setting(self, key: str, value: str | None):
        """Toggle a Git config setting."""
        try:
            if value is None:
                # Remove setting
                subprocess.run(
                    ["git", "config", "--local", "--unset", key],
                    cwd=self.repo_path,
                    check=False  # Don't error if key doesn't exist
                )
            else:
                subprocess.run(
                    ["git", "config", "--local", key, value],
                    cwd=self.repo_path,
                    check=True
                )
            self.load_config()  # Refresh to show changes
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Error", f"Failed to set {key}: {e.stderr}")
            
    def toggle_attribute_group(self, group: str | None):
        """Toggle a group of Git attributes."""
        if group is None:
            # Remove all patterns from group
            patterns = self.ATTRIBUTE_PATTERNS.get(group, [])
            current = self.attributes_editor.toPlainText().splitlines()
            current = [line for line in current if not any(
                pattern in line for pattern in patterns
            )]
        else:
            # Add all patterns from group
            patterns = self.ATTRIBUTE_PATTERNS.get(group, [])
            current = self.attributes_editor.toPlainText().splitlines()
            current.extend(patterns)
            
        self.attributes_editor.setPlainText('\n'.join(sorted(set(current))))
        self.save_attributes()
        
    def toggle_ignore_group(self, group: str | None):
        """Toggle a group of Git ignore patterns."""
        if self._is_loading:
            return
            
        if group is None:
            # Remove all patterns from group
            patterns = self.IGNORE_PATTERNS.get(group, [])
            current = set(self.ignore_editor.toPlainText().splitlines())
            current.difference_update(patterns)
        else:
            # Add all patterns from group
            patterns = self.IGNORE_PATTERNS.get(group, [])
            current = set(self.ignore_editor.toPlainText().splitlines())
            current.update(patterns)
            
        self.ignore_editor.setPlainText('\n'.join(sorted(current)))
        
        # Only save if not loading and content has changed
        if not self._is_loading:
            self.save_ignore(show_message=False)  # Don't show message for toggle updates
            
    def load_template(self, template_type: str):
        """Load a template for gitignore or gitattributes."""
        template = TemplateDialog.get_template(template_type, self)
        if template:
            if template_type == "gitignore":
                current = self.ignore_editor.toPlainText().splitlines()
                self.ignore_editor.setPlainText('\n'.join(current + template))
                self.save_ignore()
            else:
                current = self.attributes_editor.toPlainText().splitlines()
                self.attributes_editor.setPlainText('\n'.join(current + template))
                self.save_attributes()

    def load_config(self):
        """Load Git configuration and update UI state."""
        try:
            # Load config content
            result = subprocess.run(
                ["git", "config", "--list", "--local"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            self.config_editor.setPlainText(result.stdout)
            
            # Update toggle states
            config = dict(
                line.split('=', 1)
                for line in result.stdout.splitlines()
                if '=' in line
            )
            
            # Auto CRLF state
            if 'core.autocrlf' in config:
                value = config['core.autocrlf'].lower()
                self.auto_crlf.setCheckState(
                    Qt.CheckState.Checked if value == 'true' else
                    Qt.CheckState.PartiallyChecked if value == 'input' else
                    Qt.CheckState.Unchecked
                )
            
            # Safe CRLF state
            if 'core.safecrlf' in config:
                value = config['core.safecrlf'].lower()
                self.safe_crlf.setCheckState(
                    Qt.CheckState.Checked if value == 'true' else
                    Qt.CheckState.PartiallyChecked if value == 'warn' else
                    Qt.CheckState.Unchecked
                )
            
            # ... update other toggle states ...
            
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Error", f"Failed to load Git config: {e.stderr}")
            
    def save_config(self):
        """Save Git configuration to repository."""
        try:
            # First clear existing config
            subprocess.run(
                ["git", "config", "--local", "--remove-section", "."],
                cwd=self.repo_path,
                capture_output=True,
                check=False  # Ignore errors if no config exists
            )
            
            # Parse and set new config
            config_text = self.config_editor.toPlainText()
            for line in config_text.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    subprocess.run(
                        ["git", "config", "--local", key, value],
                        cwd=self.repo_path,
                        check=True
                    )
                    
            QMessageBox.information(self, "Success", "Git configuration saved")
            
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to save Git config: {e.stderr}")
            
    def load_attributes(self):
        """Load Git attributes and update UI state."""
        attributes_path = self.repo_path / '.gitattributes'
        try:
            if attributes_path.exists():
                content = attributes_path.read_text()
                self.attributes_editor.setPlainText(content)
                
                # Update toggle states
                lines = content.splitlines()
                
                # Text auto state
                text_auto_patterns = set(self.ATTRIBUTE_PATTERNS['text_auto'])
                self.text_auto.setChecked(
                    any(pattern in lines for pattern in text_auto_patterns)
                )
                
                # EOL states
                eol_lf_patterns = set(self.ATTRIBUTE_PATTERNS['eol_lf'])
                self.eol_lf.setChecked(
                    any(pattern in lines for pattern in eol_lf_patterns)
                )
                
                eol_crlf_patterns = set(self.ATTRIBUTE_PATTERNS['eol_crlf'])
                self.eol_crlf.setChecked(
                    any(pattern in lines for pattern in eol_crlf_patterns)
                )
                
                # Binary files state
                binary_patterns = set(self.ATTRIBUTE_PATTERNS['binary'])
                self.binary_files.setChecked(
                    any(pattern in lines for pattern in binary_patterns)
                )
                
            else:
                self.attributes_editor.clear()
                # Reset toggle states
                self.text_auto.setChecked(False)
                self.eol_lf.setChecked(False)
                self.eol_crlf.setChecked(False)
                self.binary_files.setChecked(False)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load .gitattributes: {str(e)}")
            
    def save_attributes(self):
        """Save Git attributes to repository."""
        attributes_path = self.repo_path / '.gitattributes'
        try:
            content = self.attributes_editor.toPlainText()
            if content.strip():
                attributes_path.write_text(content)
                QMessageBox.information(self, "Success", "Git attributes saved")
            elif attributes_path.exists():
                if QMessageBox.question(
                    self,
                    "Delete File?",
                    "The .gitattributes file is empty. Would you like to delete it?"
                ) == QMessageBox.StandardButton.Yes:
                    attributes_path.unlink()
                    QMessageBox.information(self, "Success", ".gitattributes has been deleted")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save .gitattributes: {str(e)}")
            
    def load_ignore(self):
        """Load Git ignore patterns and update UI state."""
        self._is_loading = True
        try:
            ignore_path = self.repo_path / '.gitignore'
            try:
                if ignore_path.exists():
                    content = ignore_path.read_text()
                    self.ignore_editor.setPlainText(content)
                    
                    # Update toggle states
                    lines = content.splitlines()
                    
                    # Build artifacts state
                    build_patterns = set(self.IGNORE_PATTERNS['build'])
                    self.ignore_build.setChecked(
                        any(pattern in lines for pattern in build_patterns)
                    )
                    
                    # IDE files state
                    ide_patterns = set(self.IGNORE_PATTERNS['ide'])
                    self.ignore_ide.setChecked(
                        any(pattern in lines for pattern in ide_patterns)
                    )
                    
                    # Environment files state
                    env_patterns = set(self.IGNORE_PATTERNS['env'])
                    self.ignore_env.setChecked(
                        any(pattern in lines for pattern in env_patterns)
                    )
                    
                    # Log files state
                    log_patterns = set(self.IGNORE_PATTERNS['logs'])
                    self.ignore_logs.setChecked(
                        any(pattern in lines for pattern in log_patterns)
                    )
                    
                else:
                    self.ignore_editor.clear()
                    # Reset toggle states
                    self.ignore_build.setChecked(False)
                    self.ignore_ide.setChecked(False)
                    self.ignore_env.setChecked(False)
                    self.ignore_logs.setChecked(False)
                    
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load .gitignore: {str(e)}")
        finally:
            self._is_loading = False
            
    def save_ignore(self, show_message: bool = True):
        """Save Git ignore patterns to repository."""
        ignore_path = self.repo_path / '.gitignore'
        try:
            content = self.ignore_editor.toPlainText()
            if content.strip():
                ignore_path.write_text(content)
                if show_message:
                    QMessageBox.information(self, "Success", "Git ignore patterns saved")
            elif ignore_path.exists():
                if QMessageBox.question(
                    self,
                    "Delete File?",
                    "The .gitignore file is empty. Would you like to delete it?"
                ) == QMessageBox.StandardButton.Yes:
                    ignore_path.unlink()
                    if show_message:
                        QMessageBox.information(self, "Success", ".gitignore has been deleted")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save .gitignore: {str(e)}") 