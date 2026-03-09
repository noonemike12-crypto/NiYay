from __future__ import annotations

import json
import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from nexus_god.ai.providers import Groq, HAS_GENAI, HAS_GROQ, genai
from nexus_god.core.data_manager import NexusDataManager
from nexus_god.core.logging_utils import configure_logging, install_thread_excepthook, log_error, log_debug, log_info


configure_logging()
install_thread_excepthook()

if not HAS_GENAI:
    log_error("Failed to import google-genai library")
if not HAS_GROQ:
    log_error("Failed to import groq library")

# ========== ULTIMATE UI COMPONENTS ==========
class NexusGodWriter:
    def __init__(self, root):
        log_debug("Initializing NexusGodWriter main window")
        self.root = root
        self.root.title("🌌 NEXUS GOD WRITER - ULTIMATE CREATOR EDITION (ภาษาไทย)")
        
        # Responsive window setup
        self.root.geometry("1500x950")
        self.root.minsize(1000, 600)  # Minimum window size
        self.root.state('zoomed' if sys.platform == 'win32' else 'normal')  # Maximize on Windows
        
        # Global Exception Handler for Tkinter
        self.root.report_callback_exception = self.handle_exception
        
        # Track window size for responsive adjustments
        self.window_width = 1500
        self.window_height = 950
        
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
            # ตรวจสอบว่าเป็นโปรเจกต์ใหม่หรือไม่
            if self.dm.data.get("is_new_project", True):
                log_info("New project detected, showing project setup")
                from nexus_god.ui.project_setup import show_project_setup
                if not show_project_setup(self.dm, parent=self.root):
                    log_info("Project setup cancelled by user")
                    # User cancelled or error, exit
                    sys.exit(0)
            
            self.build_layout()
            self.setup_responsive_handlers()
            self.start_autosave()
            log_info("Application started successfully")
        except Exception as e:
            log_error(f"Error building layout: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการสร้างหน้าจอ: {e}")

    def handle_exception(self, exc, val, tb):
        err_msg = "".join(traceback.format_exception(exc, val, tb))
        log_error(f"Unhandled Exception: {err_msg}")
        messagebox.showerror("เกิดข้อผิดพลาดที่ไม่คาดคิด", 
                             f"โปรแกรมพบข้อผิดพลาด แต่จะพยายามทำงานต่อไป:\n\n{str(val)}\n\nกรุณาตรวจสอบไฟล์ Log เพื่อดูรายละเอียด")

    def setup_responsive_handlers(self):
        """Setup window resize handlers for responsive design."""
        def on_resize(event=None):
            if event:
                self.window_width = event.width
                self.window_height = event.height
                self.update_responsive_layout()
        
        self.root.bind('<Configure>', on_resize)
        # Initial responsive update
        self.root.after(100, lambda: self.update_responsive_layout())
    
    def update_responsive_layout(self):
        """Update layout elements based on window size."""
        try:
            # Calculate responsive padding
            base_padx = 40
            base_pady = 30
            base_sidebar_width = 280
            
            # Scale padding based on window size (min 20, max 60)
            scale_factor = min(max(self.window_width / 1500, 0.5), 1.5)
            responsive_padx = max(20, int(base_padx * scale_factor))
            responsive_pady = max(20, int(base_pady * scale_factor))
            
            # Update container padding
            if hasattr(self, 'container'):
                self.container.config(padx=responsive_padx, pady=responsive_pady)
            
            # Update sidebar width for very small screens (optional: could hide)
            if hasattr(self, 'sidebar'):
                if self.window_width < 1200:
                    # Slightly narrower sidebar on small screens
                    self.sidebar.config(width=int(base_sidebar_width * 0.9))
                else:
                    self.sidebar.config(width=base_sidebar_width)
        except Exception as e:
            log_error(f"Error updating responsive layout: {e}")

    def build_card(self, parent, title):
        log_debug(f"Building card: {title}")
        card = tk.Frame(parent, bg=self.colors["card"], bd=1, relief="solid", highlightbackground=self.colors["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=10, pady=10)
        
        header = tk.Frame(card, bg=self.colors["sidebar"], pady=12, padx=20)
        header.pack(fill="x")
        tk.Label(header, text=title, font=("Segoe UI", 11, "bold"), bg=self.colors["sidebar"], fg=self.colors["accent"]).pack(side="left")
        
        content = tk.Frame(card, bg=self.colors["card"], padx=25, pady=20)
        content.pack(fill="both", expand=True)
        return content

    def create_input(self, parent, label, height=1):
        log_debug(f"Creating input field: {label}")
        f = tk.Frame(parent, bg=parent["bg"], pady=8)
        f.pack(fill="x")
        tk.Label(f, text=label, font=("Segoe UI", 9, "bold"), bg=parent["bg"], fg=self.colors["muted"]).pack(anchor="w")
        
        if height > 1:
            inp = scrolledtext.ScrolledText(f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=height, bd=0, wrap=tk.WORD)
        else:
            inp = tk.Entry(f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), bd=0, insertbackground="white")
            # Add subtle padding to entry
            inp.config(highlightbackground=self.colors["border"], highlightthickness=1)
            
        inp.pack(fill="x", pady=(5, 0))
        return inp

    def update_progress(self):
        log_debug("Updating creation progress")
        # Calculate progress based on data completeness
        score = 0
        total = 6
        
        if self.dm.data["world"].get("synopsis"): score += 1
        if self.dm.data["world"].get("name"): score += 1
        if self.dm.data["world"].get("genre"): score += 1
        if self.dm.data["characters"]: score += 1
        if self.dm.data["plot"].get("act1"): score += 1
        if self.dm.data["chapters"]: score += 1
        
        percent = int((score / total) * 100)
        self.progress["value"] = percent
        self.prog_label.config(text=f"{percent}%")
        log_debug(f"Progress updated to {percent}%")

    def save_all_data(self):
        log_info("Manual save triggered")
        self.dm.save_all()
        self.status_label.config(text=f"บันทึกข้อมูลแล้วเมื่อ {datetime.now().strftime('%H:%M:%S')}")
        messagebox.showinfo("สำเร็จ", "บันทึกข้อมูลโปรเจกต์ทั้งหมดเรียบร้อยแล้ว")

    def start_autosave(self):
        log_debug("Starting autosave loop")
        def loop():
            while True:
                threading.Event().wait(300) # 5 minutes
                log_info("Autosaving project data")
                self.dm.save_all()
                self.root.after(0, lambda: self.status_label.config(text=f"บันทึกอัตโนมัติเมื่อ {datetime.now().strftime('%H:%M:%S')}"))
        
        threading.Thread(target=loop, daemon=True).start()

    def random_event(self):
        log_info("Generating random event")
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังสุ่มเหตุการณ์..."))
                prompt = "ช่วยสุ่มเหตุการณ์ที่น่าสนใจหรือจุดหักมุม (Plot Twist) ที่อาจเกิดขึ้นในเรื่องนี้ โดยอิงจากข้อมูลโลกและตัวละครที่มีอยู่"
                context = json.dumps({"world": self.dm.data["world"], "characters": self.dm.data["characters"]}, ensure_ascii=False)
                
                res = self.call_ai_simple(f"Context: {context}\n\nRequest: {prompt}", "คุณคือเทพเจ้าแห่งการเล่าเรื่อง")
                
                def show():
                    messagebox.showinfo("🎲 เหตุการณ์สุ่มจากทวยเทพ", res)
                    self.is_ai_busy = False
                    self.status_label.config(text="สุ่มเหตุการณ์เสร็จสิ้น")
                
                self.root.after(0, show)
            except Exception as e:
                log_error(f"Error in random_event: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def apply_chat_update(self, update):
        log_debug(f"Applying chat update: {list(update.keys())}")
        # Update data based on AI JSON response
        if "world" in update:
            self.dm.data["world"].update(update["world"])
        if "characters" in update:
            # AI might return a list or dict of characters
            if isinstance(update["characters"], list):
                for char in update["characters"]:
                    name = char.get("name", "Unknown")
                    self.dm.data["characters"][name] = char
            else:
                self.dm.data["characters"].update(update["characters"])
        if "plot" in update:
            self.dm.data["plot"].update(update["plot"])
        
    def build_layout(self):
        log_debug("Building main layout")
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
        # Use grid for better responsive control
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        
        self.container = tk.Frame(self.content_area, bg=self.colors["bg"], padx=40, pady=30)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.switch_tab("wizard" if self.dm.data.get("creation_phase") != "story" else "chat")

    def manage_projects(self):
        log_debug("Opening project management window")
        w = tk.Toplevel(self.root)
        w.title("📂 จัดการโปรเจกต์")
        w.geometry("400x500")
        w.minsize(350, 400)  # Responsive minimum size
        w.configure(bg=self.colors["card"])
        # Make window responsive
        w.grid_rowconfigure(1, weight=1)
        w.grid_columnconfigure(0, weight=1)

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
                log_info(f"Switching project to: {name}")
                self.dm.switch_project(name)
                w.destroy()
                self.switch_tab("chat")
                messagebox.showinfo("สำเร็จ", f"สลับไปยังโปรเจกต์ '{name}' เรียบร้อยแล้ว")

        def on_new():
            log_debug("Creating new project from management window")
            new_name = filedialog.asksaveasfilename(initialdir="nexus_god_data", title="สร้างโปรเจกต์ใหม่", filetypes=[("JSON files", "*.json")])
            if new_name:
                name = Path(new_name).stem.replace("project_", "")
                log_info(f"New project created: {name}")
                self.dm.switch_project(name)
                w.destroy()
                self.switch_tab("chat")
                messagebox.showinfo("สำเร็จ", f"สร้างโปรเจกต์ '{name}' เรียบร้อยแล้ว")

        btn_f = tk.Frame(w, bg=self.colors["card"], pady=20)
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="สลับโปรเจกต์", command=on_switch, bg=self.colors["accent"], fg="black", bd=0, padx=20, pady=10).pack(side="left", expand=True, padx=5)
        tk.Button(btn_f, text="สร้างใหม่", command=on_new, bg=self.colors["success"], fg="white", bd=0, padx=20, pady=10).pack(side="left", expand=True, padx=5)

    def switch_tab(self, tab_key):
        log_debug(f"Switching to tab: {tab_key}")
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
        log_debug("Building wizard content")
        phase = self.dm.data.get("creation_phase", "synopsis")
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
        content_f.grid_rowconfigure(1, weight=1)
        content_f.grid_columnconfigure(0, weight=1)
        
        if phase == "synopsis":
            tk.Label(content_f, text="เริ่มต้นด้วยการเขียน 'เรื่องย่อ' ของนิยายที่คุณต้องการสร้าง", font=("Segoe UI", 12), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            
            text_frame = tk.Frame(content_f, bg=card["bg"])
            text_frame.pack(fill="both", expand=True, pady=10)
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
            
            self.synopsis_text = scrolledtext.ScrolledText(text_frame, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 11), height=10, bd=0, wrap=tk.WORD)
            self.synopsis_text.grid(row=0, column=0, sticky="nsew")
            self.synopsis_text.insert("1.0", self.dm.data["world"].get("synopsis", ""))
            
            tk.Button(content_f, text="บันทึกและไปต่อ →", command=self.save_synopsis_and_next, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=10, padx=30).pack(pady=20)
            
        elif phase == "planning":
            tk.Label(content_f, text="Divine Architect กำลังวิเคราะห์และแนะนำแนวทางสำหรับนิยายของคุณ...", font=("Segoe UI", 11), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            
            text_frame = tk.Frame(content_f, bg=card["bg"])
            text_frame.pack(fill="both", expand=True, pady=10)
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
            
            self.plan_display = scrolledtext.ScrolledText(text_frame, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=15, bd=0, state="disabled", wrap=tk.WORD)
            self.plan_display.grid(row=0, column=0, sticky="nsew")
            
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
            self.wizard_world_rules = self.create_input(content_f, "กฎสำคัญของโลกนี้", 4)
            
            self.wizard_world_name.insert(0, self.dm.data["world"].get("name", ""))
            self.wizard_world_genre.insert(0, self.dm.data["world"].get("genre", ""))
            self.wizard_world_rules.insert("1.0", self.dm.data["world"].get("rules", ""))

            btn_f = tk.Frame(content_f, bg=card["bg"])
            btn_f.pack(fill="x", pady=20)
            tk.Button(btn_f, text="← ย้อนกลับ", command=lambda: self.set_phase("planning"), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, pady=10, padx=20).pack(side="left")
            tk.Button(btn_f, text="บันทึกและไปสร้างตัวละคร →", command=self.save_wizard_world, bg=self.colors["success"], fg="white", bd=0, pady=10, padx=20).pack(side="right")

        elif phase == "characters":
            tk.Label(content_f, text="เนรมิตตัวละครหลักและรอง (AI จะช่วยสร้างพื้นฐานให้คุณปรับแต่ง)", font=("Segoe UI", 11), bg=card["bg"], fg=self.colors["text"]).pack(pady=10)
            
            text_frame = tk.Frame(content_f, bg=card["bg"])
            text_frame.pack(fill="both", expand=True, pady=10)
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
            
            self.wizard_char_display = scrolledtext.ScrolledText(text_frame, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=12, bd=0, state="disabled", wrap=tk.WORD)
            self.wizard_char_display.grid(row=0, column=0, sticky="nsew")
            
            btn_f = tk.Frame(content_f, bg=card["bg"])
            btn_f.pack(fill="x", pady=10)
            tk.Button(btn_f, text="← ย้อนกลับ", command=lambda: self.set_phase("world"), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, pady=10, padx=20).pack(side="left")
            tk.Button(btn_f, text="ให้ AI ช่วยสร้างตัวละคร 👤", command=self.gen_wizard_chars, bg=self.colors["accent"], fg="black", bd=0, pady=10, padx=20).pack(side="left", padx=10)
            tk.Button(btn_f, text="ไปสู่การสร้างเนื้อเรื่อง →", command=lambda: self.set_phase("story"), bg=self.colors["success"], fg="white", bd=0, pady=10, padx=20).pack(side="right")

        elif phase == "story":
            tk.Label(content_f, text="ยินดีด้วย! พื้นฐานโลกและตัวละครพร้อมแล้ว ตอนนี้คุณสามารถเริ่มสร้างเนื้อเรื่องได้", font=("Segoe UI", 12, "bold"), bg=card["bg"], fg=self.colors["success"]).pack(pady=10)
            
            text_frame = tk.Frame(content_f, bg=card["bg"])
            text_frame.pack(fill="both", expand=True, pady=10)
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
            
            self.wizard_story_display = scrolledtext.ScrolledText(text_frame, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), height=12, bd=0, state="disabled", wrap=tk.WORD)
            self.wizard_story_display.grid(row=0, column=0, sticky="nsew")

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
        log_info(f"Setting creation phase to: {phase}")
        self.dm.data["creation_phase"] = phase
        self.dm.save_all()
        self.switch_tab("wizard")

    def save_synopsis_and_next(self):
        log_debug("Saving synopsis and moving to planning phase")
        syn = self.synopsis_text.get("1.0", tk.END).strip()
        if not syn:
            messagebox.showwarning("คำเตือน", "กรุณาใส่เรื่องย่อก่อนไปต่อ")
            return
        self.dm.data["world"]["synopsis"] = syn
        self.set_phase("planning")

    def save_wizard_world(self):
        log_debug("Saving wizard world data")
        self.dm.data["world"]["name"] = self.wizard_world_name.get()
        self.dm.data["world"]["genre"] = self.wizard_world_genre.get()
        self.dm.data["world"]["rules"] = self.wizard_world_rules.get("1.0", tk.END).strip()
        self.dm.save_all()
        self.set_phase("characters")

    def get_divine_package(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("Requesting Divine Package from AI")
        
        synopsis = self.dm.data["world"].get("synopsis", "")
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังเนรมิตวิถีแห่งสวรรค์..."))
                prompt = f"จากเรื่องย่อนี้: '{synopsis}' ช่วยออกแบบ Genre, Theme, และ World Rules ที่สมบูรณ์แบบที่สุดเพียงแบบเดียว"
                
                system = "คุณคือ Divine Architect ให้ตอบกลับเป็น JSON Object ที่มี 'reply' (คำอธิบายเหตุผล) และ 'update' (ข้อมูล world ในฟิลด์ world: {genre, theme, rules})"
                res_text = self.call_ai_json(prompt, system)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: 
                        log_info("Applying Divine Package update")
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
                log_error(f"Error in get_divine_package: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def get_ai_planning(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("Requesting AI planning suggestions")
        
        synopsis = self.dm.data["world"].get("synopsis", "")
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังวิเคราะห์แผนการสร้าง..."))
                prompt = f"จากเรื่องย่อนี้: '{synopsis}' ช่วยแนะนำแนวเรื่อง (Genre), ธีมหลัก (Theme), และแนวทางการวางตัวละครที่เหมาะสม 3-5 แบบ"
                
                # We use a simplified version of chat logic here
                res_text = self.call_ai_simple(prompt, "คุณคือผู้เชี่ยวชาญด้านการวางโครงสร้างนิยาย ให้คำแนะนำที่สร้างสรรค์และเป็นระบบ")
                
                def update_ui():
                    self.plan_display.config(state="normal")
                    self.plan_display.delete("1.0", tk.END)
                    self.plan_display.insert(tk.END, res_text)
                    self.plan_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="วิเคราะห์เสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                log_error(f"Error in get_ai_planning: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def gen_wizard_chars(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("Requesting AI to generate wizard characters")
        
        world_info = json.dumps(self.dm.data["world"], ensure_ascii=False)
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังเนรมิตตัวละคร..."))
                prompt = f"จากข้อมูลโลกและเรื่องย่อนี้: {world_info} ช่วยสร้างตัวละครหลัก 1 ตัว และตัวละครรอง 2 ตัว โดยระบุ ชื่อ, บทบาท, นิสัย และปูมหลังสั้นๆ"
                
                # Ask AI to return JSON for character updates
                system = "คุณคือ Divine Architect ให้ตอบกลับเป็น JSON Object ที่มี 'reply' (คำบรรยาย) และ 'update' (ข้อมูลตัวละครในฟิลด์ characters)"
                res_text = self.call_ai_json(prompt, system)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: 
                        log_info("Applying wizard characters update")
                        self.apply_chat_update(update)
                    self.wizard_char_display.config(state="normal")
                    self.wizard_char_display.delete("1.0", tk.END)
                    self.wizard_char_display.insert(tk.END, reply)
                    self.wizard_char_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="เนรมิตตัวละครเสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                log_error(f"Error in gen_wizard_chars: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def gen_wizard_story(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("Requesting AI to generate wizard story plot")
        
        context = json.dumps({
            "world": self.dm.data["world"],
            "characters": self.dm.data["characters"]
        }, ensure_ascii=False)
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังร่างโครงเรื่อง..."))
                prompt = f"จากข้อมูลโลกและตัวละครนี้: {context} ช่วยร่างโครงเรื่อง (Plot) แบ่งเป็น 3 องก์ (Act 1, 2, 3) และแนะนำเหตุการณ์สำคัญ"
                
                system = "คุณคือ Divine Architect ให้ตอบกลับเป็น JSON Object ที่มี 'reply' (คำบรรยาย) และ 'update' (ข้อมูล plot ในฟิลด์ plot: {act1, act2, act3, key_events})"
                res_text = self.call_ai_json(prompt, system)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: 
                        log_info("Applying wizard story plot update")
                        self.apply_chat_update(update)
                    self.wizard_story_display.config(state="normal")
                    self.wizard_story_display.delete("1.0", tk.END)
                    self.wizard_story_display.insert(tk.END, reply)
                    self.wizard_story_display.config(state="disabled")
                    self.is_ai_busy = False
                    self.status_label.config(text="ร่างโครงเรื่องเสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                log_error(f"Error in gen_wizard_story: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def call_ai_simple(self, prompt, system):
        log_debug(f"Calling AI simple: {prompt[:50]}...")
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

    def build_chat_content(self):
        log_debug("Building chat content")
        card = self.build_card(self.container, "สนทนาทวยเทพ (Divine Chat)")
        
        self.chat_display = scrolledtext.ScrolledText(card, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), bd=0, wrap=tk.WORD)
        self.chat_display.pack(fill="both", expand=True, pady=(0, 15))
        self.chat_display.config(state="disabled")
        
        input_f = tk.Frame(card, bg=card["bg"])
        input_f.pack(fill="x")
        
        self.chat_input = tk.Entry(input_f, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 11), bd=0)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=5)
        self.chat_input.bind("<Return>", lambda e: self.send_chat())
        
        tk.Button(input_f, text="ส่งสาส์น ⚡", command=self.send_chat, bg=self.colors["accent"], fg="black", font=("Segoe UI", 9, "bold"), bd=0, padx=20, pady=8).pack(side="right")

    def build_world_content(self):
        log_debug("Building world content")
        card = self.build_card(self.container, "กำเนิดโลก (World Genesis)")
        
        self.world_name = self.create_input(card, "ชื่อโลก / ชื่อเรื่อง")
        self.world_genre = self.create_input(card, "แนวเรื่อง (Genre)")
        self.world_theme = self.create_input(card, "ธีมหลัก (Theme)")
        self.world_rules = self.create_input(card, "กฎของโลก / ระบบพลัง", 6)
        self.world_desc = self.create_input(card, "รายละเอียดเพิ่มเติม", 8)
        
        # Load data
        self.world_name.insert(0, self.dm.data["world"].get("name", ""))
        self.world_genre.insert(0, self.dm.data["world"].get("genre", ""))
        self.world_theme.insert(0, self.dm.data["world"].get("theme", ""))
        self.world_rules.insert("1.0", self.dm.data["world"].get("rules", ""))
        self.world_desc.insert("1.0", self.dm.data["world"].get("description", ""))
        
        tk.Button(card, text="บันทึกข้อมูลโลก 💾", command=self.save_world_data, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=12).pack(fill="x", pady=20)

    def build_char_content(self):
        log_debug("Building character content")
        card = self.build_card(self.container, "โรงหล่อตัวละคร (Character Foundry)")
        
        # List and Form Split
        split = tk.Frame(card, bg=card["bg"])
        split.pack(fill="both", expand=True)
        
        # Left: List
        left = tk.Frame(split, bg=card["bg"], width=250)
        left.pack(side="left", fill="y", padx=(0, 20))
        left.pack_propagate(False)
        
        tk.Label(left, text="รายชื่อตัวละคร", font=("Segoe UI", 9, "bold"), bg=left["bg"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 5))
        self.char_listbox = tk.Listbox(left, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 10))
        self.char_listbox.pack(fill="both", expand=True)
        self.char_listbox.bind("<<ListboxSelect>>", self.on_char_select)
        
        btn_f = tk.Frame(left, bg=left["bg"], pady=10)
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="+ เพิ่มตัวละคร", command=self.add_character, bg=self.colors["accent"], fg="black", bd=0, pady=5).pack(fill="x", pady=2)
        tk.Button(btn_f, text="- ลบตัวละคร", command=self.delete_character, bg=self.colors["danger"], fg="white", bd=0, pady=5).pack(fill="x", pady=2)
        tk.Button(btn_f, text="⚙️ จัดการฟิลด์", command=self.manage_custom_fields, bg=self.colors["muted"], fg="white", bd=0, pady=5).pack(fill="x", pady=2)

        # Right: Form
        self.char_form = tk.Frame(split, bg=card["bg"])
        self.char_form.pack(side="left", fill="both", expand=True)
        
        self.refresh_char_list()

    def build_item_content(self):
        log_debug("Building item content")
        card = self.build_card(self.container, "คลังไอเทมและสิ่งประดิษฐ์ (Divine Armory)")
        tk.Label(card, text="ระบบคลังไอเทมกำลังอยู่ในการพัฒนา...", font=("Segoe UI", 12), bg=card["bg"], fg=self.colors["muted"]).pack(pady=50)

    def build_plot_content(self):
        log_debug("Building plot content")
        card = self.build_card(self.container, "โครงเรื่องสวรรค์ (Divine Plot)")
        
        self.plot_act1 = self.create_input(card, "องก์ที่ 1: การเริ่มต้น (Act 1)", 5)
        self.plot_act2 = self.create_input(card, "องก์ที่ 2: การเผชิญหน้า (Act 2)", 5)
        self.plot_act3 = self.create_input(card, "องก์ที่ 3: บทสรุป (Act 3)", 5)
        
        self.plot_act1.insert("1.0", self.dm.data["plot"].get("act1", ""))
        self.plot_act2.insert("1.0", self.dm.data["plot"].get("act2", ""))
        self.plot_act3.insert("1.0", self.dm.data["plot"].get("act3", ""))
        
        tk.Button(card, text="บันทึกโครงเรื่อง 💾", command=self.save_plot_data, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=12).pack(fill="x", pady=20)

    def build_editor_content(self):
        log_debug("Building editor content with AI tools")
        card = self.build_card(self.container, "แก้ไขเนื้อเรื่อง (Divine Editor)")
        
        # Toolbar for AI Actions
        toolbar = tk.Frame(card, bg=self.colors["sidebar"], pady=5, padx=10)
        toolbar.pack(fill="x", pady=(0, 10))
        
        tk.Button(toolbar, text="✨ เขียนต่อ (Continue)", command=self.ai_continue_writing, bg=self.colors["accent"], fg="black", font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=5).pack(side="left", padx=2)
        tk.Button(toolbar, text="🪄 ขัดเกลา (Improve)", command=self.ai_improve_text, bg=self.colors["success"], fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=5).pack(side="left", padx=2)
        tk.Button(toolbar, text="📜 แนะนำฉากต่อไป", command=self.ai_suggest_scene, bg=self.colors["warning"], fg="black", font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=5).pack(side="left", padx=2)
        tk.Button(toolbar, text="💾 บันทึกเนื้อหา", command=self.save_current_chapter, bg=self.colors["muted"], fg="white", font=("Segoe UI", 8), bd=0, padx=10, pady=5).pack(side="right", padx=2)

        # Chapter Selector
        top_f = tk.Frame(card, bg=card["bg"])
        top_f.pack(fill="x", pady=(0, 10))
        
        tk.Label(top_f, text="ตอนที่:", font=("Segoe UI", 9, "bold"), bg=top_f["bg"], fg=self.colors["muted"]).pack(side="left")
        self.chapter_selector = ttk.Combobox(top_f, values=list(self.dm.data["chapters"].keys()) or ["ตอนที่ 1"])
        self.chapter_selector.pack(side="left", padx=10)
        self.chapter_selector.bind("<<ComboboxSelected>>", self.on_chapter_change)
        
        tk.Button(top_f, text="+ เพิ่มตอน", command=self.add_chapter, bg=self.colors["accent"], fg="black", bd=0, padx=10).pack(side="left")
        
        # Editor
        self.editor_text = scrolledtext.ScrolledText(card, bg=self.colors["input"], fg=self.colors["text"], font=("Cordia New", 16), bd=0, wrap=tk.WORD, undo=True)
        self.editor_text.pack(fill="both", expand=True, pady=10)
        
        # Load first chapter if exists
        if self.dm.data["chapters"]:
            first_key = list(self.dm.data["chapters"].keys())[0]
            self.chapter_selector.set(first_key)
            self.editor_text.insert("1.0", self.dm.data["chapters"][first_key])
        
        # Status bar for editor
        self.editor_status = tk.Label(card, text="พร้อมใช้งาน", font=("Segoe UI", 8), bg=card["bg"], fg=self.colors["muted"])
        self.editor_status.pack(anchor="e")

    def build_memory_content(self):
        log_debug("Building memory content")
        card = self.build_card(self.container, "ธนาคารความจำ (Memory Bank)")
        
        tk.Label(card, text="เก็บรวบรวมข้อมูล Lore, สถานที่, และความลับของโลก เพื่อให้ AI จดจำได้แม่นยำ", font=("Segoe UI", 10), bg=card["bg"], fg=self.colors["muted"]).pack(pady=(0, 15))
        
        # Split List and Form
        split = tk.Frame(card, bg=card["bg"])
        split.pack(fill="both", expand=True)
        
        # Left: Memory List
        left = tk.Frame(split, bg=card["bg"], width=250)
        left.pack(side="left", fill="y", padx=(0, 20))
        left.pack_propagate(False)
        
        self.memory_listbox = tk.Listbox(left, bg=self.colors["input"], fg="white", bd=0, font=("Segoe UI", 10))
        self.memory_listbox.pack(fill="both", expand=True)
        self.memory_listbox.bind("<<ListboxSelect>>", self.on_memory_select)
        
        btn_f = tk.Frame(left, bg=left["bg"], pady=10)
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="+ เพิ่มความจำ", command=self.add_memory, bg=self.colors["accent"], fg="black", bd=0, pady=5).pack(fill="x", pady=2)
        tk.Button(btn_f, text="- ลบความจำ", command=self.delete_memory, bg=self.colors["danger"], fg="white", bd=0, pady=5).pack(fill="x", pady=2)

        # Right: Memory Form
        self.memory_form = tk.Frame(split, bg=card["bg"])
        self.memory_form.pack(side="left", fill="both", expand=True)
        
        self.refresh_memory_list()

    def build_review_content(self):
        log_debug("Building review content")
        card = self.build_card(self.container, "ตรวจสอบคัมภีร์ (Divine Review)")
        tk.Label(card, text="ระบบตรวจสอบเนื้อเรื่องกำลังอยู่ในการพัฒนา...", font=("Segoe UI", 12), bg=card["bg"], fg=self.colors["muted"]).pack(pady=50)

    def build_export_content(self):
        log_debug("Building export content")
        card = self.build_card(self.container, "AI และส่งออก (Export & AI)")
        tk.Label(card, text="ระบบส่งออกกำลังอยู่ในการพัฒนา...", font=("Segoe UI", 12), bg=card["bg"], fg=self.colors["muted"]).pack(pady=50)

    def build_settings_content(self):
        log_debug("Building settings content")
        card = self.build_card(self.container, "ตั้งค่า (Settings)")
        
        self.set_theme = self.create_input(card, "ธีม (dark/light)")
        self.set_theme.insert(0, self.dm.config.get("theme", "dark"))
        
        self.set_api = self.create_input(card, "Gemini API Key")
        self.set_api.insert(0, self.dm.config.get("api_key", ""))
        
        tk.Button(card, text="บันทึกการตั้งค่า ⚙️", command=self.save_settings, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=12).pack(fill="x", pady=20)

    def send_chat(self):
        msg = self.chat_input.get().strip()
        if not msg: return
        
        log_info(f"User sent chat message: {msg[:50]}...")
        self.chat_input.delete(0, tk.END)
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"คุณ: {msg}\n\n", "user")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
        
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        
        def task():
            try:
                self.root.after(0, lambda: self.status_label.config(text="AI กำลังสื่อสาร..."))
                
                # Build context
                context = f"World: {json.dumps(self.dm.data['world'], ensure_ascii=False)}\n"
                context += f"Characters: {json.dumps(list(self.dm.data['characters'].keys()), ensure_ascii=False)}\n"
                
                system = "คุณคือ Divine Architect ผู้ช่วยสร้างสรรค์นิยายที่ชาญฉลาด ให้คำแนะนำและช่วยปรับปรุงข้อมูลในโปรเจกต์"
                system += "\nหากมีการอัปเดตข้อมูล ให้ตอบกลับเป็น JSON ที่มี 'reply' และ 'update'"
                
                res_text = self.call_ai_json(f"Context: {context}\n\nUser: {msg}", system)
                res_json = json.loads(res_text)
                
                reply = res_json.get("reply", "")
                update = res_json.get("update", {})
                
                def update_ui():
                    if update: self.apply_chat_update(update)
                    self.chat_display.config(state="normal")
                    self.chat_display.insert(tk.END, f"Divine: {reply}\n\n", "ai")
                    self.chat_display.config(state="disabled")
                    self.chat_display.see(tk.END)
                    self.is_ai_busy = False
                    self.status_label.config(text="สื่อสารเสร็จสิ้น")
                
                self.root.after(0, update_ui)
            except Exception as e:
                log_error(f"Error in send_chat: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def save_world_data(self):
        log_info("Saving world data from form")
        self.dm.data["world"]["name"] = self.world_name.get()
        self.dm.data["world"]["genre"] = self.world_genre.get()
        self.dm.data["world"]["theme"] = self.world_theme.get()
        self.dm.data["world"]["rules"] = self.world_rules.get("1.0", tk.END).strip()
        self.dm.data["world"]["description"] = self.world_desc.get("1.0", tk.END).strip()
        self.dm.save_all()
        messagebox.showinfo("สำเร็จ", "บันทึกข้อมูลโลกเรียบร้อยแล้ว")

    def refresh_char_list(self):
        log_debug("Refreshing character listbox")
        self.char_listbox.delete(0, tk.END)
        for name in self.dm.data["characters"]:
            self.char_listbox.insert(tk.END, name)

    def on_char_select(self, event):
        sel = self.char_listbox.curselection()
        if not sel: return
        name = self.char_listbox.get(sel[0])
        log_debug(f"Character selected: {name}")
        self.build_char_form(name)

    def build_char_form(self, char_name):
        log_debug(f"Building form for character: {char_name}")
        for w in self.char_form.winfo_children(): w.destroy()
        
        char_data = self.dm.data["characters"].get(char_name, {})
        
        # Header with name
        tk.Label(self.char_form, text=f"แก้ไขตัวละคร: {char_name}", font=("Segoe UI", 12, "bold"), bg=self.char_form["bg"], fg=self.colors["accent"]).pack(anchor="w", pady=(0, 15))
        
        # Fields based on config
        self.char_inputs = {}
        fields = self.dm.data.get("character_fields_config", ["ชื่อ", "บทบาท", "นิสัย", "ปูมหลัง"])
        
        for field in fields:
            h = 3 if field in ["นิสัย", "ปูมหลัง", "ลักษณะ"] else 1
            inp = self.create_input(self.char_form, field, h)
            val = char_data.get(field, "")
            if h > 1: inp.insert("1.0", val)
            else: inp.insert(0, val)
            self.char_inputs[field] = inp
            
        tk.Button(self.char_form, text="บันทึกตัวละคร 💾", command=lambda: self.save_character(char_name), bg=self.colors["success"], fg="white", bd=0, pady=10).pack(fill="x", pady=20)

    def add_character(self):
        name = filedialog.askstring("เพิ่มตัวละคร", "กรุณาใส่ชื่อตัวละคร:")
        if name:
            log_info(f"Adding new character: {name}")
            self.dm.data["characters"][name] = {"ชื่อ": name}
            self.refresh_char_list()
            self.dm.save_all()

    def delete_character(self):
        sel = self.char_listbox.curselection()
        if not sel: return
        name = self.char_listbox.get(sel[0])
        if messagebox.askyesno("ยืนยัน", f"คุณต้องการลบตัวละคร '{name}' ใช่หรือไม่?"):
            log_info(f"Deleting character: {name}")
            del self.dm.data["characters"][name]
            self.refresh_char_list()
            for w in self.char_form.winfo_children(): w.destroy()
            self.dm.save_all()

    def save_character(self, old_name):
        log_info(f"Saving character data for: {old_name}")
        new_data = {}
        for field, inp in self.char_inputs.items():
            if hasattr(inp, "get") and not isinstance(inp, scrolledtext.ScrolledText):
                new_data[field] = inp.get()
            else:
                new_data[field] = inp.get("1.0", tk.END).strip()
        
        new_name = new_data.get("ชื่อ", old_name)
        if new_name != old_name:
            log_info(f"Renaming character from {old_name} to {new_name}")
            del self.dm.data["characters"][old_name]
        
        self.dm.data["characters"][new_name] = new_data
        self.dm.save_all()
        self.refresh_char_list()
        messagebox.showinfo("สำเร็จ", f"บันทึกข้อมูล '{new_name}' เรียบร้อยแล้ว")

    def manage_custom_fields(self):
        log_debug("Opening custom fields manager")
        from nexus_god.ui.custom_fields_manager import CustomFieldsManager
        CustomFieldsManager(self.root, self.dm, on_update=lambda: self.switch_tab("chars"))

    def save_plot_data(self):
        log_info("Saving plot data from form")
        self.dm.data["plot"]["act1"] = self.plot_act1.get("1.0", tk.END).strip()
        self.dm.data["plot"]["act2"] = self.plot_act2.get("1.0", tk.END).strip()
        self.dm.data["plot"]["act3"] = self.plot_act3.get("1.0", tk.END).strip()
        self.dm.save_all()
        messagebox.showinfo("สำเร็จ", "บันทึกโครงเรื่องเรียบร้อยแล้ว")

    def on_chapter_change(self, event):
        name = self.chapter_selector.get()
        log_debug(f"Chapter changed to: {name}")
        self.editor_text.delete("1.0", tk.END)
        self.editor_text.insert("1.0", self.dm.data["chapters"].get(name, ""))

    def add_chapter(self):
        num = len(self.dm.data["chapters"]) + 1
        name = f"ตอนที่ {num}"
        log_info(f"Adding new chapter: {name}")
        self.dm.data["chapters"][name] = ""
        self.chapter_selector["values"] = list(self.dm.data["chapters"].keys())
        self.chapter_selector.set(name)
        self.on_chapter_change(None)

    def save_current_chapter(self):
        name = self.chapter_selector.get()
        if not name: return
        log_info(f"Saving chapter: {name}")
        content = self.editor_text.get("1.0", tk.END).strip()
        self.dm.data["chapters"][name] = content
        self.dm.save_all()
        self.editor_status.config(text=f"บันทึกแล้วเมื่อ {datetime.now().strftime('%H:%M:%S')}")

    def ai_continue_writing(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("AI Continue Writing triggered")
        
        # Get context
        content = self.editor_text.get("1.0", tk.END).strip()
        # Take last 2000 chars for context
        context_text = content[-2000:] if len(content) > 2000 else content
        
        world_info = json.dumps(self.dm.data["world"], ensure_ascii=False)
        memory_info = json.dumps(self.dm.data.get("memory", {}), ensure_ascii=False)
        
        def task():
            try:
                self.root.after(0, lambda: self.editor_status.config(text="AI กำลังเขียนต่อ..."))
                prompt = f"ข้อมูลโลก: {world_info}\nความจำ: {memory_info}\n\nเนื้อหาล่าสุด:\n{context_text}\n\nช่วยเขียนเนื้อหาต่อจากนี้อีกประมาณ 2-3 ย่อหน้า โดยรักษาโทนเรื่องเดิม"
                
                res = self.call_ai_simple(prompt, "คุณคือผู้ช่วยเขียนนิยายมืออาชีพ เขียนเนื้อหาที่ลื่นไหลและน่าติดตาม")
                
                def update():
                    self.editor_text.insert(tk.END, f"\n\n{res}")
                    self.editor_text.see(tk.END)
                    self.is_ai_busy = False
                    self.editor_status.config(text="เขียนต่อเสร็จสิ้น")
                    self.save_current_chapter()
                
                self.root.after(0, update)
            except Exception as e:
                log_error(f"Error in ai_continue: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def ai_improve_text(self):
        try:
            selected = self.editor_text.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            messagebox.showwarning("คำเตือน", "กรุณาคลุมดำข้อความที่ต้องการขัดเกลา")
            return

        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("AI Improve Text triggered")

        def task():
            try:
                self.root.after(0, lambda: self.editor_status.config(text="AI กำลังขัดเกลา..."))
                prompt = f"ช่วยขัดเกลาข้อความนี้ให้สละสลวยและได้อารมณ์มากขึ้น:\n\n{selected}"
                res = self.call_ai_simple(prompt, "คุณคือบรรณาธิการมืออาชีพที่เชี่ยวชาญการใช้ภาษาไทย")
                
                def update():
                    # Replace selection
                    start = self.editor_text.index(tk.SEL_FIRST)
                    end = self.editor_text.index(tk.SEL_LAST)
                    self.editor_text.delete(start, end)
                    self.editor_text.insert(start, res)
                    self.is_ai_busy = False
                    self.editor_status.config(text="ขัดเกลาเสร็จสิ้น")
                    self.save_current_chapter()
                
                self.root.after(0, update)
            except Exception as e:
                log_error(f"Error in ai_improve: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def ai_suggest_scene(self):
        if hasattr(self, 'is_ai_busy') and self.is_ai_busy: return
        self.is_ai_busy = True
        log_info("AI Suggest Scene triggered")
        
        content = self.editor_text.get("1.0", tk.END).strip()
        context_text = content[-2000:] if len(content) > 2000 else content
        
        def task():
            try:
                self.root.after(0, lambda: self.editor_status.config(text="AI กำลังคิดฉากต่อไป..."))
                prompt = f"จากเนื้อหาล่าสุดนี้:\n{context_text}\n\nช่วยแนะนำ 3 แนวทางที่เป็นไปได้สำหรับฉากต่อไป"
                res = self.call_ai_simple(prompt, "คุณคือที่ปรึกษาด้านการวางโครงเรื่องนิยาย")
                
                def show():
                    messagebox.showinfo("🎬 คำแนะนำฉากต่อไป", res)
                    self.is_ai_busy = False
                    self.editor_status.config(text="แนะนำเสร็จสิ้น")
                
                self.root.after(0, show)
            except Exception as e:
                log_error(f"Error in ai_suggest: {e}")
                self.is_ai_busy = False
                self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def refresh_memory_list(self):
        log_debug("Refreshing memory listbox")
        self.memory_listbox.delete(0, tk.END)
        memory = self.dm.data.get("memory", {})
        for key in memory:
            self.memory_listbox.insert(tk.END, key)

    def on_memory_select(self, event):
        sel = self.memory_listbox.curselection()
        if not sel: return
        key = self.memory_listbox.get(sel[0])
        self.build_memory_form(key)

    def build_memory_form(self, key):
        for w in self.memory_form.winfo_children(): w.destroy()
        
        val = self.dm.data.get("memory", {}).get(key, "")
        
        tk.Label(self.memory_form, text=f"ความจำ: {key}", font=("Segoe UI", 12, "bold"), bg=self.memory_form["bg"], fg=self.colors["accent"]).pack(anchor="w", pady=(0, 15))
        
        self.mem_key_input = self.create_input(self.memory_form, "หัวข้อความจำ")
        self.mem_key_input.insert(0, key)
        
        self.mem_val_input = self.create_input(self.memory_form, "รายละเอียด", 10)
        self.mem_val_input.insert("1.0", val)
        
        tk.Button(self.memory_form, text="บันทึกความจำ 💾", command=lambda: self.save_memory(key), bg=self.colors["success"], fg="white", bd=0, pady=10).pack(fill="x", pady=20)

    def add_memory(self):
        key = filedialog.askstring("เพิ่มความจำ", "กรุณาใส่หัวข้อความจำ (เช่น ชื่อเมือง, ตำนาน):")
        if key:
            if "memory" not in self.dm.data: self.dm.data["memory"] = {}
            self.dm.data["memory"][key] = ""
            self.refresh_memory_list()
            self.dm.save_all()

    def delete_memory(self):
        sel = self.memory_listbox.curselection()
        if not sel: return
        key = self.memory_listbox.get(sel[0])
        if messagebox.askyesno("ยืนยัน", f"ลบความจำ '{key}'?"):
            del self.dm.data["memory"][key]
            self.refresh_memory_list()
            for w in self.memory_form.winfo_children(): w.destroy()
            self.dm.save_all()

    def save_memory(self, old_key):
        new_key = self.mem_key_input.get().strip()
        new_val = self.mem_val_input.get("1.0", tk.END).strip()
        
        if "memory" not in self.dm.data: self.dm.data["memory"] = {}
        
        if new_key != old_key:
            del self.dm.data["memory"][old_key]
        
        self.dm.data["memory"][new_key] = new_val
        self.dm.save_all()
        self.refresh_memory_list()
        messagebox.showinfo("สำเร็จ", "บันทึกความจำแล้ว")

    def save_settings(self):
        log_info("Saving settings from form")
        theme = self.set_theme.get().strip()
        api_key = self.set_api.get().strip()
        
        self.dm.config["theme"] = theme
        self.dm.config["api_key"] = api_key
        self.dm.save_config()
        
        messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่าแล้ว (กรุณารีสตาร์ทโปรแกรมเพื่อเปลี่ยนธีม)")

def run_app():
    log_info("Starting main application")
    root = tk.Tk()
    app = NexusGodWriter(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
