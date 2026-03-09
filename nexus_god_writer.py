import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import os
import sys
import traceback
import logging
from pathlib import Path
import threading
from datetime import datetime

# ========== LOGGING SETUP ==========
log_dir = Path("nexus_god_logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"nexus_log_{datetime.now().strftime('%Y%m%d')}.txt"

logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def log_error(msg):
    logging.error(msg)
    print(f"ERROR: {msg}")

# Global Thread Exception Handler
def thread_exception_handler(args):
    err_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    log_error(f"Thread Exception: {err_msg}")

threading.excepthook = thread_exception_handler

# พยายาม import library สำหรับ AI
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    log_error("Failed to import google-genai library")

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    log_error("Failed to import groq library")

# ========== PROMPTS & AI CONFIG ==========
class NexusPrompts:
    @staticmethod
    def get_architect_system(phase, data_summary, memory_context):
        return f"""คุณคือ "Divine Architect" (สถาปนิกสวรรค์) ผู้เป็นเจ้าแห่งการสรรค์สร้างและคัมภีร์นิยายระดับสูงสุด
        หน้าที่ของคุณคือการเป็นผู้นำทางและผู้เนรมิตโลกนิยายร่วมกับผู้ใช้ (The Creator) โดยคุณต้องมีความคิดริเริ่มและไม่รอเพียงคำสั่ง

        เฟสการสร้างปัจจุบัน: {phase}
        (ลำดับเฟส: synopsis -> planning -> world -> characters -> story)

        บุคลิกภาพ:
        - ทรงพลัง, รอบรู้ทุกสรรพสิ่ง, มีวิสัยทัศน์กว้างไกล และมีความคิดสร้างสรรค์ที่ไร้ขีดจำกัด
        - ใช้ภาษาที่ดูภูมิฐาน สูงส่ง แต่แฝงด้วยความเมตตาและชาญฉลาด (สไตล์เทพเจ้าผู้ยิ่งใหญ่)
        - **ห้ามตอบสั้นๆ** หรือตอบแบบหุ่นยนต์ ทุกคำตอบต้องเปี่ยมด้วยรายละเอียด บรรยากาศ และอารมณ์ที่ดึงดูด
        - **มีความคิดริเริ่ม (Proactive)**: หากผู้ใช้ให้ไอเดียเพียงเล็กน้อย คุณต้องขยายความให้กลายเป็นมหากาพย์ หรือเสนอทางเลือก "วิถีแห่งสวรรค์" (Divine Paths) 3 ทางเลือกที่แตกต่างกันเพื่อให้ผู้ใช้เลือกเดินต่อ

        กฎเหล็กแห่งสวรรค์:
        1. **ความละเอียดคือพลังสูงสุด**: เมื่อบรรยายเหตุการณ์หรือสถานที่ ให้เน้นประสาทสัมผัสและบริบททางสังคมให้สมจริง
        2. **การจัดการคัมภีร์อย่างชาญฉลาด**: ใช้ฟิลด์ "update" เพื่อบันทึกข้อมูลสำคัญ (world, plot, characters, items, memory_bank)
        3. **ธนาคารความจำ**: เชื่อมโยงเหตุการณ์ในอดีตและปัจจุบันให้สอดคล้องกัน
        4. **การตอบกลับ**: ต้องเป็น JSON Object ที่มี: "reply" (ข้อความไทย), "update" (Optional), "suggestions" (Optional)

        ข้อมูลโปรเจกต์ปัจจุบัน:
        {data_summary}

        ข้อมูลจากธนาคารความจำ:
        {memory_context}"""

    REVIEWER_SYSTEM = """คุณคือ "Divine Reviewer" ผู้เชี่ยวชาญด้านการเขียนนิยายและการพิสูจน์อักษร
    หน้าที่ของคุณคือตรวจสอบข้อมูลในคัมภีร์นิยายนี้ เพื่อหาคำผิด การจัดรูปแบบ และข้อเสนอแนะ
    ให้ตอบกลับเป็น JSON array ของวัตถุที่มีโครงสร้างดังนี้เท่านั้น:
    [{"path": "...", "label": "...", "original": "...", "suggested": "...", "reason": "...", "type": "..."}]"""

    PLANNER_SYSTEM = "คุณคือผู้เชี่ยวชาญด้านการวางโครงสร้างนิยาย ให้คำแนะนำที่สร้างสรรค์และเป็นระบบ"
    
    JSON_ARCHITECT_SYSTEM = "คุณคือ Divine Architect ให้ตอบกลับเป็น JSON Object ที่มี 'reply' (คำอธิบายเหตุผล) และ 'update' (ข้อมูลที่ต้องการบันทึก)"

# ========== DATA & CONFIG MANAGER ==========
class NexusDataManager:
    def __init__(self):
        self.data_dir = Path("nexus_god_data")
        self.data_dir.mkdir(exist_ok=True)
        self.config_file = self.data_dir / "config.json"
        self.config = self.load_config()
        
        # จัดการชื่อโปรเจกต์ปัจจุบัน
        self.current_project = self.config.get("last_project", "Default_Story")
        self.project_file = self.data_dir / f"project_{self.current_project}.json"
        self.data = self.load_data()

    def load_data(self):
        default_data = {
            "world": {"name": "", "theme": "", "geography": "", "climate": "", "rules": "", "genre": "ทั่วไป", "culture": "", "sensory": "", "synopsis": ""},
            "characters": [],
            "plot": {"act1": "", "act2": "", "act3": "", "key_events": "", "ending": ""},
            "chapters": [],
            "memory_bank": [],
            "items": [],
            "style": "มาตรฐาน",
            "chat_history": [],
            "creation_phase": "synopsis" # phases: synopsis, planning, world, characters, story
        }
        
        if self.project_file.exists():
            try:
                with open(self.project_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    # Migration สำหรับฟิลด์ใหม่ และความปลอดภัยของข้อมูล
                    if not isinstance(d, dict): return default_data
                    
                    if "world" not in d: d["world"] = default_data["world"]
                    if "characters" not in d: d["characters"] = []
                    if "plot" not in d: d["plot"] = default_data["plot"]
                    if "chapters" not in d: d["chapters"] = []
                    if "memory_bank" not in d: d["memory_bank"] = []
                    if "items" not in d: d["items"] = []
                    if "chat_history" not in d: d["chat_history"] = []
                    if "creation_phase" not in d: d["creation_phase"] = "synopsis"
                    
                    # Sub-fields migration
                    for k, v in default_data["world"].items():
                        if k not in d["world"]: d["world"][k] = v
                    
                    if "style" not in d: d["style"] = "มาตรฐาน"
                    return d
            except Exception as e:
                log_error(f"Error loading project data: {e}")
                messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถโหลดข้อมูลโปรเจกต์ได้: {e}\nระบบจะใช้ข้อมูลเริ่มต้นแทน")
        
        return default_data

    def load_config(self):
        default_config = {
            "api_key": "", 
            "model": "gemini-2.0-flash", 
            "theme": "dark", 
            "last_project": "Default_Story",
            "ai_provider": "gemini",
            "groq_api_key": "",
            "groq_model": "llama-3.3-70b-versatile"
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    if not isinstance(c, dict): return default_config
                    # Ensure all default keys exist
                    for k, v in default_config.items():
                        if k not in c: c[k] = v
                    return c
            except Exception as e:
                log_error(f"Error loading config: {e}")
        return default_config

    def save_all(self):
        # Run saving in a background thread to prevent UI hang
        try:
            data_copy = json.loads(json.dumps(self.data)) # Simple deep copy
            config_copy = json.loads(json.dumps(self.config))
            
            def task():
                try:
                    # Save Project Data (No indent for speed and size)
                    with open(self.project_file, "w", encoding="utf-8") as f:
                        json.dump(data_copy, f, ensure_ascii=False)
                    
                    # Save Config
                    with open(self.config_file, "w", encoding="utf-8") as f:
                        json.dump(config_copy, f, ensure_ascii=False)
                    
                    # Create a backup of project data
                    backup_file = self.data_dir / f"backup_{self.current_project}.json"
                    with open(backup_file, "w", encoding="utf-8") as f:
                        json.dump(data_copy, f, ensure_ascii=False)
                except Exception as e:
                    print(f"ERROR: Async Save Error: {e}")
            
            threading.Thread(target=task, daemon=True).start()
        except Exception as e:
            log_error(f"Error initiating async save: {e}")

    def deep_update(self, source, overrides):
        """Recursively updates a dictionary with another, handling specific list types for the app."""
        for key, value in overrides.items():
            if key in ["characters", "items"] and isinstance(value, list):
                if key not in source: source[key] = []
                for item in value:
                    if isinstance(item, dict) and "name" in item:
                        # Find existing by name to update instead of duplicate
                        existing_idx = next((i for i, x in enumerate(source[key]) if x.get("name") == item["name"]), None)
                        if existing_idx is not None:
                            source[key][existing_idx].update(item)
                        else:
                            source[key].append(item)
                    elif item not in source[key]:
                        source[key].append(item)
            elif key == "memory_bank" and isinstance(value, list):
                if key not in source: source[key] = []
                for item in value:
                    if item not in source[key]:
                        source[key].append(item)
            elif isinstance(value, dict) and key in source and isinstance(source[key], dict):
                self.deep_update(source[key], value)
            else:
                source[key] = value
        return source

    def get_genre_config(self, genre=None):
        if not genre:
            genre = self.data["world"].get("genre", "ทั่วไป")
            
        # Default labels
        config = {
            "world_rules": "กฎของโลก (ระบบเวทมนตร์/เทคโนโลยี)",
            "char_powers": "พลัง / ทักษะพิเศษ",
            "char_role_hint": "เช่น ผู้กล้า, จอมมาร",
            "item_tab": "ไอเทมและวัตถุโบราณ",
            "item_card": "คลังไอเทม (Item Database)",
            "item_type": "ประเภท (เช่น อาวุธ, ของวิเศษ)",
            "item_abilities": "ความสามารถ / ตำนาน"
        }
        
        if "ความรัก" in genre or "ชีวิตประจำวัน" in genre:
            config.update({
                "world_rules": "บรรทัดฐานทางสังคม / อุปสรรคความรัก",
                "char_powers": "ภาษารัก / เสน่ห์ดึงดูด",
                "char_role_hint": "เช่น พระเอก, นางเอก, มือที่สาม",
                "item_tab": "ของที่ระลึกและสิ่งของแทนใจ",
                "item_card": "คลังความทรงจำ (Memory Objects)",
                "item_type": "ประเภท (เช่น ของขวัญ, จดหมาย)",
                "item_abilities": "ความหมาย / ความทรงจำที่เกี่ยวข้อง"
            })
        elif "สืบสวน" in genre:
            config.update({
                "world_rules": "กฎหมาย / กระบวนการยุติธรรม",
                "char_powers": "ทักษะการสืบสวน / ความเชี่ยวชาญ",
                "char_role_hint": "เช่น นักสืบ, ผู้ต้องสงสัย",
                "item_tab": "หลักฐานและเบาะแส",
                "item_card": "ฐานข้อมูลหลักฐาน (Evidence DB)",
                "item_type": "ประเภท (เช่น อาวุธสังหาร, ลายนิ้วมือ)",
                "item_abilities": "ความเกี่ยวข้องกับคดี"
            })
        return config

    def get_genre_templates(self):
        return {
            "แฟนตาซีระดับสูง (High Fantasy)": {"theme": "การต่อสู้ระดับมหากาพย์, เวทมนตร์โบราณ", "rules": "เวทมนตร์ต้องใช้มานา, มีมังกรอยู่จริง", "culture": "ระบอบกษัตริย์, สมาคมนักผจญภัย"},
            "ไซเบอร์พังก์": {"theme": "เทคโนโลยีล้ำสมัย แต่คุณภาพชีวิตต่ำ", "rules": "การปลูกถ่ายไซเบอร์เนติก, การปกครองโดยบริษัท", "culture": "สลัมแสงนีออน, บริษัทยักษ์ใหญ่"},
            "ดาร์กแฟนตาซี": {"theme": "การดิ้นรนที่โหดร้าย, เวทมนตร์ต้องห้าม", "rules": "เวทมนตร์กัดกินผู้ใช้, สัตว์ประหลาดในเงามืด", "culture": "อาณาจักรที่ล่มสลาย, ความเชื่อเรื่องโชคลาง"},
            "ความรัก / โรแมนติก": {"theme": "ความรักที่ต้องฝ่าฟันอุปสรรคทางฐานะ", "rules": "กฎเกณฑ์ทางสังคมที่เข้มงวด, การคลุมถุงชน", "culture": "สังคมชั้นสูง, งานเลี้ยงเต้นรำ"},
            "ชีวิตประจำวัน / ฟีลกู๊ด": {"theme": "ความสุขในสิ่งเล็กๆ น้อยๆ", "rules": "มารยาททางสังคมทั่วไป", "culture": "เมืองเล็กๆ ที่อบอุ่น, ร้านกาแฟประจำ"}
        }

    def list_projects(self):
        try:
            return [f.stem.replace("project_", "") for f in self.data_dir.glob("project_*.json")]
        except Exception as e:
            log_error(f"Error listing projects: {e}")
            return ["Default_Story"]

    def switch_project(self, name):
        try:
            self.save_all()
            self.current_project = name
            self.config["last_project"] = name
            self.project_file = self.data_dir / f"project_{name}.json"
            self.data = self.load_data()
            self.save_all()
        except Exception as e:
            log_error(f"Error switching project: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถสลับโปรเจกต์ได้: {e}")

# ========== ULTIMATE UI COMPONENTS ==========
class NexusGodWriter:
    def __init__(self, root):
        self.root = root
        self.root.title("🌌 NEXUS GOD WRITER - ULTIMATE CREATOR EDITION (ภาษาไทย)")
        self.root.geometry("1500x950")
        
        # Global Exception Handler for Tkinter
        self.root.report_callback_exception = self.handle_exception
        
        try:
            self.dm = NexusDataManager()
        except Exception as e:
            log_error(f"Critical error initializing Data Manager: {e}")
            messagebox.showerror("ข้อผิดพลาดร้ายแรง", f"ไม่สามารถเริ่มต้นระบบจัดการข้อมูลได้: {e}")
            sys.exit(1)
            
        self.current_ch_idx = None
        self.current_tab = "chat"
        
        # Initialize style_var early to prevent AttributeError in save_all_data
        self.style_var = tk.StringVar(value=self.dm.data.get("style", "มาตรฐาน"))
        
        # Themes
        self.themes = {
            "dark": {
                "bg": "#0f172a", "sidebar": "#1e293b", "card": "#1e293b", "input": "#0f172a",
                "accent": "#38bdf8", "text": "#f8fafc", "muted": "#94a3b8", "border": "#334155",
                "success": "#10b981", "danger": "#ef4444", "warning": "#f59e0b"
            },
            "light": {
                "bg": "#f1f5f9", "sidebar": "#e2e8f0", "card": "#ffffff", "input": "#f8fafc",
                "accent": "#0ea5e9", "text": "#0f172a", "muted": "#64748b", "border": "#cbd5e1",
                "success": "#059669", "danger": "#dc2626", "warning": "#d97706"
            }
        }
        self.colors = self.themes.get(self.dm.config.get("theme", "dark"), self.themes["dark"])
        
        self.root.configure(bg=self.colors["bg"])
        
        try:
            self.build_layout()
            self.start_autosave()
            logging.info("Application started successfully")
        except Exception as e:
            log_error(f"Error building layout: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการสร้างหน้าจอ: {e}")

    def handle_exception(self, exc, val, tb):
        err_msg = "".join(traceback.format_exception(exc, val, tb))
        log_error(f"Unhandled Exception: {err_msg}")
        messagebox.showerror("เกิดข้อผิดพลาดที่ไม่คาดคิด", 
                             f"โปรแกรมพบข้อผิดพลาด แต่จะพยายามทำงานต่อไป:\n\n{str(val)}\n\nกรุณาตรวจสอบไฟล์ Log เพื่อดูรายละเอียด")

    def build_layout(self):
        # --- Sidebar ---
        self.sidebar = tk.Frame(self.root, bg=self.colors["sidebar"], width=280)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"], pady=25)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="🌌", font=("Segoe UI", 32), bg=self.colors["sidebar"]).pack()
        tk.Label(logo_frame, text="NEXUS GOD", font=("Segoe UI", 16, "bold"), bg=self.colors["sidebar"], fg=self.colors["accent"]).pack()
        
        # Progress Section
        self.prog_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"], pady=10)
        self.prog_frame.pack(fill="x", padx=20)
        tk.Label(self.prog_frame, text="CREATION PROGRESS", font=("Segoe UI", 7, "bold"), bg=self.colors["sidebar"], fg=self.colors["muted"]).pack(anchor="w")
        self.progress = ttk.Progressbar(self.prog_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(fill="x", pady=5)
        self.prog_label = tk.Label(self.prog_frame, text="0%", font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["accent"])
        self.prog_label.pack(anchor="e")

        # Nav Buttons
        self.nav_btns = {}
        nav_items = [
            ("wizard", "✨ วิถีแห่งสวรรค์ (Guided)"),
            ("chat", "💬 สนทนาทวยเทพ"),
            ("world", "🌍 กำเนิดโลก"),
            ("chars", "👤 โรงหล่อตัวละคร"),
            ("items", "⚔️ คลังไอเทม"),
            ("plot", "📜 โครงเรื่องสวรรค์"),
            ("editor", "📝 แก้ไขเนื้อเรื่อง"),
            ("memory", "🧠 ธนาคารความจำ"),
            ("review", "🔍 ตรวจสอบคัมภีร์"),
            ("export", "🚀 AI และส่งออก"),
            ("settings", "⚙️ ตั้งค่า")
        ]
        
        for key, label in nav_items:
            btn = tk.Button(self.sidebar, text=f"  {label}", font=("Segoe UI", 10), 
                            bg=self.colors["sidebar"], fg=self.colors["muted"], 
                            activebackground=self.colors["accent"], activeforeground="black",
                            bd=0, anchor="w", padx=20, pady=10, cursor="hand2",
                            command=lambda k=key: self.switch_tab(k))
            btn.pack(fill="x", padx=10, pady=1)
            self.nav_btns[key] = btn

        # Quick Actions
        qa_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"], pady=10)
        qa_frame.pack(fill="x", padx=10)
        tk.Button(qa_frame, text="💬 เริ่มต้นคุยกับ AI", font=("Segoe UI", 8, "bold"), bg=self.colors["warning"], fg="black", bd=0, pady=8, command=lambda: self.switch_tab("chat")).pack(fill="x", pady=5)
        tk.Button(qa_frame, text="🎲 เหตุการณ์สุ่ม", font=("Segoe UI", 8, "bold"), bg=self.colors["accent"], fg="black", bd=0, pady=8, command=self.random_event).pack(fill="x", pady=5)
        tk.Button(qa_frame, text="📂 สลับโปรเจกต์", font=("Segoe UI", 8, "bold"), bg=self.colors["muted"], fg="white", bd=0, pady=8, command=self.manage_projects).pack(fill="x", pady=5)

        # Footer
        footer = tk.Frame(self.sidebar, bg=self.colors["sidebar"], pady=20)
        footer.pack(side="bottom", fill="x")
        self.status_label = tk.Label(footer, text="ระบบพร้อมใช้งาน", font=("Segoe UI", 7), bg=self.colors["sidebar"], fg=self.colors["muted"])
        self.status_label.pack(pady=5)
        tk.Button(footer, text="💾 บันทึกโปรเจกต์", font=("Segoe UI", 9, "bold"), 
                  bg=self.colors["success"], fg="white", bd=0, pady=12, cursor="hand2",
                  command=self.save_all_data).pack(fill="x", padx=20)

        # --- Main Content Area ---
        self.content_area = tk.Frame(self.root, bg=self.colors["bg"])
        self.content_area.pack(side="left", fill="both", expand=True)
        self.container = tk.Frame(self.content_area, bg=self.colors["bg"], padx=40, pady=30)
        self.container.pack(fill="both", expand=True)

        self.switch_tab("wizard" if self.dm.data.get("creation_phase") != "story" else "chat")

    def manage_projects(self):
        w = tk.Toplevel(self.root)
        w.title("📂 จัดการโปรเจกต์")
        w.geometry("400x500")
        w.configure(bg=self.colors["card"])

        tk.Label(w, text="โปรเจกต์ของคุณ", font=("Segoe UI", 12, "bold"), bg=self.colors["card"], fg=self.colors["accent"]).pack(pady=20)
        
        list_frame = tk.Frame(w, bg=self.colors["card"])
        list_frame.pack(fill="both", expand=True, padx=20)
        
        lb = tk.Listbox(list_frame, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 10))
        lb.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(list_frame)
        sb.pack(side="right", fill="y")
        lb.config(yscrollcommand=sb.set)
        sb.config(command=lb.yview)

        for p in self.dm.list_projects():
            lb.insert(tk.END, p)

        def on_switch():
            sel = lb.curselection()
            if sel:
                name = lb.get(sel[0])
                self.dm.switch_project(name)
                w.destroy()
                self.switch_tab("chat")
                messagebox.showinfo("สำเร็จ", f"สลับไปยังโปรเจกต์ '{name}' เรียบร้อยแล้ว")

        def on_new():
            new_name = filedialog.asksaveasfilename(initialdir="nexus_god_data", title="สร้างโปรเจกต์ใหม่", filetypes=[("JSON files", "*.json")])
            if new_name:
                name = Path(new_name).stem.replace("project_", "")
                self.dm.switch_project(name)
                w.destroy()
                self.switch_tab("chat")
                messagebox.showinfo("สำเร็จ", f"สร้างโปรเจกต์ '{name}' เรียบร้อยแล้ว")

        btn_f = tk.Frame(w, bg=self.colors["card"], pady=20)
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="สลับโปรเจกต์", command=on_switch, bg=self.colors["accent"], fg="black", bd=0, padx=20, pady=10).pack(side="left", expand=True, padx=5)
        tk.Button(btn_f, text="สร้างใหม่", command=on_new, bg=self.colors["success"], fg="white", bd=0, padx=20, pady=10).pack(side="left", expand=True, padx=5)

    def switch_tab(self, tab_key):
        self.current_tab = tab_key
        for k, btn in self.nav_btns.items():
            btn.config(bg=self.colors["accent"] if k == tab_key else self.colors["sidebar"], 
                       fg="black" if k == tab_key else self.colors["muted"])
        
        for widget in self.container.winfo_children(): widget.destroy()
            
        if tab_key == "wizard": self.build_wizard_content()
        elif tab_key == "chat": self.build_chat_content()
        elif tab_key == "world": self.build_world_content()
        elif tab_key == "chars": self.build_char_content()
        elif tab_key == "items": self.build_item_content()
        elif tab_key == "plot": self.build_plot_content()
        elif tab_key == "editor": self.build_editor_content()
        elif tab_key == "memory": self.build_memory_content()
        elif tab_key == "review": self.build_review_content()
        elif tab_key == "export": self.build_export_content()
        elif tab_key == "settings": self.build_settings_content()
        self.update_progress()

    def build_wizard_content(self):
        phase = self.dm.data.get("creation_phase", "synopsis")
        g_config = self.dm.get_genre_config()
        card = self.build_card(self.container, "วิถีแห่งการสรรค์สร้าง (The Divine Path)")
        
        # Progress Steps Header
        steps_f = tk.Frame(card, bg=card["bg"])
        steps_f.pack(fill="x", pady=(0, 20))
        
        phases = [
            ("synopsis", "1. เรื่องย่อ"),
            ("planning", "2. วางแผน"),
            ("world", "3. สร้างโลก"),
            ("characters", "4. ตัวละคร"),
            ("story", "5. เนื้อเรื่อง")
        ]
        
        for p_id, p_label in phases:
            color = self.colors["accent"] if p_id == phase else (self.colors["success"] if self.is_phase_complete(p_id, phase) else self.colors["muted"])
            lbl = tk.Label(steps_f, text=p_label, font=("Segoe UI", 9, "bold" if p_id == phase else "normal"), 
                           bg=card["bg"], fg=color)
            lbl.pack(side="left", expand=True)
            if p_id != "story":
                tk.Label(steps_f, text="→", bg=card["bg"], fg=self.colors["muted"]).pack(side="left")

        # Phase Content
        content_f = tk.Frame(card, bg=card["bg"])
        content_f.pack(fill="both", expand=True)
        
        if phase == "synopsis":
            tk.Label(content_f, text="เริ่มต้นด้วยการเขียน 'เรื่องย่อ' ของนิยายที่คุณต้องการสร้าง", font=("Segoe UI", 12), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            self.synopsis_text = scrolledtext.ScrolledText(content_f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 11), height=10, bd=0)
            self.synopsis_text.pack(fill="x", pady=10)
            self.synopsis_text.insert("1.0", self.dm.data["world"].get("synopsis", ""))
            
            tk.Button(content_f, text="บันทึกและไปต่อ →", command=self.save_synopsis_and_next, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=10, padx=30).pack(pady=20)
            
        elif phase == "planning":
            tk.Label(content_f, text="Divine Architect กำลังวิเคราะห์และแนะนำแนวทางสำหรับนิยายของคุณ...", font=("Segoe UI", 11), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            self.plan_display = scrolledtext.ScrolledText(content_f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=15, bd=0, state="disabled")
            self.plan_display.pack(fill="both", expand=True, pady=10)
            
            btn_f = tk.Frame(content_f, bg=card["bg"])
            btn_f.pack(fill="x", pady=10)
            tk.Button(btn_f, text="← ย้อนกลับ", command=lambda: self.set_phase("synopsis"), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, pady=10, padx=20).pack(side="left")
            tk.Button(btn_f, text="รับคำแนะนำเบื้องต้น ✨", command=self.get_ai_planning, bg=self.colors["accent"], fg="black", bd=0, pady=10, padx=20).pack(side="left", padx=10)
            tk.Button(btn_f, text="ขอ 'วิถีแห่งสวรรค์' (Complete Package) 🌌", command=self.get_divine_package, bg=self.colors["warning"], fg="black", bd=0, pady=10, padx=20).pack(side="left", padx=10)
            tk.Button(btn_f, text="ไปสู่การสร้างโลก →", command=lambda: self.set_phase("world"), bg=self.colors["success"], fg="white", bd=0, pady=10, padx=20).pack(side="right")

        elif phase == "world":
            tk.Label(content_f, text="กำหนดรายละเอียดของโลกตามความสำคัญ (AI จะช่วยแนะนำฟิลด์ที่จำเป็น)", font=("Segoe UI", 11), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            # Simplified world building for wizard
            self.wizard_world_name = self.create_input(content_f, "ชื่อโลก / ชื่อเรื่อง")
            self.wizard_world_genre = self.create_input(content_f, "แนวเรื่อง (Genre)")
            self.wizard_world_rules = self.create_input(content_f, g_config["world_rules"], 4)
            
            self.wizard_world_name.insert(0, self.dm.data["world"].get("name", ""))
            self.wizard_world_genre.insert(0, self.dm.data["world"].get("genre", ""))
            self.wizard_world_rules.insert("1.0", self.dm.data["world"].get("rules", ""))

            btn_f = tk.Frame(content_f, bg=card["bg"])
            btn_f.pack(fill="x", pady=20)
            tk.Button(btn_f, text="← ย้อนกลับ", command=lambda: self.set_phase("planning"), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, pady=10, padx=20).pack(side="left")
            tk.Button(btn_f, text="บันทึกและไปสร้างตัวละคร →", command=self.save_wizard_world, bg=self.colors["success"], fg="white", bd=0, pady=10, padx=20).pack(side="right")

        elif phase == "characters":
            tk.Label(content_f, text="เนรมิตตัวละครหลักและรอง (AI จะช่วยสร้างพื้นฐานให้คุณปรับแต่ง)", font=("Segoe UI", 11), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            
            self.wizard_char_display = scrolledtext.ScrolledText(content_f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=12, bd=0, state="disabled")
            self.wizard_char_display.pack(fill="both", expand=True, pady=10)
            
            btn_f = tk.Frame(content_f, bg=card["bg"])
            btn_f.pack(fill="x", pady=10)
            tk.Button(btn_f, text="← ย้อนกลับ", command=lambda: self.set_phase("world"), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, pady=10, padx=20).pack(side="left")
            tk.Button(btn_f, text="ให้ AI ช่วยสร้างตัวละคร 👤", command=self.gen_wizard_chars, bg=self.colors["accent"], fg="black", bd=0, pady=10, padx=20).pack(side="left", padx=10)
            tk.Button(btn_f, text="ไปสู่การสร้างเนื้อเรื่อง →", command=lambda: self.set_phase("story"), bg=self.colors["success"], fg="white", bd=0, pady=10, padx=20).pack(side="right")

        elif phase == "story":
            tk.Label(content_f, text="ยินดีด้วย! พื้นฐานโลกและตัวละครพร้อมแล้ว ตอนนี้คุณสามารถเริ่มสร้างเนื้อเรื่องได้", font=("Segoe UI", 12, "bold"), bg=card["bg"], fg=self.colors["success"]).pack(pady=10)
            
            self.wizard_story_display = scrolledtext.ScrolledText(content_f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=12, bd=0, state="disabled")
            self.wizard_story_display.pack(fill="both", expand=True, pady=10)

            btn_f = tk.Frame(content_f, bg=card["bg"])
            btn_f.pack(fill="x", pady=10)
            tk.Button(btn_f, text="← ย้อนกลับ", command=lambda: self.set_phase("characters"), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, pady=10, padx=20).pack(side="left")
            tk.Button(btn_f, text="ให้ AI ช่วยร่างโครงเรื่อง (Plot) 📜", command=self.gen_wizard_story, bg=self.colors["accent"], fg="black", bd=0, pady=10, padx=20).pack(side="left", padx=10)
            tk.Button(btn_f, text="เข้าสู่โหมดการเขียนเต็มรูปแบบ 📝", command=lambda: self.switch_tab("editor"), bg=self.colors["success"], fg="white", font=("Segoe UI", 11, "bold"), bd=0, pady=10, padx=30).pack(side="right")
            
            tk.Button(content_f, text="เริ่มต้นใหม่ (ล้างเฟสการสร้าง)", command=lambda: self.set_phase("synopsis"), bg=self.colors["danger"], fg="white", bd=0, pady=8, padx=20).pack(pady=10)

    def is_phase_complete(self, p_id, current_phase):
        phases = ["synopsis", "planning", "world", "characters", "story"]
        return phases.index(p_id) < phases.index(current_phase)

    def set_phase(self, phase):
        self.dm.data["creation_phase"] = phase
        self.dm.save_all()
        self.switch_tab("wizard")

    def save_synopsis_and_next(self):
        syn = self.synopsis_text.get("1.0", tk.END).strip()
        if not syn:
            messagebox.showwarning("คำเตือน", "กรุณาใส่เรื่องย่อก่อนไปต่อ")
            return
        self.dm.data["world"]["synopsis"] = syn
        self.set_phase("planning")

    def save_wizard_world(self):
        self.dm.data["world"]["name"] = self.wizard_world_name.get()
        self.dm.data["world"]["genre"] = self.wizard_world_genre.get()
        self.dm.data["world"]["rules"] = self.wizard_world_rules.get("1.0", tk.END).strip()
        self.dm.save_all()
        self.set_phase("characters")

    def get_divine_package(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        
        synopsis = self.dm.data["world"].get("synopsis", "")
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังเนรมิตวิถีแห่งสวรรค์..."))
                prompt = f"จากเรื่องย่อนี้: '{synopsis}' ช่วยออกแบบ Genre, Theme, และ World Rules ที่สมบูรณ์แบบที่สุดเพียงแบบเดียว"
                res_text = self.call_ai_json(prompt, NexusPrompts.JSON_ARCHITECT_SYSTEM)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: 
                        self.apply_chat_update(update)
                        messagebox.showinfo("สำเร็จ", "วิถีแห่งสวรรค์ได้รับการจารึกลงในข้อมูลโลกแล้ว")
                    
                    self.plan_display.config(state="normal")
                    self.plan_display.delete("1.0", tk.END)
                    self.plan_display.insert(tk.END, f"--- วิถีแห่งสวรรค์ที่เลือกสรรแล้ว ---\n\n{reply}")
                    self.plan_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="จารึกวิถีแห่งสวรรค์เสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def get_ai_planning(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        
        synopsis = self.dm.data["world"].get("synopsis", "")
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังวิเคราะห์แผนการสร้าง..."))
                prompt = f"จากเรื่องย่อนี้: '{synopsis}' ช่วยแนะนำแนวเรื่อง (Genre), ธีมหลัก (Theme), และแนวทางการวางตัวละครที่เหมาะสม 3-5 แบบ"
                res_text = self.call_ai_simple(prompt, NexusPrompts.PLANNER_SYSTEM)
                
                def update_ui():
                    self.plan_display.config(state="normal")
                    self.plan_display.delete("1.0", tk.END)
                    self.plan_display.insert(tk.END, res_text)
                    self.plan_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="วิเคราะห์เสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def gen_wizard_chars(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        
        world_info = json.dumps(self.dm.data["world"], ensure_ascii=False)
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังเนรมิตตัวละคร..."))
                prompt = f"จากข้อมูลโลกและเรื่องย่อนี้: {world_info} ช่วยสร้างตัวละครหลัก 1 ตัว และตัวละครรอง 2 ตัว โดยระบุ ชื่อ, บทบาท, นิสัย และปูมหลังสั้นๆ"
                res_text = self.call_ai_json(prompt, NexusPrompts.JSON_ARCHITECT_SYSTEM)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: self.apply_chat_update(update)
                    self.wizard_char_display.config(state="normal")
                    self.wizard_char_display.delete("1.0", tk.END)
                    self.wizard_char_display.insert(tk.END, reply)
                    self.wizard_char_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="เนรมิตตัวละครเสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def gen_wizard_story(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        
        context = json.dumps({
            "world": self.dm.data["world"],
            "characters": self.dm.data["characters"]
        }, ensure_ascii=False)
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังร่างโครงเรื่อง..."))
                prompt = f"จากข้อมูลโลกและตัวละครนี้: {context} ช่วยร่างโครงเรื่อง (Plot) แบ่งเป็น 3 องก์ (Act 1, 2, 3) และแนะนำเหตุการณ์สำคัญ"
                
                res_text = self.call_ai_json(prompt, NexusPrompts.JSON_ARCHITECT_SYSTEM)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: self.apply_chat_update(update)
                    self.wizard_story_display.config(state="normal")
                    self.wizard_story_display.delete("1.0", tk.END)
                    self.wizard_story_display.insert(tk.END, reply)
                    self.wizard_story_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="ร่างโครงเรื่องเสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def call_ai_simple(self, prompt, system):
        # Helper for simple text completion
        provider = self.dm.config.get("ai_provider", "gemini")
        if provider == "gemini":
            client = genai.Client(api_key=self.dm.config["api_key"])
            resp = client.models.generate_content(
                model=self.dm.config.get("model", "gemini-2.0-flash"),
                contents=prompt,
                config={"system_instruction": system}
            )
            return resp.text
        else:
            client = Groq(api_key=self.dm.config["groq_api_key"])
            resp = client.chat.completions.create(
                model=self.dm.config.get("groq_model", "llama-3.3-70b-versatile"),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content

    def call_ai_json(self, prompt, system):
        # Helper for JSON completion
        provider = self.dm.config.get("ai_provider", "gemini")
        if provider == "gemini":
            client = genai.Client(api_key=self.dm.config["api_key"])
            resp = client.models.generate_content(
                model=self.dm.config.get("model", "gemini-2.0-flash"),
                contents=prompt,
                config={"system_instruction": system, "response_mime_type": "application/json"}
            )
            return resp.text
        else:
            client = Groq(api_key=self.dm.config["groq_api_key"])
            resp = client.chat.completions.create(
                model=self.dm.config.get("groq_model", "llama-3.3-70b-versatile"),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return resp.choices[0].message.content

    def build_chat_content(self):
        card = self.build_card(self.container, "บทสนทนาแห่งทวยเทพ (Divine Chat)")
        
        # Header with Clear button
        header_f = tk.Frame(card, bg=card["bg"])
        header_f.pack(fill="x", pady=(0, 10))
        tk.Label(header_f, text="คุยกับ Divine Architect เพื่อเนรมิตโลกของคุณ", font=("Segoe UI", 9), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        tk.Button(header_f, text="🗑️ ล้างการสนทนา", command=self.clear_chat, bg=self.colors["card"], fg=self.colors["danger"], bd=0, font=("Segoe UI", 8)).pack(side="right")

        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(card, bg=self.colors["input"], fg=self.colors["text"], 
                                                     font=("Segoe UI", 11), bd=0, padx=15, pady=15, state="disabled")
        self.chat_display.pack(fill="both", expand=True)
        
        # Quick Actions (Static)
        actions_f = tk.Frame(card, bg=card["bg"], pady=5)
        actions_f.pack(fill="x")
        
        quick_actions = [
            ("📜 สรุปพล็อต", "ช่วยสรุปพล็อตเรื่องปัจจุบันให้หน่อย"),
            ("👤 แนะนำตัวละคร", "ช่วยแนะนำตัวละครใหม่ที่เข้ากับโลกนี้หน่อย"),
            ("🌍 ขยายความโลก", "ช่วยขยายรายละเอียดภูมิศาสตร์หรือวัฒนธรรมของโลกนี้เพิ่มที"),
            ("💡 ไอเดียตอนต่อไป", "ช่วยคิดไอเดียสำหรับเหตุการณ์ถัดไปในเรื่องนี้หน่อย")
        ]
        
        for label, cmd in quick_actions:
            btn = tk.Button(actions_f, text=label, font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["accent"],
                            bd=0, padx=10, pady=5, cursor="hand2", command=lambda c=cmd: self.send_quick_chat(c))
            btn.pack(side="left", padx=2)

        # Dynamic Suggestions (From AI)
        self.suggestions_f = tk.Frame(card, bg=card["bg"], pady=5)
        self.suggestions_f.pack(fill="x")
        self.suggestion_label = tk.Label(self.suggestions_f, text="วิถีแห่งสวรรค์:", font=("Segoe UI", 8, "bold"), bg=card["bg"], fg=self.colors["muted"])
        # Hidden by default
        self.suggestion_label.pack_forget() 

        # Input area
        input_f = tk.Frame(card, bg=card["bg"], pady=15)
        input_f.pack(fill="x")
        
        self.chat_input = tk.Entry(input_f, bg=self.colors["input"], fg=self.colors["text"], 
                                  bd=0, font=("Segoe UI", 12), insertbackground="white")
        self.chat_input.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        self.chat_input.bind("<Return>", lambda e: self.send_divine_chat())
        
        tk.Button(input_f, text="ส่งสาส์น", command=self.send_divine_chat, 
                  bg=self.colors["accent"], fg="black", font=("Segoe UI", 10, "bold"), bd=0, padx=30).pack(side="left")
        
        self.refresh_chat_display()

    def send_quick_chat(self, text):
        self.chat_input.delete(0, tk.END)
        self.chat_input.insert(0, text)
        self.send_divine_chat()

    def clear_chat(self):
        if messagebox.askyesno("ยืนยัน", "คุณต้องการล้างประวัติการสนทนาทั้งหมดหรือไม่?"):
            self.dm.data["chat_history"] = []
            self.dm.save_all()
            self.refresh_chat_display()

    def refresh_chat_display(self):
        try:
            self.chat_display.config(state="normal")
            self.chat_display.delete("1.0", tk.END)
            
            history = self.dm.data.get("chat_history", [])
            if not history:
                self.chat_display.insert(tk.END, "Divine Architect: สวัสดีผู้สร้าง... ข้าพร้อมช่วยเจ้าเนรมิตโลกใบใหม่แล้ว เจ้าอยากเริ่มจากแนวไหน หรือมีไอเดียอะไรในใจบ้างหรือไม่?\n\n")
            
            for msg in history:
                role = "คุณ" if msg["role"] == "user" else "Divine Architect"
                self.chat_display.insert(tk.END, f"{role}: {msg['content']}\n\n")
            
            self.chat_display.see(tk.END)
            self.chat_display.config(state="disabled")
        except Exception as e:
            log_error(f"Error refreshing chat display: {e}")

    def _append_chat_message(self, role, content):
        try:
            self.chat_display.config(state="normal")
            display_role = "คุณ" if role == "user" else "Divine Architect"
            self.chat_display.insert(tk.END, f"{display_role}: {content}\n\n")
            self.chat_display.see(tk.END)
            self.chat_display.config(state="disabled")
        except Exception as e:
            log_error(f"Error appending chat message: {e}")

    def send_divine_chat(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy:
            return
            
        msg = self.chat_input.get().strip()
        if not msg: return
        
        provider = self.dm.config.get("ai_provider", "gemini")
        
        if provider == "gemini":
            if not HAS_GENAI or not self.dm.config.get("api_key"):
                messagebox.showwarning("AI", "กรุณาตั้งค่า Gemini API Key ก่อน")
                return
        else:
            if not HAS_GROQ or not self.dm.config.get("groq_api_key"):
                messagebox.showwarning("AI", "กรุณาตั้งค่า Groq API Key ก่อน")
                return
            
        self.is_ai_busy = True
        self.chat_input.delete(0, tk.END)
        self.dm.data.setdefault("chat_history", []).append({"role": "user", "content": msg})
        self._append_chat_message("user", msg)
        
        # Prepare data summary for AI context on MAIN thread (Thread Safety)
        try:
            data_summary = json.dumps({
                "world": self.dm.data.get("world"),
                "plot": self.dm.data.get("plot"),
                "characters_count": len(self.dm.data.get("characters", [])),
                "items_count": len(self.dm.data.get("items", []))
            }, ensure_ascii=False)
            
            # Include memory bank for smarter context
            memory_context = "\n".join(self.dm.data.get("memory_bank", [])[-15:])
            
            # Prepare history context on MAIN thread
            history_context = []
            for h in self.dm.data.get("chat_history", [])[-15:]:
                history_context.append({"role": h["role"], "content": h["content"]})
        except Exception as e:
            log_error(f"Error preparing chat context: {e}")
            self.is_ai_busy = False
            return
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text=f"AI ({provider}) กำลังประมวลผล..."))
                
                system_instr = NexusPrompts.get_architect_system(
                    self.dm.data.get("creation_phase", "synopsis"),
                    data_summary,
                    memory_context
                )
                
                if provider == "gemini":
                    client = genai.Client(api_key=self.dm.config["api_key"])
                    contents = []
                    for h in history_context:
                        contents.append({"role": h["role"], "parts": [{"text": h["content"]}]})
                    
                    resp = client.models.generate_content(
                        model=self.dm.config.get("model", "gemini-2.0-flash"),
                        contents=contents,
                        config={
                            "system_instruction": system_instr,
                            "response_mime_type": "application/json"
                        }
                    )
                    res_text = resp.text
                else:
                    client = Groq(api_key=self.dm.config["groq_api_key"])
                    messages = [{"role": "system", "content": system_instr + "\nIMPORTANT: Return only a JSON object."}]
                    for h in history_context:
                        messages.append({"role": h["role"] if h["role"] != "model" else "assistant", "content": h["content"]})
                    
                    resp = client.chat.completions.create(
                        model=self.dm.config.get("groq_model", "llama-3.3-70b-versatile"),
                        messages=messages,
                        response_format={"type": "json_object"}
                    )
                    res_text = resp.choices[0].message.content

                res_json = json.loads(res_text)
                reply = res_json.get("reply", "ข้ากำลังประมวลผล...")
                update = res_json.get("update")
                
                def finalize_chat():
                    try:
                        if update:
                            self.apply_chat_update(update)
                        
                        suggestions = res_json.get("suggestions", [])
                        if suggestions:
                            self.display_suggestions(suggestions)
                        else:
                            self.clear_suggestions()
                        
                        self.dm.data.setdefault("chat_history", []).append({"role": "model", "content": reply})
                        self._append_chat_message("model", reply)
                        self.status_label.config(text="ระบบพร้อมใช้งาน")
                    finally:
                        self.is_ai_busy = False
                
                self.root.after(0, finalize_chat)
                
            except Exception as e:
                self.is_ai_busy = False
                log_error(f"Divine Chat Error: {e}")
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    friendly_msg = f"⚠️ โควต้าการใช้งาน AI ({provider}) ของคุณเต็มแล้ว\n\nกรุณารอสักครู่ หรือสลับไปใช้ผู้ให้บริการอื่นในหน้าตั้งค่า"
                else:
                    friendly_msg = f"เกิดข้อผิดพลาดในการสื่อสารกับ AI ({provider}):\n{err_str}"
                
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", friendly_msg))
                self.root.after(0, lambda: self.status_label.config(text="เกิดข้อผิดพลาดในการสื่อสาร"))
                
        threading.Thread(target=task, daemon=True).start()

    def display_suggestions(self, suggestions):
        if not hasattr(self, 'suggestions_f') or not self.suggestions_f.winfo_exists():
            return
        self.clear_suggestions()
        if not suggestions: return
        
        self.suggestion_label.pack(side="left", padx=(0, 10))
        for s in suggestions:
            btn = tk.Button(self.suggestions_f, text=f"✨ {s}", font=("Segoe UI", 8), 
                            bg=self.colors["accent"], fg="black", bd=0, padx=8, pady=4, 
                            cursor="hand2", command=lambda text=s: self.send_quick_chat(text))
            btn.pack(side="left", padx=2)

    def clear_suggestions(self):
        if not hasattr(self, 'suggestions_f') or not self.suggestions_f.winfo_exists():
            return
        for widget in self.suggestions_f.winfo_children():
            if widget != self.suggestion_label:
                widget.destroy()
        self.suggestion_label.pack_forget()

    def apply_chat_update(self, update):
        try:
            self.dm.deep_update(self.dm.data, update)
            self.dm.save_all()
            
            # Refresh UI components if they are visible
            self.root.after(0, self.refresh_all_views)
            log_error("AI Updated Project Data via Chat")
        except Exception as e:
            log_error(f"Error applying chat update: {e}")

    def refresh_all_views(self):
        """Refreshes all UI tabs to reflect potential data changes from AI."""
        try:
            self.refresh_ch_list()
            self.refresh_char_list()
            self.refresh_item_list()
            self.refresh_memory_display()
            self.load_world_data()
            self.status_label.config(text="✨ ข้อมูลโปรเจกต์ได้รับการอัปเดตโดย AI")
        except: pass

    def refresh_memory_display(self):
        """Reloads memory bank text from data."""
        if hasattr(self, 'mem_text') and self.mem_text.winfo_exists():
            self.mem_text.delete("1.0", tk.END)
            mem = self.dm.data.get("memory_bank", [])
            self.mem_text.insert("1.0", "\n".join(mem))

    def build_card(self, parent, title):
        card = tk.Frame(parent, bg=self.colors["card"], padx=25, pady=25, 
                        highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(fill="both", expand=True, pady=10)
        header = tk.Frame(card, bg=self.colors["card"])
        header.pack(fill="x", pady=(0, 15))
        tk.Label(header, text=title.upper(), font=("Segoe UI", 10, "bold"), 
                 bg=self.colors["card"], fg=self.colors["accent"]).pack(side="left")
        return card

    def create_input(self, parent, label, height=1, ai_help=True, placeholder=""):
        f = tk.Frame(parent, bg=parent["bg"])
        f.pack(fill="x", pady=(8, 4))
        
        lbl_f = tk.Frame(f, bg=parent["bg"])
        lbl_f.pack(fill="x")
        tk.Label(lbl_f, text=label, font=("Segoe UI", 8, "bold"), bg=parent["bg"], fg=self.colors["muted"]).pack(side="left")
        
        if ai_help:
            btn_box = tk.Frame(lbl_f, bg=parent["bg"])
            btn_box.pack(side="right")
            tk.Button(btn_box, text="💡", font=("Segoe UI", 8), bg=parent["bg"], fg=self.colors["accent"], 
                      bd=0, cursor="hand2", command=lambda l=label: self.ai_brainstorm(l)).pack(side="left", padx=2)
            if height > 1:
                tk.Button(btn_box, text="🪄", font=("Segoe UI", 8), bg=parent["bg"], fg=self.colors["success"], 
                          bd=0, cursor="hand2", command=lambda l=label: self.ai_expand(l)).pack(side="left", padx=2)

        if height == 1:
            e = tk.Entry(f, bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"], bd=0, font=("Segoe UI", 11))
            e.pack(fill="x", ipady=8)
            if placeholder: 
                e.insert(0, placeholder)
                e.bind("<FocusIn>", lambda ev: self.clear_placeholder(e, placeholder))
            return e
        else:
            t = scrolledtext.ScrolledText(f, bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"], bd=0, font=("Segoe UI", 10), height=height)
            t.pack(fill="x")
            return t

    def clear_placeholder(self, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=self.colors["text"])

    def build_world_content(self):
        genre = self.dm.data["world"].get("genre", "ทั่วไป")
        g_config = self.dm.get_genre_config()
        card = self.build_card(self.container, "กำเนิดโลก (World Genesis)")
        
        # Genre Selector
        g_f = tk.Frame(card, bg=card["bg"])
        g_f.pack(fill="x", pady=(0, 10))
        tk.Label(g_f, text="เทมเพลตแนวเรื่อง", font=("Segoe UI", 8, "bold"), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        self.genre_var = tk.StringVar(value=genre)
        genres = ["ทั่วไป", "แฟนตาซีระดับสูง (High Fantasy)", "ดาร์กแฟนตาซี", "ไซเบอร์พังก์", "สเปซโอเปร่า", "หลังวันสิ้นโลก", "สตีมพังก์", "สยองขวัญ", "สืบสวนสอบสวน", "ความรัก / โรแมนติก", "ชีวิตประจำวัน / ฟีลกู๊ด"]
        g_menu = ttk.OptionMenu(g_f, self.genre_var, self.genre_var.get(), *genres, command=self.apply_genre_template)
        g_menu.pack(side="left", padx=10)

        self.world_entries = {
            "name": self.create_input(card, "ชื่อโลก / ชื่อเรื่อง", placeholder="เช่น เอลดอเรีย, นีโอ-โตเกียว"),
            "theme": self.create_input(card, "ธีมหลัก / บรรยากาศ", placeholder="เช่น ความหวัง vs ความสิ้นหวัง, เวทมนตร์ vs เทคโนโลยี"),
            "geography": self.create_input(card, "ภูมิศาสตร์และสภาพภูมิประเทศ", 2),
            "culture": self.create_input(card, "วัฒนธรรมและสังคม (ศาสนา, การเมือง)", 3),
            "sensory": self.create_input(card, "รายละเอียดประสาทสัมผัส (กลิ่น, เสียง)", 2),
            "rules": self.create_input(card, g_config["world_rules"], 3)
        }
        self.load_world_data()

    def build_char_content(self):
        g_config = self.dm.get_genre_config()
        main_f = tk.Frame(self.container, bg=self.colors["bg"])
        main_f.pack(fill="both", expand=True)
        
        left = tk.Frame(main_f, bg=self.colors["card"], width=280, padx=15, pady=15)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        
        tk.Label(left, text="ค้นหา", font=("Segoe UI", 7, "bold"), bg=left["bg"], fg=self.colors["muted"]).pack(anchor="w")
        self.char_search = tk.Entry(left, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 9))
        self.char_search.pack(fill="x", pady=(2, 10), ipady=5)
        self.char_search.bind("<KeyRelease>", self.filter_char_list)

        self.char_listbox = tk.Listbox(left, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 10), selectbackground=self.colors["accent"])
        self.char_listbox.pack(fill="both", expand=True)
        self.char_listbox.bind("<<ListboxSelect>>", self.load_char_details)
        
        btn_f = tk.Frame(left, bg=self.colors["card"], pady=10)
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="+ เพิ่ม", command=self.add_char, bg=self.colors["success"], fg="white", bd=0, pady=5).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_f, text="🗑️ ลบ", command=self.delete_char, bg=self.colors["danger"], fg="white", bd=0, pady=5).pack(side="left", padx=2)
        tk.Button(left, text="💬 สัมภาษณ์", command=self.char_interview, bg=self.colors["accent"], fg="black", bd=0, pady=8).pack(fill="x", pady=5)

        right = self.build_card(main_f, "โรงหล่อตัวละคร (Character Forge)")
        right.pack(side="left", fill="both", expand=True, padx=(20, 0))
        
        self.char_entries = {
            "name": self.create_input(right, "ชื่อตัวละคร"),
            "role": self.create_input(right, f"บทบาท ({g_config['char_role_hint']})"),
            "personality": self.create_input(right, "บุคลิกภาพ / นิสัย", 2),
            "appearance": self.create_input(right, "รูปลักษณ์ภายนอก", 2),
            "powers": self.create_input(right, g_config["char_powers"], 2),
            "relationships": self.create_input(right, "ความสัมพันธ์กับคนอื่น", 2),
            "backstory": self.create_input(right, "ปูมหลัง / ประวัติ", 3)
        }
        tk.Button(right, text="อัปเดตข้อมูลตัวละคร", command=self.update_char, 
                  bg=self.colors["accent"], fg="black", font=("Segoe UI", 9, "bold"), bd=0, pady=10).pack(fill="x", pady=15)
        self.refresh_char_list()

    def build_item_content(self):
        g_config = self.dm.get_genre_config()
        main_f = tk.Frame(self.container, bg=self.colors["bg"])
        main_f.pack(fill="both", expand=True)
        
        left = tk.Frame(main_f, bg=self.colors["card"], width=250, padx=15, pady=15)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        
        tk.Label(left, text=g_config["item_tab"], font=("Segoe UI", 9, "bold"), bg=left["bg"], fg=self.colors["accent"]).pack(pady=(0, 10))
        self.item_listbox = tk.Listbox(left, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 10), selectbackground=self.colors["accent"])
        self.item_listbox.pack(fill="both", expand=True)
        self.item_listbox.bind("<<ListboxSelect>>", self.load_item_details)
        
        btn_f = tk.Frame(left, bg=self.colors["card"], pady=10)
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="+ เพิ่ม", command=self.add_item, bg=self.colors["success"], fg="white", bd=0, pady=5).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_f, text="🗑️ ลบ", command=self.delete_item, bg=self.colors["danger"], fg="white", bd=0, pady=5).pack(side="left", padx=2)

        right = self.build_card(main_f, g_config["item_card"])
        right.pack(side="left", fill="both", expand=True, padx=(20, 0))
        
        self.item_entries = {
            "name": self.create_input(right, "ชื่อสิ่งของ"),
            "type": self.create_input(right, g_config["item_type"]),
            "description": self.create_input(right, "คำอธิบาย", 3),
            "abilities": self.create_input(right, g_config["item_abilities"], 3),
            "owner": self.create_input(right, "ผู้ครอบครองปัจจุบัน")
        }
        tk.Button(right, text="อัปเดตข้อมูล", command=self.update_item, 
                  bg=self.colors["accent"], fg="black", font=("Segoe UI", 9, "bold"), bd=0, pady=10).pack(fill="x", pady=15)
        self.refresh_item_list()

    def build_plot_content(self):
        card = self.build_card(self.container, "โครงเรื่องสวรรค์ (Divine Plot)")
        self.plot_entries = {
            "act1": self.create_input(card, "องก์ที่ 1: จุดเริ่มต้น", 3),
            "act2": self.create_input(card, "องก์ที่ 2: การเผชิญหน้า / ปมขัดแย้ง", 5),
            "act3": self.create_input(card, "องก์ที่ 3: บทสรุป", 3),
            "key_events": self.create_input(card, "เหตุการณ์สำคัญ (Timeline)", 3),
            "ending": self.create_input(card, "ตอนจบ", 2)
        }
        self.load_plot_data()

    def build_editor_content(self):
        main_f = tk.Frame(self.container, bg=self.colors["bg"])
        main_f.pack(fill="both", expand=True)
        
        left = tk.Frame(main_f, bg=self.colors["card"], width=200, padx=15, pady=15)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        
        self.ch_listbox = tk.Listbox(left, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 10), selectbackground=self.colors["accent"])
        self.ch_listbox.pack(fill="both", expand=True)
        self.ch_listbox.bind("<<ListboxSelect>>", self.load_ch_content)
        tk.Button(left, text="+ บทใหม่", command=self.add_ch, bg=self.colors["success"], fg="white", bd=0, pady=8).pack(fill="x", pady=5)
        tk.Button(left, text="🗑️ ลบบท", command=self.delete_ch, bg=self.colors["danger"], fg="white", bd=0, pady=8).pack(fill="x", pady=5)

        right = self.build_card(main_f, "แก้ไขเนื้อเรื่อง (Story Editor)")
        right.pack(side="left", fill="both", expand=True, padx=(20, 0))
        
        # Editor Toolbar
        toolbar = tk.Frame(right, bg=right["bg"])
        toolbar.pack(fill="x", pady=(0, 10))
        
        tk.Button(toolbar, text="🪄 เขียนต่อให้ที", command=self.ai_continue_story, bg=self.colors["success"], fg="white", bd=0, padx=15, pady=5, font=("Segoe UI", 8, "bold")).pack(side="left", padx=2)
        tk.Button(toolbar, text="✨ ปรับสำนวน", command=self.ai_improve_prose, bg=self.colors["accent"], fg="black", bd=0, padx=15, pady=5, font=("Segoe UI", 8, "bold")).pack(side="left", padx=2)
        tk.Button(toolbar, text="💾 บันทึกบทนี้", command=self.save_all_data, bg=self.colors["sidebar"], fg="white", bd=0, padx=15, pady=5, font=("Segoe UI", 8)).pack(side="right", padx=2)

        self.editor = scrolledtext.ScrolledText(right, bg=self.colors["input"], fg=self.colors["text"], 
                                               font=("Consolas", 12), bd=0, insertbackground="white", undo=True)
        self.editor.pack(fill="both", expand=True)
        self.refresh_ch_list()

    def ai_continue_story(self):
        if self.current_ch_idx is None:
            messagebox.showwarning("AI", "กรุณาเลือกบทที่ต้องการเขียนต่อก่อน")
            return
            
        current_text = self.editor.get("1.0", tk.END).strip()
        if not current_text:
            messagebox.showwarning("AI", "กรุณาเขียนเนื้อหาเริ่มต้นไว้สักนิดเพื่อให้ AI เขียนต่อได้")
            return
            
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังร่างเนื้อเรื่องต่อ..."))
                world = self.dm.data.get("world", {})
                style = self.dm.data.get("style", "มาตรฐาน")
                
                prompt = f"""เขียนเนื้อเรื่องนิยายต่อจากข้อความที่กำหนดให้ โดยใช้สไตล์การเขียนแบบ {style}
                ข้อมูลโลก: {world.get('name')} ({world.get('genre')})
                ธีม: {world.get('theme')}
                
                เนื้อเรื่องปัจจุบัน:
                {current_text}
                
                เขียนต่อจากจุดนี้ (ประมาณ 2-3 ย่อหน้า):"""
                
                res_text = self._get_ai_response(prompt)
                if res_text:
                    self.root.after(0, lambda: self.editor.insert(tk.END, f"\n\n{res_text}"))
                    self.root.after(0, lambda: self.status_label.config(text="AI เขียนต่อเสร็จสิ้น"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", str(e)))
                
        threading.Thread(target=task, daemon=True).start()

    def ai_improve_prose(self):
        try:
            sel_text = self.editor.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except tk.TclError:
            messagebox.showwarning("AI", "กรุณาคลุมดำข้อความที่ต้องการปรับสำนวน")
            return
            
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังปรับสำนวน..."))
                style = self.dm.data.get("style", "มาตรฐาน")
                
                prompt = f"ปรับปรุงสำนวนภาษาของข้อความต่อไปนี้ให้สละสลวยขึ้นในสไตล์ {style} โดยยังคงความหมายเดิมไว้:\n\n{sel_text}"
                
                res_text = self._get_ai_response(prompt)
                if res_text:
                    self.root.after(0, lambda: self._replace_selection(res_text))
                    self.root.after(0, lambda: self.status_label.config(text="ปรับสำนวนเสร็จสิ้น"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", str(e)))
                
        threading.Thread(target=task, daemon=True).start()

    def _replace_selection(self, new_text):
        try:
            self.editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.editor.insert(tk.INSERT, new_text)
        except: pass

    def build_memory_content(self):
        card = self.build_card(self.container, "ธนาคารความจำ (Memory Bank)")
        self.mem_text = scrolledtext.ScrolledText(card, bg=self.colors["input"], fg=self.colors["text"], bd=0, font=("Segoe UI", 11))
        self.mem_text.pack(fill="both", expand=True)
        self.mem_text.insert("1.0", "\n".join(self.dm.data["memory_bank"]))
        
        ai_f = tk.Frame(card, bg=card["bg"], pady=20)
        ai_f.pack(fill="x")
        self.ai_q = tk.Entry(ai_f, bg=self.colors["input"], fg=self.colors["text"], bd=0, font=("Segoe UI", 12), insertbackground="white")
        self.ai_q.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        tk.Button(ai_f, text="AI ช่วยจำ", command=self.run_ai_recall, bg=self.colors["accent"], fg="black", font=("Segoe UI", 10, "bold"), bd=0, padx=30).pack(side="left")

    def build_export_content(self):
        card = self.build_card(self.container, "AI และส่งออก (AI & Export)")
        
        # Writing Style
        s_f = tk.Frame(card, bg=card["bg"])
        s_f.pack(fill="x", pady=(0, 20))
        tk.Label(s_f, text="สไตล์การเขียน", font=("Segoe UI", 8, "bold"), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        styles = ["มาตรฐาน", "มหากาพย์/บทกวี", "ดาร์ก/สมจริง", "เน้นแอ็คชัน", "อารมณ์/ดราม่า", "มินิมอล"]
        s_menu = ttk.OptionMenu(s_f, self.style_var, self.style_var.get(), *styles)
        s_menu.pack(side="left", padx=10)

        exp_f = tk.Frame(card, bg=card["bg"])
        exp_f.pack(fill="x", pady=(0, 20))
        tk.Button(exp_f, text="📄 TXT", command=lambda: self.export_data("txt"), bg=self.colors["sidebar"], fg="white", bd=0, padx=15).pack(side="left", padx=5)
        tk.Button(exp_f, text="Ⓜ️ MD", command=lambda: self.export_data("md"), bg=self.colors["sidebar"], fg="white", bd=0, padx=15).pack(side="left", padx=5)
        tk.Button(exp_f, text="📦 JSON", command=lambda: self.export_data("json"), bg=self.colors["sidebar"], fg="white", bd=0, padx=15).pack(side="left", padx=5)

        self.prompt_out = scrolledtext.ScrolledText(card, bg=self.colors["input"], fg="#10b981", bd=0, font=("Consolas", 10), padx=15, pady=15)
        self.prompt_out.pack(fill="both", expand=True)
        tk.Button(card, text="🚀 สร้างและคัดลอก Master Prompt", command=self.gen_copy_prompt, 
                  bg=self.colors["accent"], fg="black", font=("Segoe UI", 11, "bold"), bd=0, pady=15).pack(fill="x", pady=20)

    def build_review_content(self):
        card = self.build_card(self.container, "ตรวจสอบคัมภีร์ (Divine Review)")
        
        info_f = tk.Frame(card, bg=card["bg"])
        info_f.pack(fill="x", pady=(0, 20))
        tk.Label(info_f, text="AI จะตรวจสอบคำผิด การจัดรูปแบบ และความสมเหตุสมผลของข้อมูลทั้งหมด", 
                 font=("Segoe UI", 10), bg=card["bg"], fg=self.colors["text"]).pack(side="left")
        
        tk.Button(card, text="🔍 เริ่มการตรวจสอบด้วย AI", command=self.run_divine_review, 
                  bg=self.colors["accent"], fg="black", font=("Segoe UI", 11, "bold"), bd=0, pady=12).pack(fill="x", pady=(0, 20))

        self.review_container = tk.Frame(card, bg=card["bg"])
        self.review_container.pack(fill="both", expand=True)
        
        # Initial message
        tk.Label(self.review_container, text="กดปุ่มด้านบนเพื่อเริ่มการตรวจสอบคัมภีร์ของคุณ", 
                 font=("Segoe UI", 10, "italic"), bg=card["bg"], fg=self.colors["muted"]).pack(pady=50)

    def build_settings_content(self):
        card = self.build_card(self.container, "ตั้งค่า (Settings)")
        
        # Theme & Provider
        top_f = tk.Frame(card, bg=card["bg"])
        top_f.pack(fill="x", pady=10)
        
        tk.Label(top_f, text="ธีมโปรแกรม", font=("Segoe UI", 8, "bold"), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        tk.Button(top_f, text="🌙 มืด", command=lambda: self.set_theme("dark"), bg="#1e293b", fg="white", bd=0, padx=10).pack(side="left", padx=10)
        tk.Button(top_f, text="☀️ สว่าง", command=lambda: self.set_theme("light"), bg="#f8fafc", fg="black", bd=0, padx=10).pack(side="left", padx=10)

        tk.Label(top_f, text="  |  ผู้ให้บริการ AI", font=("Segoe UI", 8, "bold"), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        self.provider_var = tk.StringVar(value=self.dm.config.get("ai_provider", "gemini"))
        p_menu = ttk.OptionMenu(top_f, self.provider_var, self.provider_var.get(), "gemini", "groq")
        p_menu.pack(side="left", padx=10)

        # Gemini Settings
        g_card = tk.LabelFrame(card, text=" Gemini Settings (แนะนำสำหรับงานละเอียด) ", bg=card["bg"], fg=self.colors["accent"], font=("Segoe UI", 9, "bold"), padx=15, pady=15)
        g_card.pack(fill="x", pady=10)
        
        m_f = tk.Frame(g_card, bg=card["bg"])
        m_f.pack(fill="x", pady=5)
        tk.Label(m_f, text="รุ่น AI", font=("Segoe UI", 8), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        self.model_var = tk.StringVar(value=self.dm.config.get("model", "gemini-2.0-flash"))
        models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        ttk.OptionMenu(m_f, self.model_var, self.model_var.get(), *models).pack(side="left", padx=10)

        self.api_entry = self.create_input(g_card, "Gemini API Key")
        self.api_entry.insert(0, self.dm.config.get("api_key", ""))

        # Groq Settings
        gr_card = tk.LabelFrame(card, text=" Groq Settings (ฟรีและเร็วมาก - แนะนำสำหรับใช้ยาวๆ) ", bg=card["bg"], fg=self.colors["success"], font=("Segoe UI", 9, "bold"), padx=15, pady=15)
        gr_card.pack(fill="x", pady=10)

        gm_f = tk.Frame(gr_card, bg=card["bg"])
        gm_f.pack(fill="x", pady=5)
        tk.Label(gm_f, text="รุ่น AI", font=("Segoe UI", 8), bg=card["bg"], fg=self.colors["muted"]).pack(side="left")
        self.groq_model_var = tk.StringVar(value=self.dm.config.get("groq_model", "llama-3.3-70b-versatile"))
        groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]
        ttk.OptionMenu(gm_f, self.groq_model_var, self.groq_model_var.get(), *groq_models).pack(side="left", padx=10)

        self.groq_api_entry = self.create_input(gr_card, "Groq API Key (สมัครฟรีที่ console.groq.com)")
        self.groq_api_entry.insert(0, self.dm.config.get("groq_api_key", ""))

        tk.Button(card, text="💾 บันทึกการตั้งค่าทั้งหมด", command=self.save_config, 
                  bg=self.colors["accent"], fg="black", font=("Segoe UI", 10, "bold"), bd=0, pady=15).pack(fill="x", pady=20)

    # ========== LOGIC ==========
    def _get_ai_response(self, prompt, system_instruction=None, json_mode=False):
        provider = self.dm.config.get("ai_provider", "gemini")
        try:
            if provider == "gemini":
                if not HAS_GENAI or not self.dm.config.get("api_key"):
                    raise Exception("Gemini API Key not set")
                client = genai.Client(api_key=self.dm.config["api_key"])
                config = {}
                if system_instruction: config["system_instruction"] = system_instruction
                if json_mode: config["response_mime_type"] = "application/json"
                
                resp = client.models.generate_content(
                    model=self.dm.config.get("model", "gemini-2.0-flash"),
                    contents=prompt,
                    config=config
                )
                return resp.text
            else:
                if not HAS_GROQ or not self.dm.config.get("groq_api_key"):
                    raise Exception("Groq API Key not set")
                client = Groq(api_key=self.dm.config["groq_api_key"])
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction + ("\nIMPORTANT: Return only a JSON object." if json_mode else "")})
                messages.append({"role": "user", "content": prompt})
                
                kwargs = {
                    "model": self.dm.config.get("groq_model", "llama-3.3-70b-versatile"),
                    "messages": messages
                }
                if json_mode: kwargs["response_format"] = {"type": "json_object"}
                
                resp = client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content
        except Exception as e:
            log_error(f"AI Error ({provider}): {e}")
            raise e

    def run_divine_review(self):
        provider = self.dm.config.get("ai_provider", "gemini")
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text=f"AI ({provider}) กำลังตรวจสอบข้อมูล..."))
                
                review_data = {
                    "world": self.dm.data.get("world", {}),
                    "characters": self.dm.data.get("characters", []),
                    "plot": self.dm.data.get("plot", {}),
                    "items": self.dm.data.get("items", [])
                }
                
                prompt = f"ตรวจสอบข้อมูลคัมภีร์นี้:\n{json.dumps(review_data, ensure_ascii=False, indent=2)}"
                res_text = self._get_ai_response(prompt, system_instruction=NexusPrompts.REVIEWER_SYSTEM, json_mode=True)
                suggestions = json.loads(res_text)
                self.root.after(0, lambda: self.display_review_results(suggestions))
                self.root.after(0, lambda: self.status_label.config(text="ตรวจสอบเสร็จสิ้น"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", str(e)))
                self.root.after(0, lambda: self.status_label.config(text="เกิดข้อผิดพลาดในการตรวจสอบ"))
                
        threading.Thread(target=task, daemon=True).start()

    def display_review_results(self, suggestions):
        try:
            if not hasattr(self, 'review_container') or not self.review_container.winfo_exists():
                return
            # Clear previous
            for widget in self.review_container.winfo_children(): widget.destroy()
            
            if not suggestions:
                tk.Label(self.review_container, text="✨ ไม่พบข้อผิดพลาดหรือสิ่งที่ต้องปรับปรุง! คัมภีร์ของคุณสมบูรณ์แบบแล้ว", 
                         font=("Segoe UI", 12), bg=self.colors["card"], fg=self.colors["success"]).pack(pady=50)
                return

            canvas = tk.Canvas(self.review_container, bg=self.colors["bg"], highlightthickness=0)
            scrollbar = ttk.Scrollbar(self.review_container, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=1000)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            for s in suggestions:
                s_card = tk.Frame(scrollable_frame, bg=self.colors["card"], padx=15, pady=15, highlightthickness=1, highlightbackground=self.colors["border"])
                s_card.pack(fill="x", pady=5, padx=10)
                
                header = tk.Frame(s_card, bg=self.colors["card"])
                header.pack(fill="x")
                
                type_colors = {"typo": self.colors["danger"], "format": self.colors["warning"], "suggestion": self.colors["accent"]}
                t_label = tk.Label(header, text=s.get("type", "suggestion").upper(), font=("Segoe UI", 8, "bold"), 
                                   bg=type_colors.get(s.get("type", "suggestion"), self.colors["muted"]), fg="white", padx=5)
                t_label.pack(side="left")
                
                tk.Label(header, text=f"  {s.get('label', s.get('path'))}", font=("Segoe UI", 10, "bold"), 
                         bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
                
                tk.Label(s_card, text=f"เหตุผล: {s.get('reason')}", font=("Segoe UI", 9, "italic"), 
                         bg=self.colors["card"], fg=self.colors["muted"], wraplength=900, justify="left").pack(anchor="w", pady=5)
                
                diff_f = tk.Frame(s_card, bg=self.colors["input"], padx=10, pady=10)
                diff_f.pack(fill="x", pady=5)
                
                tk.Label(diff_f, text=f"เดิม: {s.get('original')}", font=("Segoe UI", 9), bg=self.colors["input"], fg=self.colors["muted"], wraplength=800, justify="left").pack(anchor="w")
                tk.Label(diff_f, text=f"ใหม่: {s.get('suggested')}", font=("Segoe UI", 10, "bold"), bg=self.colors["input"], fg=self.colors["success"], wraplength=800, justify="left").pack(anchor="w", pady=(5, 0))
                
                tk.Button(s_card, text="✅ นำไปใช้", command=lambda data=s: self.apply_suggestion(data), 
                          bg=self.colors["success"], fg="white", bd=0, padx=20, pady=5).pack(side="right")
        except Exception as e:
            log_error(f"Error displaying suggestions: {e}")

    def apply_suggestion(self, s):
        path = s.get("path")
        val = s.get("suggested")
        if not path or val is None: return
        
        try:
            # Simple path parser for world.name or characters[0].backstory
            parts = path.split('.')
            target = self.dm.data
            
            for i, part in enumerate(parts[:-1]):
                if '[' in part:
                    name, idx_str = part.replace(']', '').split('[')
                    idx = int(idx_str)
                    target = target[name][idx]
                else:
                    target = target[part]
            
            last = parts[-1]
            if '[' in last:
                name, idx_str = last.replace(']', '').split('[')
                idx = int(idx_str)
                target[name][idx] = val
            else:
                target[last] = val
                
            self.dm.save_all()
            messagebox.showinfo("สำเร็จ", f"อัปเดตข้อมูล '{s.get('label')}' เรียบร้อยแล้ว")
            
            # Refresh current tab if needed
            if self.current_tab in ["world", "chars", "items", "plot"]:
                self.switch_tab(self.current_tab)
            else:
                # Just re-run review to show updated state (optional, maybe just remove the card)
                pass
        except Exception as e:
            log_error(f"Apply Suggestion Error: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถนำข้อเสนอแนะไปใช้ได้: {e}")

    def start_autosave(self):
        def loop():
            try:
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.save_all_data(silent=True)
                    now_str = datetime.now().strftime("%H:%M:%S")
                    if hasattr(self, 'status_label'):
                        self.status_label.config(text=f"บันทึกอัตโนมัติเมื่อ: {now_str}")
                    self.root.after(30000, loop)
            except Exception as e:
                log_error(f"Autosave Loop Error: {e}")
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.root.after(30000, loop)
        self.root.after(30000, loop)

    def set_theme(self, theme):
        self.dm.config["theme"] = theme
        self.dm.save_all()
        self.colors = self.themes[theme]
        self.root.configure(bg=self.colors["bg"])
        self.switch_tab(self.current_tab)

    def update_progress(self):
        try:
            if not hasattr(self, 'progress') or not hasattr(self, 'prog_label'): return
            total = 20
            filled = 0
            w = self.dm.data.get("world", {})
            for k in ["name", "theme", "geography", "culture", "sensory", "rules", "synopsis"]: 
                if w.get(k): filled += 1
            if self.dm.data.get("characters"): filled += 3
            if self.dm.data.get("items"): filled += 2
            p = self.dm.data.get("plot", {})
            for k in ["act1", "act2", "act3", "ending"]:
                if p.get(k): filled += 2
            
            perc = min(100, int((filled / total) * 100))
            self.progress["value"] = perc
            self.prog_label.config(text=f"{perc}%")
        except Exception as e:
            log_error(f"Update Progress Error: {e}")

    def apply_genre_template(self, genre):
        try:
            templates = self.dm.get_genre_templates()
            if genre in templates:
                for k, v in templates[genre].items():
                    if k in self.world_entries:
                        e = self.world_entries[k]
                        if isinstance(e, tk.Entry):
                            e.delete(0, tk.END)
                            e.insert(0, v)
                        else:
                            e.delete("1.0", tk.END)
                            e.insert("1.0", v)
            self.dm.data["world"]["genre"] = genre
            self.switch_tab("world") # Refresh UI to update labels
        except Exception as e:
            log_error(f"Error applying genre template: {e}")

    def ai_brainstorm(self, field):
        def task():
            try:
                genre = self.dm.data.get("world", {}).get("genre", "ทั่วไป")
                world_name = self.dm.data.get("world", {}).get("name", "ไม่ระบุ")
                prompt = f"ขอไอเดียสร้างสรรค์ 3 อย่างสำหรับ '{field}' ในเรื่องแนว {genre} ชื่อโลกปัจจุบัน: {world_name}"
                res_text = self._get_ai_response(prompt)
                if res_text:
                    self.root.after(0, lambda: messagebox.showinfo("AI ระดมสมอง", res_text))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("AI", "AI ไม่สามารถสร้างไอเดียได้ในขณะนี้"))
            except Exception as e: 
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", str(e)))
        threading.Thread(target=task, daemon=True).start()

    def ai_expand(self, field):
        try:
            widget = None
            for k, v in {**self.world_entries, **self.char_entries, **self.item_entries, **self.plot_entries}.items():
                if k.lower() in field.lower() or field.lower() in k.lower(): 
                    widget = v
                    break
            if not widget: return
            
            txt = widget.get("1.0", tk.END).strip() if not isinstance(widget, tk.Entry) else widget.get().strip()
            if not txt: return
            
            def task():
                try:
                    genre = self.dm.data.get("world", {}).get("genre", "ทั่วไป")
                    prompt = f"ขยายความรายละเอียดนี้ให้เป็นย่อหน้าที่สละสลวยสำหรับนิยาย: '{txt}' บริบท: {field} ในโลกแนว {genre}"
                    res_text = self._get_ai_response(prompt)
                    if res_text:
                        self.root.after(0, lambda: self._safe_insert_expand(widget, res_text))
                except Exception as e: 
                    self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", str(e)))
            threading.Thread(target=task, daemon=True).start()
        except Exception as e:
            log_error(f"Error initiating AI expand: {e}")

    def _safe_insert_expand(self, widget, text):
        try:
            if isinstance(widget, tk.Entry):
                widget.insert(tk.END, f" ({text})")
            else:
                widget.insert(tk.END, f"\n\n[ส่วนที่ AI ขยายความ]:\n{text}")
        except Exception as e:
            log_error(f"Error inserting AI expansion: {e}")

    def run_wizard(self):
        try:
            w = tk.Toplevel(self.root)
            w.title("🧙‍♂️ Divine World Builder Wizard")
            w.geometry("800x650")
            w.configure(bg=self.colors["bg"])
            w.transient(self.root)
            w.grab_set()

            container = tk.Frame(w, bg=self.colors["bg"], padx=40, pady=40)
            container.pack(fill="both", expand=True)

            self.wizard_data = {"genre": "", "setting": "", "systems": []}
            self.wizard_step = 1

            def clear_frame():
                for widget in container.winfo_children(): widget.destroy()

            def show_step1(): # Select Genre
                clear_frame()
                tk.Label(container, text="ขั้นที่ 1: เลือกแนวเรื่องหลักของคุณ", font=("Segoe UI", 18, "bold"), bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=(0, 20))
                
                genres = ["แฟนตาซี (Fantasy)", "ไซไฟ (Sci-Fi)", "โรแมนติก (Romance)", "สยองขวัญ (Horror)", "สืบสวน (Mystery)", "กำลังภายใน (Wuxia)", "ย้อนยุค (Historical)"]
                
                grid_f = tk.Frame(container, bg=self.colors["bg"])
                grid_f.pack(fill="both", expand=True)
                
                for i, g in enumerate(genres):
                    btn = tk.Button(grid_f, text=g, font=("Segoe UI", 11), bg=self.colors["card"], fg=self.colors["text"], 
                                    bd=1, relief="flat", highlightthickness=1, highlightbackground=self.colors["border"],
                                    padx=20, pady=15, cursor="hand2", command=lambda val=g: select_genre(val))
                    btn.grid(row=i//2, column=i%2, sticky="nsew", padx=10, pady=10)
                
                grid_f.grid_columnconfigure(0, weight=1)
                grid_f.grid_columnconfigure(1, weight=1)

            def select_genre(genre):
                self.wizard_data["genre"] = genre
                show_step2()

            def show_step2(): # Select Setting/Environment
                clear_frame()
                genre = self.wizard_data["genre"]
                tk.Label(container, text=f"ขั้นที่ 2: เลือกสภาพแวดล้อมสำหรับแนว {genre}", font=("Segoe UI", 18, "bold"), bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=(0, 20))
                
                settings_map = {
                    "แฟนตาซี (Fantasy)": ["ยุคกลางเวทมนตร์", "เกาะลอยฟ้า", "โลกใต้พิภพ", "ป่าศักดิ์สิทธิ์", "อาณาจักรที่ล่มสลาย"],
                    "ไซไฟ (Sci-Fi)": ["สถานีอวกาศ", "เมืองนีออนล้ำยุค", "ดาวเคราะห์ทะเลทราย", "โลกใต้น้ำ", "ยานอพยพ"],
                    "โรแมนติก (Romance)": ["เมืองใหญ่ที่วุ่นวาย", "ชนบทที่เงียบสงบ", "โรงเรียน/มหาวิทยาลัย", "ที่ทำงาน", "รีสอร์ทริมทะเล"],
                    "สยองขวัญ (Horror)": ["คฤหาสน์ร้าง", "โรงพยาบาลเก่า", "ป่าอาถรรพ์", "หมู่บ้านที่ถูกลืม", "ห้องปิดตาย"],
                    "สืบสวน (Mystery)": ["ลอนดอนยุควิกตอเรีย", "เมืองท่าที่เต็มไปด้วยอาชญากรรม", "เกาะส่วนตัว", "รถไฟข้ามทวีป"],
                    "กำลังภายใน (Wuxia)": ["สำนักบนยอดเขา", "โรงเตี๊ยมกลางป่า", "วังหลวง", "ยุทธภพที่กว้างใหญ่"],
                    "ย้อนยุค (Historical)": ["ยุคอยุธยา", "ยุคเรอเนซองส์", "ยุคอียิปต์โบราณ", "ยุคคาวบอยตะวันตก"]
                }
                
                settings = settings_map.get(genre, ["โลกปัจจุบัน", "โลกอนาคต", "โลกคู่ขนาน"])
                
                for s in settings:
                    btn = tk.Button(container, text=s, font=("Segoe UI", 11), bg=self.colors["card"], fg=self.colors["text"], 
                                    bd=0, pady=12, cursor="hand2", command=lambda val=s: select_setting(val))
                    btn.pack(fill="x", pady=5)
                
                tk.Button(container, text="⬅️ ย้อนกลับ", command=show_step1, bg=self.colors["bg"], fg=self.colors["muted"], bd=0).pack(pady=20)

            def select_setting(setting):
                self.wizard_data["setting"] = setting
                show_step3()

            def show_step3(): # AI Suggest Systems
                clear_frame()
                tk.Label(container, text="ขั้นที่ 3: เลือกระบบที่จำเป็นสำหรับโลกของคุณ", font=("Segoe UI", 18, "bold"), bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=(0, 10))
                tk.Label(container, text="AI กำลังวิเคราะห์และแนะนำระบบที่เหมาะสม...", font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["muted"]).pack()
                
                loading_lbl = tk.Label(container, text="⌛", font=("Segoe UI", 24), bg=self.colors["bg"], fg=self.colors["accent"])
                loading_lbl.pack(pady=40)

                def get_ai_suggestions():
                    try:
                        prompt = f"แนะนำ 'ระบบ' (World Systems) ที่จำเป็น 8-10 อย่างสำหรับนิยายแนว {self.wizard_data['genre']} ในสภาพแวดล้อม {self.wizard_data['setting']} เช่น ระบบเวทมนตร์, ระบบยศถาบรรดาศักดิ์, ระบบพลังงาน ฯลฯ ให้ตอบเป็น JSON array ของสตริงเท่านั้น"
                        res_text = self._get_ai_response(prompt, json_mode=True)
                        systems = json.loads(res_text)
                        if isinstance(systems, dict) and "systems" in systems: # Handle case where AI returns an object instead of array
                            systems = systems["systems"]
                        elif isinstance(systems, dict):
                            systems = list(systems.values())[0] if isinstance(list(systems.values())[0], list) else ["ระบบพื้นฐาน"]
                        
                        if not isinstance(systems, list): systems = ["ระบบพื้นฐาน", "ระบบสังคม"]
                        
                        self.root.after(0, lambda: display_systems(systems))
                    except Exception as e:
                        log_error(f"Wizard AI Error: {e}")
                        self.root.after(0, lambda: display_systems(["ระบบพื้นฐาน", "ระบบสังคม", "ระบบความสัมพันธ์"]))

                def display_systems(systems):
                    loading_lbl.destroy()
                    
                    scroll_f = tk.Frame(container, bg=self.colors["bg"])
                    scroll_f.pack(fill="both", expand=True)
                    
                    canvas = tk.Canvas(scroll_f, bg=self.colors["bg"], highlightthickness=0)
                    scrollbar = ttk.Scrollbar(scroll_f, orient="vertical", command=canvas.yview)
                    list_f = tk.Frame(canvas, bg=self.colors["bg"])
                    
                    canvas.create_window((0, 0), window=list_f, anchor="nw", width=700)
                    canvas.configure(yscrollcommand=scrollbar.set)
                    canvas.pack(side="left", fill="both", expand=True)
                    scrollbar.pack(side="right", fill="y")

                    vars = []
                    for s in systems:
                        var = tk.BooleanVar(value=True)
                        cb = tk.Checkbutton(list_f, text=s, variable=var, font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text"], 
                                            selectcolor=self.colors["card"], activebackground=self.colors["bg"])
                        cb.pack(anchor="w", pady=5)
                        vars.append((s, var))

                    def finalize():
                        selected = [s for s, v in vars if v.get()]
                        self.wizard_data["systems"] = selected
                        finish_wizard()

                    tk.Button(container, text="✨ สร้างโลกนิยายของคุณ", command=finalize, bg=self.colors["success"], fg="white", font=("Segoe UI", 12, "bold"), bd=0, pady=15).pack(fill="x", pady=20)

                threading.Thread(target=get_ai_suggestions, daemon=True).start()

            def finish_wizard():
                try:
                    # Populate data
                    self.dm.data["world"]["genre"] = self.wizard_data["genre"]
                    self.dm.data["world"]["geography"] = self.wizard_data["setting"]
                    self.dm.data["world"]["rules"] = "ระบบที่ใช้ในโลกนี้:\n- " + "\n- ".join(self.wizard_data["systems"])
                    
                    self.dm.save_all()
                    w.destroy()
                    self.switch_tab("world")
                    messagebox.showinfo("สำเร็จ", "เนรมิตโลกนิยายของคุณเรียบร้อยแล้ว! AI ได้จัดเตรียมโครงสร้างพื้นฐานให้คุณแล้ว")
                except Exception as e:
                    log_error(f"Finish wizard error: {e}")
                    w.destroy()

            show_step1()
        except Exception as e:
            log_error(f"Error starting wizard: {e}")

    def random_event(self):
        def task():
            try:
                genre = self.dm.data.get("world", {}).get("genre", "ทั่วไป")
                world_name = self.dm.data.get("world", {}).get("name", "ไม่ระบุ")
                prompt = f"สร้างเหตุการณ์สุ่มที่คาดไม่ถึงซึ่งอาจเกิดขึ้นในโลกแนว {genre} ชื่อ {world_name}"
                res_text = self._get_ai_response(prompt)
                if res_text:
                    self.root.after(0, lambda: messagebox.showinfo("🎲 เหตุการณ์สุ่ม", res_text))
            except Exception as e: 
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", str(e)))
        threading.Thread(target=task, daemon=True).start()

    def char_interview(self):
        try:
            sel = self.char_listbox.curselection()
            if not sel: 
                messagebox.showwarning("สัมภาษณ์", "กรุณาเลือกตัวละครก่อน!")
                return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["characters"]): return
            
            char = self.dm.data["characters"][idx]
            
            w = tk.Toplevel(self.root)
            w.title(f"💬 สัมภาษณ์ {char.get('name', 'Unknown')}")
            w.geometry("600x500")
            w.configure(bg=self.colors["bg"])
            
            chat = scrolledtext.ScrolledText(w, bg=self.colors["input"], fg="white", font=("Segoe UI", 10), bd=0)
            chat.pack(fill="both", expand=True, padx=10, pady=10)
            chat.insert(tk.END, f"AI: สวัสดี ข้าคือ {char.get('name', 'Unknown')} เจ้าอยากรู้เรื่องอะไรเกี่ยวกับอดีตหรือนิสัยของข้าล่ะ?\n\n")
            
            inp = tk.Entry(w, bg=self.colors["card"], fg="white", bd=0, font=("Segoe UI", 11))
            inp.pack(fill="x", padx=10, pady=(0, 10), ipady=8)
            
            def send():
                try:
                    q = inp.get().strip()
                    if not q: return
                    chat.insert(tk.END, f"คุณ: {q}\n")
                    inp.delete(0, tk.END)
                    
                    def task():
                        try:
                            prompt = f"สวมบทบาทเป็นตัวละครนี้: {char.get('name')} บทบาท: {char.get('role')} นิสัย: {char.get('personality')} ปูมหลัง: {char.get('backstory')} ตอบคำถามนี้: {q}"
                            res_text = self._get_ai_response(prompt)
                            if res_text:
                                self.root.after(0, lambda: chat.insert(tk.END, f"{char.get('name', 'Unknown').upper()}: {res_text}\n\n"))
                        except Exception as e:
                            self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด AI", str(e)))
                    threading.Thread(target=task, daemon=True).start()
                except Exception as e:
                    log_error(f"Char Interview Send Error: {e}")
            
            inp.bind("<Return>", lambda e: send())
        except Exception as e:
            log_error(f"Error starting char interview: {e}")

    def filter_char_list(self, event=None):
        q = self.char_search.get().lower()
        self.char_listbox.delete(0, tk.END)
        for c in self.dm.data["characters"]:
            if q in c["name"].lower(): self.char_listbox.insert(tk.END, f" {c['name']}")

    def export_data(self, fmt):
        try:
            path = filedialog.asksaveasfilename(defaultextension=f".{fmt}")
            if not path: return
            if fmt == "json":
                with open(path, "w", encoding="utf-8") as f: 
                    json.dump(self.dm.data, f, indent=2, ensure_ascii=False)
            else:
                world = self.dm.data.get("world", {})
                content = f"# คัมภีร์นิยาย: {world.get('name', 'ไม่ระบุ')}\n\n"
                content += f"แนวเรื่อง: {world.get('genre', 'ไม่ระบุ')}\n"
                content += f"ธีมหลัก: {world.get('theme', 'ไม่ระบุ')}\n\n"
                content += "## ตัวละคร\n"
                for c in self.dm.data.get("characters", []): 
                    content += f"- {c.get('name', 'Unknown')} ({c.get('role', 'N/A')}): {c.get('personality', 'N/A')}\n"
                content += "\n## โครงเรื่อง\n"
                plot = self.dm.data.get("plot", {})
                content += f"องก์ที่ 1: {plot.get('act1', 'N/A')}\n"
                with open(path, "w", encoding="utf-8") as f: f.write(content)
            messagebox.showinfo("ส่งออก", "ส่งออกโปรเจกต์เรียบร้อยแล้ว!")
        except Exception as e:
            log_error(f"Export error: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถส่งออกข้อมูลได้: {e}")

    def load_world_data(self):
        try:
            if not hasattr(self, 'world_entries'): return
            for k, e in self.world_entries.items():
                val = self.dm.data.get("world", {}).get(k, "")
                if isinstance(e, tk.Entry): 
                    e.delete(0, tk.END)
                    e.insert(0, val)
                else: 
                    e.delete("1.0", tk.END)
                    e.insert("1.0", val)
        except Exception as e:
            log_error(f"Error loading world data: {e}")

    def load_plot_data(self):
        try:
            for k, e in self.plot_entries.items():
                val = self.dm.data.get("plot", {}).get(k, "")
                e.delete("1.0", tk.END)
                e.insert("1.0", val)
        except Exception as e:
            log_error(f"Error loading plot data: {e}")

    def save_all_data(self, silent=False):
        try:
            if not hasattr(self, 'current_tab'): return
            
            if self.current_tab == "world" and hasattr(self, 'world_entries'):
                for k, e in self.world_entries.items():
                    try:
                        self.dm.data["world"][k] = e.get() if isinstance(e, tk.Entry) else e.get("1.0", tk.END).strip()
                    except: pass
            elif self.current_tab == "plot" and hasattr(self, 'plot_entries'):
                for k, e in self.plot_entries.items():
                    try:
                        self.dm.data["plot"][k] = e.get("1.0", tk.END).strip()
                    except: pass
            elif self.current_tab == "memory" and hasattr(self, 'mem_text'):
                try:
                    self.dm.data["memory_bank"] = self.mem_text.get("1.0", tk.END).strip().split("\n")
                except: pass
            elif self.current_tab == "editor" and self.current_ch_idx is not None and hasattr(self, 'editor'):
                if self.current_ch_idx < len(self.dm.data["chapters"]):
                    try:
                        self.dm.data["chapters"][self.current_ch_idx]["content"] = self.editor.get("1.0", tk.END)
                    except: pass
            
            if hasattr(self, 'style_var'):
                self.dm.data["style"] = self.style_var.get()
            
            self.dm.save_all()
            if not silent: messagebox.showinfo("สำเร็จ", "บันทึกโปรเจกต์เรียบร้อยแล้ว!")
            self.update_progress()
        except Exception as e:
            log_error(f"Error saving all data: {e}")
            if not silent: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถบันทึกข้อมูลได้: {e}")

    def save_config(self):
        try:
            self.dm.config["api_key"] = self.api_entry.get().strip()
            self.dm.config["model"] = self.model_var.get()
            self.dm.config["ai_provider"] = self.provider_var.get()
            self.dm.config["groq_api_key"] = self.groq_api_entry.get().strip()
            self.dm.config["groq_model"] = self.groq_model_var.get()
            self.dm.save_all()
            messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว!")
        except Exception as e:
            log_error(f"Error saving config: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถบันทึกการตั้งค่าได้: {e}")

    # Char Logic
    def add_char(self):
        try:
            self.dm.data["characters"].append({"name": "New Char", "role": "", "personality": "", "appearance": "", "powers": "", "relationships": "", "backstory": ""})
            self.refresh_char_list()
            self.char_listbox.selection_clear(0, tk.END)
            self.char_listbox.selection_set(tk.END)
            self.load_char_details(None)
        except Exception as e:
            log_error(f"Error adding character: {e}")

    def refresh_char_list(self):
        try:
            if not hasattr(self, 'char_listbox') or not self.char_listbox.winfo_exists():
                return
            self.char_listbox.delete(0, tk.END)
            for c in self.dm.data.get("characters", []): 
                self.char_listbox.insert(tk.END, f" {c.get('name', 'Unknown')}")
        except Exception as e:
            log_error(f"Error refreshing character list: {e}")

    def load_char_details(self, event):
        try:
            sel = self.char_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["characters"]): return
            
            char = self.dm.data["characters"][idx]
            for k, e in self.char_entries.items():
                val = char.get(k, "")
                if isinstance(e, tk.Entry): 
                    e.delete(0, tk.END)
                    e.insert(0, val)
                else: 
                    e.delete("1.0", tk.END)
                    e.insert("1.0", val)
        except Exception as e:
            log_error(f"Error loading character details: {e}")

    def update_char(self):
        try:
            sel = self.char_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["characters"]): return
            
            for k, e in self.char_entries.items():
                self.dm.data["characters"][idx][k] = e.get() if isinstance(e, tk.Entry) else e.get("1.0", tk.END).strip()
            self.refresh_char_list()
            self.char_listbox.selection_set(idx)
        except Exception as e:
            log_error(f"Error updating character: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถอัปเดตข้อมูลตัวละครได้: {e}")

    def delete_char(self):
        try:
            sel = self.char_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["characters"]): return
            
            name = self.dm.data["characters"][idx].get("name", "Unknown")
            if messagebox.askyesno("ยืนยัน", f"คุณต้องการลบตัวละคร '{name}' ใช่หรือไม่?"):
                self.dm.data["characters"].pop(idx)
                self.refresh_char_list()
                # Clear entries
                for e in self.char_entries.values():
                    if isinstance(e, tk.Entry): e.delete(0, tk.END)
                    else: e.delete("1.0", tk.END)
        except Exception as e:
            log_error(f"Error deleting character: {e}")

    # Item Logic
    def add_item(self):
        try:
            self.dm.data["items"].append({"name": "New Item", "type": "", "description": "", "abilities": "", "owner": ""})
            self.refresh_item_list()
            self.item_listbox.selection_clear(0, tk.END)
            self.item_listbox.selection_set(tk.END)
            self.load_item_details(None)
        except Exception as e:
            log_error(f"Error adding item: {e}")

    def refresh_item_list(self):
        try:
            if not hasattr(self, 'item_listbox') or not self.item_listbox.winfo_exists():
                return
            self.item_listbox.delete(0, tk.END)
            for i in self.dm.data.get("items", []): 
                self.item_listbox.insert(tk.END, f" {i.get('name', 'Unknown')}")
        except Exception as e:
            log_error(f"Error refreshing item list: {e}")

    def load_item_details(self, event):
        try:
            sel = self.item_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["items"]): return
            
            item = self.dm.data["items"][idx]
            for k, e in self.item_entries.items():
                val = item.get(k, "")
                if isinstance(e, tk.Entry): 
                    e.delete(0, tk.END)
                    e.insert(0, val)
                else: 
                    e.delete("1.0", tk.END)
                    e.insert("1.0", val)
        except Exception as e:
            log_error(f"Error loading item details: {e}")

    def update_item(self):
        try:
            sel = self.item_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["items"]): return
            
            for k, e in self.item_entries.items():
                self.dm.data["items"][idx][k] = e.get() if isinstance(e, tk.Entry) else e.get("1.0", tk.END).strip()
            self.refresh_item_list()
            self.item_listbox.selection_set(idx)
        except Exception as e:
            log_error(f"Error updating item: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถอัปเดตข้อมูลไอเทมได้: {e}")

    def delete_item(self):
        try:
            sel = self.item_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["items"]): return
            
            name = self.dm.data["items"][idx].get("name", "Unknown")
            if messagebox.askyesno("ยืนยัน", f"คุณต้องการลบไอเทม '{name}' ใช่หรือไม่?"):
                self.dm.data["items"].pop(idx)
                self.refresh_item_list()
                # Clear entries
                for e in self.item_entries.values():
                    if isinstance(e, tk.Entry): e.delete(0, tk.END)
                    else: e.delete("1.0", tk.END)
        except Exception as e:
            log_error(f"Error deleting item: {e}")

    # Chapter Logic
    def add_ch(self):
        try:
            count = len(self.dm.data.get("chapters", []))
            self.dm.data["chapters"].append({"title": f"บทที่ {count+1}", "content": ""})
            self.refresh_ch_list()
            self.ch_listbox.selection_clear(0, tk.END)
            self.ch_listbox.selection_set(tk.END)
            self.load_ch_content(None)
        except Exception as e:
            log_error(f"Error adding chapter: {e}")

    def refresh_ch_list(self):
        try:
            if not hasattr(self, 'ch_listbox') or not self.ch_listbox.winfo_exists():
                return
            self.ch_listbox.delete(0, tk.END)
            for i, ch in enumerate(self.dm.data.get("chapters", [])): 
                self.ch_listbox.insert(tk.END, f" Ch.{i+1}: {ch.get('title', 'Untitled')}")
        except Exception as e:
            log_error(f"Error refreshing chapter list: {e}")

    def delete_ch(self):
        try:
            sel = self.ch_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["chapters"]): return
            
            title = self.dm.data["chapters"][idx].get("title", "Untitled")
            if messagebox.askyesno("ยืนยัน", f"คุณต้องการลบบท '{title}' ใช่หรือไม่?"):
                self.dm.data["chapters"].pop(idx)
                self.current_ch_idx = None
                self.editor.delete("1.0", tk.END)
                self.refresh_ch_list()
        except Exception as e:
            log_error(f"Error deleting chapter: {e}")

    def load_ch_content(self, event):
        try:
            sel = self.ch_listbox.curselection()
            if not sel: return
            idx = sel[0]
            if idx < 0 or idx >= len(self.dm.data["chapters"]): return
            
            # Save current chapter before switching
            if self.current_ch_idx is not None and self.current_ch_idx < len(self.dm.data["chapters"]):
                self.dm.data["chapters"][self.current_ch_idx]["content"] = self.editor.get("1.0", tk.END)
            
            self.current_ch_idx = idx
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", self.dm.data["chapters"][self.current_ch_idx].get("content", ""))
        except Exception as e:
            log_error(f"Error loading chapter content: {e}")

    def gen_copy_prompt(self):
        try:
            w, p, chars, items = self.dm.data.get("world", {}), self.dm.data.get("plot", {}), self.dm.data.get("characters", []), self.dm.data.get("items", [])
            style = self.style_var.get() if hasattr(self, 'style_var') else "มาตรฐาน"
            prompt = f"สวมบทบาทเป็นนักเขียนนิยายมืออาชีพ สไตล์การเขียน: {style}\n\n🌍 โลก: {w.get('name', 'ไม่ระบุ')}\nแนวเรื่อง: {w.get('genre', 'ไม่ระบุ')}\nธีมหลัก: {w.get('theme', 'ไม่ระบุ')}\nวัฒนธรรม: {w.get('culture', 'ไม่ระบุ')}\nประสาทสัมผัส: {w.get('sensory', 'ไม่ระบุ')}\nกฎของโลก: {w.get('rules', 'ไม่ระบุ')}\n\n👤 ตัวละคร:\n"
            for c in chars: prompt += f"- {c.get('name', 'Unknown')} ({c.get('role', 'N/A')}): {c.get('personality', 'N/A')}. ความสัมพันธ์: {c.get('relationships', 'N/A')}\n"
            prompt += f"\n⚔️ ไอเทม:\n"
            for i in items: prompt += f"- {i.get('name', 'Unknown')} ({i.get('type', 'N/A')}): {i.get('abilities', 'N/A')}\n"
            prompt += f"\n📜 โครงเรื่อง:\nองก์ที่ 1: {p.get('act1', 'N/A')}\nองก์ที่ 2: {p.get('act2', 'N/A')}\nตอนจบ: {p.get('ending', 'N/A')}\n\nภารกิจ: เขียนบทถัดไปโดยอ้างอิงจากข้อมูลคัมภีร์นิยายนี้"
            self.prompt_out.delete("1.0", tk.END)
            self.prompt_out.insert("1.0", prompt)
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            messagebox.showinfo("คัดลอกแล้ว", "สร้าง Master Prompt และคัดลอกไปยังคลิปบอร์ดแล้ว!")
        except Exception as e:
            log_error(f"Error generating prompt: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถสร้าง Prompt ได้: {e}")

    def run_ai_recall(self):
        try:
            q = self.ai_q.get().strip()
            if not q: return
            threading.Thread(target=self._ai_task, args=(q,), daemon=True).start()
        except Exception as e:
            log_error(f"Error initiating AI recall: {e}")

    def _ai_task(self, q):
        try:
            mem_bank = self.dm.data.get('memory_bank', [])
            ctx = f"ข้อมูลบริบท: {' '.join(mem_bank)}\nชื่อโลก: {self.dm.data.get('world', {}).get('name', 'ไม่ระบุ')}\nคำถาม: {q}"
            res_text = self._get_ai_response(ctx)
            if res_text:
                self.root.after(0, lambda: messagebox.showinfo("Nexus AI ช่วยจำ", res_text))
        except Exception as e: 
            self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", str(e)))

if __name__ == "__main__":
    root = tk.Tk(); app = NexusGodWriter(root); root.mainloop()
