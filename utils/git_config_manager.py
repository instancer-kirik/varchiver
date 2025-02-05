import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QMessageBox
from PyQt5.QtGui import QFont
import subprocess

class GitConfigManager:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def show_git_status(self):
        """Show detailed git status"""
        try:
            if not self.repo_path or not os.path.exists(self.repo_path / '.git'):
                QMessageBox.warning(self, "Error", "Not a Git repository")
                return
                
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Git Status")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout()
            dialog.setLayout(layout)
            
            # Add status text
            status_text = QTextEdit()
            status_text.setReadOnly(True)
            status_text.setFont(QFont("Monospace"))
            layout.addWidget(status_text)
            
            # Add refresh button and status
            button_layout = QHBoxLayout()
            
            refresh_btn = QPushButton("Refresh")
            refresh_btn.clicked.connect(lambda: self._refresh_status_dialog(status_text, status_label))
            button_layout.addWidget(refresh_btn)
            
            # Add status label
            status_label = QLabel()
            status_label.setFont(QFont("", weight=QFont.Weight.Bold))
            button_layout.addWidget(status_label)
            
            button_layout.addStretch()
            
            # Add close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            # Initial status update
            self._refresh_status_dialog(status_text, status_label)
            
            dialog.exec()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get status: {str(e)}")

    def _refresh_status_dialog(self, status_text: QTextEdit, status_label: QLabel):
        """Refresh the status text in the dialog"""
        try:
            # Get detailed status
            status_result = subprocess.run(
                ["git", "status"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            # Get porcelain status for precise state detection
            porcelain_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if status_result.returncode == 0:
                # Update status text
                status_text.setText(status_result.stdout)
                
                # Update status label based on porcelain output
                if porcelain_result.returncode == 0:
                    if not porcelain_result.stdout.strip():
                        status_label.setText("✓ Repository is clean")
                        status_label.setStyleSheet("color: #00aa00;")  # Green
                    else:
                        changes = porcelain_result.stdout.strip().split('\n')
                        status_label.setText(f"⚠ Repository has {len(changes)} change(s)")
                        status_label.setStyleSheet("color: #ffa500;")  # Orange
                else:
                    status_label.setText("⚠ Unable to determine detailed status")
                    status_label.setStyleSheet("color: #ffa500;")  # Orange
            else:
                status_text.setText(f"Error getting status:\n{status_result.stderr}")
                status_label.setText("✗ Error checking status")
                status_label.setStyleSheet("color: #ff0000;")  # Red
                
        except Exception as e:
            status_text.setText(f"Error: {str(e)}")
            status_label.setText("✗ Error checking status")
            status_label.setStyleSheet("color: #ff0000;")  # Red