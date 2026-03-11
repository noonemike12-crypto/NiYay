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
        tk.Label(parent, text="บันทึกประวัติศาสตร์โลก แบ่งตามยุคสมัย (Era) และเหตุการณ์ (Event)", font=("Segoe UI", 9), bg=parent["bg"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 10))
        
        # Structured timeline input
        self.timeline_text = self.create_input(parent, "ประวัติศาสตร์ (รูปแบบ: [ยุค] ปี: เหตุการณ์ - รายละเอียด)", height=15)
        
        # Load existing data
        timeline_data = self.dm.data["world"].get("timeline", [])
        if isinstance(timeline_data, list):
            text = ""
            for item in timeline_data:
                if isinstance(item, dict):
                    text += f"[{item.get('era', '')}] {item.get('year', '')}: {item.get('event', '')} - {item.get('description', '')}\n"
                else:
                    text += f"{item}\n"
            self.timeline_text.insert("1.0", text.strip())

    def build_myth_section(self, parent):
        self.myth_text = self.create_input(parent, "ตำนาน ความเชื่อ และเทพเจ้า (Mythology)", height=6)
        self.religion_text = self.create_input(parent, "ศาสนาและลัทธิต่างๆ (Religions)", height=6)
        self.magic_text = self.create_input(parent, "ระบบพลังและกฎเกณฑ์เหนือธรรมชาติ (Magic Rules)", height=6)
        
        # Load existing data
        lore = self.dm.data["world"].get("lore", {})
        self.myth_text.insert("1.0", lore.get("mythology", ""))
        self.religion_text.insert("1.0", lore.get("religions", ""))
        self.magic_text.insert("1.0", self.dm.data["world"].get("magic_system", ""))

    def build_faction_section(self, parent):
        self.faction_text = self.create_input(parent, "รายละเอียดอาณาจักร กลุ่มอำนาจ และกองกำลัง (Factions)", height=15)
        
        # Load existing data
        factions = self.dm.data["world"].get("factions", {})
        if isinstance(factions, dict):
            text = ""
            for name, data in factions.items():
                if isinstance(data, dict):
                    text += f"[{name}]\nคำอธิบาย: {data.get('description', '')}\nผู้นำ: {data.get('leader', '')}\n\n"
                else:
                    text += f"[{name}]\n{data}\n\n"
            self.faction_text.insert("1.0", text.strip())

    def save_lore(self):
        log_info("Saving lore data")
        
        # Timeline Parsing
        timeline_raw = self.timeline_text.get("1.0", tk.END).strip()
        timeline = []
        for line in timeline_raw.split("\n"):
            if not line.strip(): continue
            # Simple parser for "[Era] Year: Event - Desc"
            try:
                era = ""
                if line.startswith("[") and "]" in line:
                    era = line[1:line.find("]")]
                    line = line[line.find("]")+1:].strip()
                
                year = ""
                if ":" in line:
                    year = line.split(":", 1)[0].strip()
                    line = line.split(":", 1)[1].strip()
                
                event = line
                desc = ""
                if " - " in line:
                    event = line.split(" - ", 1)[0].strip()
                    desc = line.split(" - ", 1)[1].strip()
                
                timeline.append({"era": era, "year": year, "event": event, "description": desc})
            except:
                timeline.append(line.strip())
        
        self.dm.data["world"]["timeline"] = timeline
        
        # Mythology, Religion & Magic
        if "lore" not in self.dm.data["world"]: self.dm.data["world"]["lore"] = {}
        self.dm.data["world"]["lore"]["mythology"] = self.myth_text.get("1.0", tk.END).strip()
        self.dm.data["world"]["lore"]["religions"] = self.religion_text.get("1.0", tk.END).strip()
        self.dm.data["world"]["magic_system"] = self.magic_text.get("1.0", tk.END).strip()
        
        # Factions Parsing
        faction_raw = self.faction_text.get("1.0", tk.END).strip()
        factions = {}
        current_faction = None
        current_data = {}
        
        for line in faction_raw.split("\n"):
            if line.startswith("[") and line.endswith("]"):
                if current_faction: factions[current_faction] = current_data
                current_faction = line[1:-1]
                current_data = {"description": "", "leader": ""}
            elif ":" in line:
                key, val = line.split(":", 1)
                if "คำอธิบาย" in key: current_data["description"] = val.strip()
                elif "ผู้นำ" in key: current_data["leader"] = val.strip()
                else: current_data["description"] += line + "\n"
            else:
                if current_faction: current_data["description"] += line + "\n"
        
        if current_faction: factions[current_faction] = current_data
        self.dm.data["world"]["factions"] = factions
        
        self.dm.save_all()
        messagebox.showinfo("สำเร็จ", "บันทึกข้อมูลตำนานและประวัติศาสตร์เรียบร้อยแล้ว")
