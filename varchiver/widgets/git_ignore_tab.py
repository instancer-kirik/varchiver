"""Git ignore file management tool."""

from pathlib import Path
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QMessageBox, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat

class GitIgnoreHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for .gitignore files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Comment format (gray)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(Qt.GlobalColor.gray)
        
        # Pattern format (default color but bold)
        self.pattern_format = QTextCharFormat()
        self.pattern_format.setFontWeight(700)  # Bold
        
        # Negation format (red)
        self.negation_format = QTextCharFormat()
        self.negation_format.setForeground(Qt.GlobalColor.red)
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        # Handle comments
        if text.lstrip().startswith('#'):
            self.setFormat(0, len(text), self.comment_format)
            return
            
        # Handle negation patterns
        if text.lstrip().startswith('!'):
            self.setFormat(text.find('!'), 1, self.negation_format)
            self.setFormat(text.find('!') + 1, len(text) - text.find('!') - 1, self.pattern_format)
            return
            
        # Handle normal patterns
        if text.strip():
            self.setFormat(0, len(text), self.pattern_format)

class GitIgnoreTab(QWidget):
    """Widget for managing .gitignore files."""
    
    def __init__(self, repo_path: str, parent=None):
        super().__init__(parent)
        self.repo_path = Path(repo_path)
        self.gitignore_path = self.repo_path / '.gitignore'
        self.init_ui()
        self.load_content()
        
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description
        desc = QLabel(
            "Manage .gitignore patterns. Add patterns to exclude files from Git tracking."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Quick add pattern
        quick_add_layout = QHBoxLayout()
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter pattern to ignore (e.g. *.log)")
        self.pattern_input.returnPressed.connect(self.add_pattern)
        quick_add_layout.addWidget(self.pattern_input)
        
        add_btn = QPushButton("Add Pattern")
        add_btn.clicked.connect(self.add_pattern)
        quick_add_layout.addWidget(add_btn)
        
        layout.addLayout(quick_add_layout)
        
        # Editor
        self.editor = QTextEdit()
        self.highlighter = GitIgnoreHighlighter(self.editor.document())
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
        """Load .gitignore content into editor."""
        try:
            if self.gitignore_path.exists():
                content = self.gitignore_path.read_text()
            else:
                content = self.get_default_content()
            self.editor.setText(content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load .gitignore: {str(e)}")
            
    def save_content(self):
        """Save changes to .gitignore file."""
        try:
            content = self.editor.toPlainText()
            if content.strip():  # Only save if there's actual content
                self.gitignore_path.write_text(content)
                QMessageBox.information(self, "Success", "Changes saved to .gitignore")
            else:
                # If file exists but content is empty, ask if user wants to delete it
                if self.gitignore_path.exists():
                    reply = QMessageBox.question(
                        self, "Delete File?",
                        "The .gitignore file is empty. Would you like to delete it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.gitignore_path.unlink()
                        QMessageBox.information(self, "Success", ".gitignore has been deleted")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save .gitignore: {str(e)}")
            
    def add_pattern(self):
        """Add a new pattern to .gitignore."""
        pattern = self.pattern_input.text().strip()
        if not pattern:
            return
            
        # Add pattern to editor
        current_content = self.editor.toPlainText()
        if current_content and not current_content.endswith('\n'):
            current_content += '\n'
        current_content += pattern + '\n'
        self.editor.setText(current_content)
        
        # Clear input
        self.pattern_input.clear()
        
    def get_default_content(self):
        """Get default content for new .gitignore file."""
        return """# Ignore files generated by your IDE
.idea/
.vscode/
*.swp
*~

# Ignore Python compiled files
__pycache__/
*.py[cod]
*$py.class
*.so

# Ignore virtual environments
venv/
env/
.env/

# Ignore package build files
dist/
build/
*.egg-info/

# Ignore logs and databases
*.log
*.sqlite3
""" 