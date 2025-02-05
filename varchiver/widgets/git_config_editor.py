"""Git config file management tool."""

from pathlib import Path
import os
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QMessageBox, QComboBox, QLineEdit,
                            QTreeWidget, QTreeWidgetItem, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat

class GitConfigHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Git config files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Comment format (gray)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(Qt.GlobalColor.gray)
        
        # Section format (blue)
        self.section_format = QTextCharFormat()
        self.section_format.setForeground(Qt.GlobalColor.blue)
        self.section_format.setFontWeight(700)  # Bold
        
        # Key format (dark cyan)
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(Qt.GlobalColor.darkCyan)
        
        # Value format (dark green)
        self.value_format = QTextCharFormat()
        self.value_format.setForeground(Qt.GlobalColor.darkGreen)
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        # Handle comments
        if text.lstrip().startswith('#') or text.lstrip().startswith(';'):
            self.setFormat(0, len(text), self.comment_format)
            return
            
        # Handle sections
        if text.lstrip().startswith('['):
            end = text.find(']')
            if end != -1:
                self.setFormat(text.find('['), end + 1, self.section_format)
            return
            
        # Handle key-value pairs
        if '=' in text:
            key, value = text.split('=', 1)
            self.setFormat(0, len(key), self.key_format)
            self.setFormat(len(key) + 1, len(value), self.value_format)

class GitConfigEditor(QWidget):
    """Widget for managing Git config files."""
    
    COMMON_SECTIONS = [
        'core', 'user', 'remote "origin"', 'branch', 'color',
        'diff', 'merge', 'pull', 'push', 'fetch', 'gui'
    ]
    
    COMMON_KEYS = {
        'core': ['autocrlf', 'filemode', 'bare', 'logallrefupdates', 'ignorecase'],
        'user': ['name', 'email', 'signingkey'],
        'remote "origin"': ['url', 'fetch', 'pushurl', 'proxy'],
        'branch': ['remote', 'merge'],
        'color': ['ui', 'branch', 'diff', 'status'],
        'diff': ['tool', 'algorithm', 'colorMoved'],
        'merge': ['tool', 'conflictstyle', 'ff'],
        'pull': ['rebase', 'ff'],
        'push': ['default', 'followTags', 'autoSetupRemote'],
        'fetch': ['prune', 'pruneTags'],
        'gui': ['encoding', 'fontui', 'fontdiff']
    }
    
    def __init__(self, repo_path: str, parent=None):
        super().__init__(parent)
        self.repo_path = Path(repo_path)
        self.config_path = self.repo_path / '.git' / 'config'
        self.init_ui()
        self.load_content()
        
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description
        desc = QLabel(
            "Manage Git configuration. Edit settings in the repository's .git/config file."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Quick add section
        quick_add_layout = QHBoxLayout()
        
        # Section selector
        self.section_combo = QComboBox()
        self.section_combo.setEditable(True)
        self.section_combo.addItems(self.COMMON_SECTIONS)
        self.section_combo.setCurrentText("")
        self.section_combo.setPlaceholderText("Select or enter section")
        self.section_combo.currentTextChanged.connect(self.update_key_combo)
        quick_add_layout.addWidget(self.section_combo)
        
        # Key selector
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.setPlaceholderText("Select or enter key")
        quick_add_layout.addWidget(self.key_combo)
        
        # Value input
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter value")
        quick_add_layout.addWidget(self.value_input)
        
        # Add button
        add_btn = QPushButton("Add Setting")
        add_btn.clicked.connect(self.add_setting)
        quick_add_layout.addWidget(add_btn)
        
        layout.addLayout(quick_add_layout)
        
        # Editor
        self.editor = QTextEdit()
        self.highlighter = GitConfigHighlighter(self.editor.document())
        layout.addWidget(self.editor)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_content)
        button_layout.addWidget(save_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_content)
        button_layout.addWidget(refresh_btn)
        
        layout.addLayout(button_layout)
        
    def update_key_combo(self, section):
        """Update key combo box based on selected section."""
        self.key_combo.clear()
        if section in self.COMMON_KEYS:
            self.key_combo.addItems(self.COMMON_KEYS[section])
        
    def load_content(self):
        """Load Git config content into editor."""
        try:
            if self.config_path.exists():
                content = self.config_path.read_text()
            else:
                content = self.get_default_content()
            self.editor.setText(content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Git config: {str(e)}")
            
    def save_content(self):
        """Save changes to Git config file."""
        try:
            content = self.editor.toPlainText()
            if content.strip():  # Only save if there's actual content
                self.config_path.write_text(content)
                QMessageBox.information(self, "Success", "Changes saved to Git config")
            else:
                QMessageBox.warning(self, "Warning", "Cannot save empty Git config")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Git config: {str(e)}")
            
    def add_setting(self):
        """Add a new setting to Git config."""
        section = self.section_combo.currentText().strip()
        key = self.key_combo.currentText().strip()
        value = self.value_input.text().strip()
        
        if not section or not key or not value:
            return
            
        # Add setting to editor
        content = self.editor.toPlainText()
        lines = content.split('\n')
        
        # Find or create section
        section_start = -1
        section_end = -1
        section_text = f"[{section}]"
        
        for i, line in enumerate(lines):
            if line.strip() == section_text:
                section_start = i
                # Find section end
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith('['):
                        section_end = j
                        break
                if section_end == -1:
                    section_end = len(lines)
                break
                
        if section_start == -1:
            # Add new section at end
            if content and not content.endswith('\n'):
                content += '\n'
            content += f"\n{section_text}\n"
            content += f"\t{key} = {value}\n"
        else:
            # Add to existing section
            lines.insert(section_end, f"\t{key} = {value}")
            content = '\n'.join(lines)
            
        self.editor.setText(content)
        
        # Clear inputs
        self.section_combo.setCurrentText("")
        self.key_combo.setCurrentText("")
        self.value_input.clear()
        
    def get_default_content(self):
        """Get default content for new Git config file."""
        return """[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = true
\tignorecase = true

[user]
\tname = 
\temail = 

[remote "origin"]
\turl = 
\tfetch = +refs/heads/*:refs/remotes/origin/*

[branch "master"]
\tremote = origin
\tmerge = refs/heads/master
""" 