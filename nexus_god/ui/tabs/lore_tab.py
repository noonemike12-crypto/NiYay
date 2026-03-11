import tkinter as tk
from tkinter import ttk, messagebox
from nexus_god.core.logging_utils import log_debug, log_info

class LoreTab:
    def __init__(self, parent, dm, colors, build_card, create_input):
        self.parent = parent
        self.dm = dm
        self.colors = colors
        self.build_card = build_card
        self.create_input = create_input

    def build(self):
        log_debug("Building lore content")
        card = self.build_card(self.parent, "ตำนานและประวัติศาสตร์ (Lore & History)")
        
        # Tabs for Lore sub-sections
        lore_tabs = ttk.Notebook(card)
        lore_tabs.pack(fill="both", expand=True)

        # 1. Timeline
        timeline_frame = tk.Frame(lore_tabs, bg=self.colors["card"], padx=10, pady=10)
        lore_tabs.add(timeline_frame, text="⏳ ลำดับเหตุการณ์ (Timeline)")
        self.build_timeline_section(timeline_frame)

        # 2. Mythology & Lore
        myth_frame = tk.Frame(lore_tabs, bg=self.colors["card"], padx=10, pady=10)
        lore_tabs.add(myth_frame, text="📜 ตำนานและเทพปกรณัม")
        self.build_myth_section(myth_frame)

        # 3. Factions & Kingdoms
        faction_frame = tk.Frame(lore_tabs, bg=self.colors["card"], padx=10, pady=10)
        lore_tabs.add(faction_frame, text="🏰 อาณาจักรและกลุ่มอำนาจ")
        self.build_faction_section(faction_frame)

        # Save Button at the bottom of the card
        tk.Button(card, text="บันทึกข้อมูลตำนาน 💾", command=self.save_lore, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=10).pack(fill="x", pady=(10, 0))

    def build_timeline_section(self, parent):
        tk.Label(parent, text="บันทึกเหตุการณ์สำคัญในประวัติศาสตร์ของโลกคุณ", font=("Segoe UI", 9), bg=parent["bg"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 10))
        
        # Simple text area for now, can be improved to a list later
        self.timeline_text = self.create_input(parent, "เหตุการณ์สำคัญ (เรียงตามเวลา)", height=15)
        
        # Load existing data
        timeline_data = self.dm.data["world"].get("timeline", [])
        if isinstance(timeline_data, list):
            self.timeline_text.insert("1.0", "\n".join(timeline_data))
        else:
            self.timeline_text.insert("1.0", str(timeline_data))

    def build_myth_section(self, parent):
        self.myth_text = self.create_input(parent, "ตำนาน ความเชื่อ และเทพเจ้า", height=8)
        self.magic_text = self.create_input(parent, "ระบบพลังและกฎเกณฑ์เหนือธรรมชาติ", height=8)
        
        # Load existing data
        self.myth_text.insert("1.0", self.dm.data["world"].get("lore", {}).get("mythology", ""))
        self.magic_text.insert("1.0", self.dm.data["world"].get("magic_system", ""))

    def build_faction_section(self, parent):
        self.faction_text = self.create_input(parent, "รายละเอียดอาณาจักรและกลุ่มต่างๆ", height=15)
        
        # Load existing data
        factions = self.dm.data["world"].get("factions", {})
        if isinstance(factions, dict):
            text = ""
            for name, desc in factions.items():
                text += f"[{name}]\n{desc}\n\n"
            self.faction_text.insert("1.0", text.strip())
        else:
            self.faction_text.insert("1.0", str(factions))

    def save_lore(self):
        log_info("Saving lore data")
        
        # Timeline
        timeline_raw = self.timeline_text.get("1.0", tk.END).strip()
        self.dm.data["world"]["timeline"] = [line.strip() for line in timeline_raw.split("\n") if line.strip()]
        
        # Mythology & Magic
        if "lore" not in self.dm.data["world"]: self.dm.data["world"]["lore"] = {}
        self.dm.data["world"]["lore"]["mythology"] = self.myth_text.get("1.0", tk.END).strip()
        self.dm.data["world"]["magic_system"] = self.magic_text.get("1.0", tk.END).strip()
        
        # Factions (Simple parsing)
        faction_raw = self.faction_text.get("1.0", tk.END).strip()
        # This is a simple parser for [Kingdom Name] format
        factions = {}
        current_faction = None
        current_desc = []
        
        for line in faction_raw.split("\n"):
            if line.startswith("[") and line.endswith("]"):
                if current_faction:
                    factions[current_faction] = "\n".join(current_desc).strip()
                current_faction = line[1:-1]
                current_desc = []
            else:
                current_desc.append(line)
        
        if current_faction:
            factions[current_faction] = "\n".join(current_desc).strip()
            
        self.dm.data["world"]["factions"] = factions
        
        self.dm.save_all()
        messagebox.showinfo("สำเร็จ", "บันทึกข้อมูลตำนานและประวัติศาสตร์เรียบร้อยแล้ว")
