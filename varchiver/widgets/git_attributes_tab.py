"""Git attributes file management tool."""

from pathlib import Path
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QMessageBox, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat

class GitAttributesHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for .gitattributes files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Comment format (gray)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(Qt.GlobalColor.gray)
        
        # Pattern format (default color but bold)
        self.pattern_format = QTextCharFormat()
        self.pattern_format.setFontWeight(700)  # Bold
        
        # Attribute format (blue)
        self.attribute_format = QTextCharFormat()
        self.attribute_format.setForeground(Qt.GlobalColor.blue)
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        # Handle comments
        if text.lstrip().startswith('#'):
            self.setFormat(0, len(text), self.comment_format)
            return
            
        # Handle pattern and attributes
        parts = text.split()
        if len(parts) > 0:
            # Pattern is the first part
            pattern_end = text.find(parts[0]) + len(parts[0])
            self.setFormat(0, pattern_end, self.pattern_format)
            
            # Attributes are the rest
            for part in parts[1:]:
                start = text.find(part)
                self.setFormat(start, len(part), self.attribute_format)

class GitAttributesTab(QWidget):
    """Widget for managing .gitattributes files."""
    
    COMMON_ATTRIBUTES = [
        'text', 'binary', 'eol=lf', 'eol=crlf', 'diff', 'merge',
        'delta', 'encoding=', 'working-tree-encoding=', 'ident',
        'filter=', 'diff=', 'merge=', 'export-ignore', 'export-subst'
    ]
    
    def __init__(self, repo_path: str, parent=None):
        super().__init__(parent)
        self.repo_path = Path(repo_path)
        self.gitattributes_path = self.repo_path / '.gitattributes'
        self.init_ui()
        self.load_content()
        
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description
        desc = QLabel(
            "Manage .gitattributes patterns. Define attributes for path patterns."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Quick add section
        quick_add_layout = QHBoxLayout()
        
        # Pattern input
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter path pattern (e.g. *.txt)")
        quick_add_layout.addWidget(self.pattern_input)
        
        # Attribute selector
        self.attribute_combo = QComboBox()
        self.attribute_combo.setEditable(True)
        self.attribute_combo.addItems(self.COMMON_ATTRIBUTES)
        self.attribute_combo.setCurrentText("")
        self.attribute_combo.setPlaceholderText("Select or enter attribute")
        quick_add_layout.addWidget(self.attribute_combo)
        
        # Add button
        add_btn = QPushButton("Add Rule")
        add_btn.clicked.connect(self.add_rule)
        quick_add_layout.addWidget(add_btn)
        
        layout.addLayout(quick_add_layout)
        
        # Editor
        self.editor = QTextEdit()
        self.highlighter = GitAttributesHighlighter(self.editor.document())
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
        
    def load_content(self):
        """Load .gitattributes content into editor."""
        try:
            if self.gitattributes_path.exists():
                content = self.gitattributes_path.read_text()
            else:
                content = self.get_default_content()
            self.editor.setText(content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load .gitattributes: {str(e)}")
            
    def save_content(self):
        """Save changes to .gitattributes file."""
        try:
            content = self.editor.toPlainText()
            if content.strip():  # Only save if there's actual content
                self.gitattributes_path.write_text(content)
                QMessageBox.information(self, "Success", "Changes saved to .gitattributes")
            else:
                # If file exists but content is empty, ask if user wants to delete it
                if self.gitattributes_path.exists():
                    reply = QMessageBox.question(
                        self, "Delete File?",
                        "The .gitattributes file is empty. Would you like to delete it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.gitattributes_path.unlink()
                        QMessageBox.information(self, "Success", ".gitattributes has been deleted")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save .gitattributes: {str(e)}")
            
    def add_rule(self):
        """Add a new rule to .gitattributes."""
        pattern = self.pattern_input.text().strip()
        attribute = self.attribute_combo.currentText().strip()
        
        if not pattern or not attribute:
            return
            
        # Add rule to editor
        rule = f"{pattern} {attribute}"
        current_content = self.editor.toPlainText()
        if current_content and not current_content.endswith('\n'):
            current_content += '\n'
        current_content += rule + '\n'
        self.editor.setText(current_content)
        
        # Clear inputs
        self.pattern_input.clear()
        self.attribute_combo.setCurrentText("")
        
    def get_default_content(self):
        """Get default content for new .gitattributes file."""
        return """# Handle line endings automatically for files detected as text
# and leave all files detected as binary untouched.
* text=auto

# Python source files
*.py text diff=python

# Shell scripts should use LF
*.sh text eol=lf

# Windows batch files should use CRLF
*.bat text eol=crlf
*.cmd text eol=crlf

# Binary files
*.png binary
*.jpg binary
*.gif binary
*.ico binary
*.zip binary
*.pdf binary
""" 