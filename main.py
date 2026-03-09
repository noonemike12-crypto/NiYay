"""
NEXUS GOD WRITER - Entry Point

Run: python main.py
"""

from nexus_god.ui.app import run_app
from nexus_god.ui.project_selector import show_project_selector

if __name__ == "__main__":
    # แสดงหน้าเลือกโปรเจกต์ก่อน
    selected_project = show_project_selector()
    
    # ถ้าเลือกโปรเจกต์แล้ว ให้เข้าโปรแกรม
    if selected_project:
        run_app()
