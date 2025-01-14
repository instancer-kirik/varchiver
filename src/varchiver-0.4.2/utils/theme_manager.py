from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
import json
import os

class ThemeManager:
    """Manages application theming with light and dark mode support."""
    
    LIGHT_THEME = {
        'window': '#E3E3E3',
        'windowText': '#000000',
        'base': '#F5F5F5',
        'alternateBase': '#E0E0E0',
        'text': '#000000',
        'button': '#E3E3E3',
        'buttonText': '#000000',
        'brightText': '#E3E3E3',
        'highlight': '#FF69AA',  # Hot pink for selection
        'highlightedText': '#F3F3F3',
        'link': '#FF69AA',  # Hot pink for links
        'linkVisited': '#DB7093',  # Pale violet red for visited links
        'border': '#BDBDBD',
        'progressBar': '#FF69AA',  # Hot pink for progress
        'progressBarBackground': '#E0E0E0'
    }
    
    DARK_THEME = {
        'window': '#1E1E1E',
        'windowText': '#E3E3E3',
        'base': '#2D2D2D',
        'alternateBase': '#353535',
        'text': '#E3E3E3',
        'button': '#424242',
        'buttonText': '#E3E3E3',
        'brightText': '#E3E3E3',
        'highlight': '#FF69AA',  # Hot pink for selection
        'highlightedText': '#FFFFFF',
        'link': '#FFB6C1',  # Light pink for links
        'linkVisited': '#DB7093',  # Pale violet red for visited links
        'border': '#424242',
        'progressBar': '#FF69AA',  # Hot pink for progress
        'progressBarBackground': '#424242'
    }
    
    def __init__(self):
        self.config_dir = os.path.expanduser('~/.config/varchiver')
        self.config_file = os.path.join(self.config_dir, 'theme.json')
        self.dark_mode = self._load_theme_preference()
    
    def _load_theme_preference(self) -> bool:
        """Load theme preference from config file."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('dark_mode', False)
        except Exception:
            pass
        return False
    
    def save_theme_preference(self):
        """Save theme preference to config file."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({'dark_mode': self.dark_mode}, f)
        except Exception:
            pass
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.save_theme_preference()
    
    def apply_theme(self):
        """Apply the current theme to the application."""
        app = QApplication.instance()
        if not app:
            return
            
        # Create palette
        palette = QPalette()
        colors = self.DARK_THEME if self.dark_mode else self.LIGHT_THEME
        
        # Set colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors['window']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors['windowText']))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors['base']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors['alternateBase']))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors['text']))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors['button']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors['buttonText']))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors['brightText']))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors['highlight']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors['highlightedText']))
        palette.setColor(QPalette.ColorRole.Link, QColor(colors['link']))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors['linkVisited']))
        
        # Apply palette
        app.setPalette(palette)
        
        # Apply stylesheet
        app.setStyleSheet(self._get_stylesheet())
    
    def _get_stylesheet(self) -> str:
        """Get the stylesheet for the current theme."""
        colors = self.DARK_THEME if self.dark_mode else self.LIGHT_THEME
        pink_color = '#FF69B4'
        
        return f"""
            QWidget {{
                background-color: {colors['window']};
                color: {colors['windowText']};
            }}
            
            QTreeWidget {{
                background-color: {colors['base']};
                alternate-background-color: {colors['alternateBase']};
                border: 1px solid {colors['border']};
            }}
            
            QTreeWidget::item:selected {{
                background-color: {colors['highlight']};
                color: {colors['highlightedText']};
            }}
            
            QPushButton {{
                background-color: {colors['button']};
                color: {colors['buttonText']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 5px 10px;
            }}
            
            QPushButton:hover {{
                background-color: {colors['highlight']};
                color: {colors['highlightedText']};
            }}
            
            QProgressBar {{
                border: 1px solid {colors['border']};
                border-radius: 4px;
                text-align: center;
                background-color: {colors['progressBarBackground']};
            }}
            
            QProgressBar::chunk {{
                background-color: {colors['progressBar']};
            }}
            
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {colors['base']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            
            QCheckBox {{
                spacing: 8px;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {colors['border']};
                border-radius: 3px;
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {pink_color};
                border: 2px solid {pink_color};
                border-radius: 3px;
            }}
            
            QCheckBox::indicator:unchecked {{
                background-color: transparent;
                border: 2px solid #AAAAAA;
                border-radius: 3px;
            }}
            
            QCheckBox::indicator:checked:hover {{
                background-color: #FF83C8;
                border: 2px solid #FF83C8;
            }}
            
            QCheckBox::indicator:unchecked:hover {{
                border: 2px solid {pink_color};
            }}
        """
