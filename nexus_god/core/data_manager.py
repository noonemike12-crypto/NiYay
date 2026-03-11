from __future__ import annotations

import json
import threading
from pathlib import Path
from datetime import datetime
from tkinter import messagebox

from .logging_utils import log_error, log_debug, log_info


class NexusDataManager:
    def __init__(self):
        log_debug("Initializing NexusDataManager")
        self.data_dir = Path("nexus_god_data")
        self.projects_dir = self.data_dir / "projects"
        self.data_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)
        
        self.config_file = self.data_dir / "config.json"
        self.config = self.load_config()

        # Current project name
        self.current_project = self.config.get("last_project", "Default_Story")
        self.project_path = self.projects_dir / self.current_project
        self.project_path.mkdir(exist_ok=True)
        
        # Files within project
        self.metadata_file = self.project_path / "metadata.json"
        self.world_file = self.project_path / "world.json"
        self.facts_file = self.project_path / "facts.json"
        self.modules_dir = self.project_path / "modules"
        self.modules_dir.mkdir(exist_ok=True)
        self.story_dir = self.project_path / "story"
        self.story_dir.mkdir(exist_ok=True)
        
        self.data = self.load_data()

    def load_data(self):
        log_debug(f"Loading data for project: {self.current_project}")
        
        # 1. Metadata
        metadata = {
            "name": self.current_project, 
            "genre": "ทั่วไป", 
            "theme": "", 
            "world_type": "fantasy", 
            "created_at": str(datetime.now()), 
            "enabled_tabs": ["wizard", "chat", "world", "lore", "chars", "items", "plot", "editor", "memory", "review", "export", "settings"],
            "creation_phase": "synopsis"
        }
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                metadata.update(json.load(f))
        
        # 2. World
        world = {"name": "", "theme": "", "geography": "", "climate": "", "rules": "", "genre": "ทั่วไป", "culture": "", "sensory": "", "synopsis": "", "timeline": [], "lore": {}, "factions": {}, "magic_system": ""}
        if self.world_file.exists():
            with open(self.world_file, "r", encoding="utf-8") as f:
                world.update(json.load(f))
        
        # 3. Facts
        facts = []
        if self.facts_file.exists():
            with open(self.facts_file, "r", encoding="utf-8") as f:
                facts = json.load(f)
        
        # 4. Modules
        modules = {}
        for f in self.modules_dir.glob("*.json"):
            with open(f, "r", encoding="utf-8") as m_file:
                modules[f.stem] = json.load(m_file)
        
        # 5. Story (Chapters)
        chapters = {}
        chapters_file = self.story_dir / "chapters.json"
        if chapters_file.exists():
            with open(chapters_file, "r", encoding="utf-8") as f:
                chapters = json.load(f)
        
        # 6. Plot
        plot = {"act1": "", "act2": "", "act3": "", "key_events": "", "ending": ""}
        plot_file = self.project_path / "plot.json"
        if plot_file.exists():
            with open(plot_file, "r", encoding="utf-8") as f:
                plot.update(json.load(f))

        # Combine into a single data object for the app to use (maintaining compatibility)
        return {
            "metadata": metadata,
            "world": world,
            "facts": facts,
            "modules": modules,
            "chapters": chapters,
            "plot": plot,
            "characters": modules.get("characters", {}), # Compatibility
            "items": modules.get("items", {}), # Compatibility
            "memory": {f["id"]: f["content"] for f in facts if isinstance(f, dict) and "id" in f}, # Compatibility
            "enabled_tabs": metadata.get("enabled_tabs", []),
            "creation_phase": metadata.get("creation_phase", "synopsis"),
            "project_genre": metadata.get("genre", ""),
        }

    def load_config(self):
        log_debug("Loading configuration")
        default_config = {
            "api_key": "",
            "model": "gemini-2.0-flash",
            "theme": "dark",
            "last_project": "Default_Story",
            "ai_provider": "gemini",
            "groq_api_key": "",
            "groq_model": "llama-3.3-70b-versatile",
            # Custom character fields system
            "default_character_fields": [
                {"key": "name", "label": "ชื่อ", "type": "text", "required": True},
                {"key": "role", "label": "บทบาท", "type": "text", "required": False},
                {"key": "personality", "label": "บุคลิกภาพ", "type": "textarea", "required": False},
                {"key": "appearance", "label": "รูปลักษณ์", "type": "textarea", "required": False},
                {"key": "powers", "label": "พลัง/ความสามารถ", "type": "textarea", "required": False},
                {"key": "relationships", "label": "ความสัมพันธ์", "type": "textarea", "required": False},
                {"key": "backstory", "label": "ปูมหลัง", "type": "textarea", "required": False},
            ],
            "custom_character_fields": [],  # User-created custom fields
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    if not isinstance(c, dict):
                        return default_config
                    # Ensure all default keys exist
                    for k, v in default_config.items():
                        if k not in c:
                            c[k] = v
                    # Migrate old configs
                    if "default_character_fields" not in c:
                        c["default_character_fields"] = default_config["default_character_fields"]
                    if "custom_character_fields" not in c:
                        c["custom_character_fields"] = []
                    return c
            except Exception as e:
                log_error(f"Error loading config: {e}")
        return default_config

    def save_all(self):
        # Run saving in a background thread to prevent UI hang
        log_debug("Initiating save_all (Multi-file structure)")
        try:
            data = self.data
            config_copy = json.loads(json.dumps(self.config))

            def task():
                try:
                    # Save Metadata
                    with open(self.metadata_file, "w", encoding="utf-8") as f:
                        json.dump(data["metadata"], f, ensure_ascii=False, indent=2)
                    
                    # Save World
                    with open(self.world_file, "w", encoding="utf-8") as f:
                        json.dump(data["world"], f, ensure_ascii=False, indent=2)
                    
                    # Save Facts
                    with open(self.facts_file, "w", encoding="utf-8") as f:
                        json.dump(data["facts"], f, ensure_ascii=False, indent=2)
                    
                    # Save Modules
                    for mod_id, mod_data in data["modules"].items():
                        mod_file = self.modules_dir / f"{mod_id}.json"
                        with open(mod_file, "w", encoding="utf-8") as f:
                            json.dump(mod_data, f, ensure_ascii=False, indent=2)
                    
                    # Save Story
                    with open(self.story_dir / "chapters.json", "w", encoding="utf-8") as f:
                        json.dump(data["chapters"], f, ensure_ascii=False, indent=2)
                    
                    # Save Plot
                    with open(self.project_path / "plot.json", "w", encoding="utf-8") as f:
                        json.dump(data["plot"], f, ensure_ascii=False, indent=2)
                        
                    # Save Config
                    with open(self.config_file, "w", encoding="utf-8") as f:
                        json.dump(config_copy, f, ensure_ascii=False, indent=2)
                        
                except Exception as e:
                    log_error(f"Async Save Error: {e}")

            threading.Thread(target=task, daemon=True).start()
        except Exception as e:
            log_error(f"Error initiating async save: {e}")

    def save_config(self):
        """Save only the application configuration."""
        log_debug("Saving configuration")
        try:
            config_copy = json.loads(json.dumps(self.config))
            def task():
                try:
                    with open(self.config_file, "w", encoding="utf-8") as f:
                        json.dump(config_copy, f, ensure_ascii=False)
                except Exception as e:
                    log_error(f"Error saving config: {e}")
            threading.Thread(target=task, daemon=True).start()
        except Exception as e:
            log_error(f"Error initiating config save: {e}")

    def save_sync(self):
        """Synchronous save for graceful shutdown."""
        log_info("Performing synchronous save...")
        try:
            with open(self.project_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False)
            log_info("Synchronous save completed.")
        except Exception as e:
            log_error(f"Error during synchronous save: {e}")

    def list_projects(self):
        try:
            return [d.name for d in self.projects_dir.iterdir() if d.is_dir()]
        except Exception as e:
            log_error(f"Error listing projects: {e}")
            return ["Default_Story"]

    def switch_project(self, name):
        log_info(f"Switching to project: {name}")
        try:
            self.save_all()
            self.current_project = name
            self.config["last_project"] = name
            
            self.project_path = self.projects_dir / name
            self.project_path.mkdir(exist_ok=True)
            
            self.metadata_file = self.project_path / "metadata.json"
            self.world_file = self.project_path / "world.json"
            self.facts_file = self.project_path / "facts.json"
            self.modules_dir = self.project_path / "modules"
            self.modules_dir.mkdir(exist_ok=True)
            self.story_dir = self.project_path / "story"
            self.story_dir.mkdir(exist_ok=True)
            
            self.data = self.load_data()
            self.save_all()
        except Exception as e:
            log_error(f"Error switching project: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถสลับโปรเจกต์ได้: {e}")
