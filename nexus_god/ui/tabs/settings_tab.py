import tkinter as tk
from tkinter import ttk, messagebox
from nexus_god.core.logging_utils import log_debug, log_info

class SettingsTab:
    def __init__(self, parent, dm, colors, build_card, create_input, refresh_sidebar):
        self.parent = parent
        self.dm = dm
        self.colors = colors
        self.build_card = build_card
        self.create_input = create_input
        self.refresh_sidebar = refresh_sidebar

    def build(self):
        log_debug("Building settings content")
        card = self.build_card(self.parent, "ตั้งค่า (Settings)")
        
        # Tabs for Settings sub-sections
        settings_tabs = ttk.Notebook(card)
        settings_tabs.pack(fill="both", expand=True)

        # 1. General Settings
        general_frame = tk.Frame(settings_tabs, bg=self.colors["card"], padx=10, pady=10)
        settings_tabs.add(general_frame, text="⚙️ ทั่วไป")
        self.build_general_settings(general_frame)

        # 2. Tab Management (Dynamic Menus)
        tabs_frame = tk.Frame(settings_tabs, bg=self.colors["card"], padx=10, pady=10)
        settings_tabs.add(tabs_frame, text="📂 จัดการเมนู (Dynamic Menus)")
        self.build_tab_management(tabs_frame)

        # 3. Module Manager (Dynamic Modules)
        modules_frame = tk.Frame(settings_tabs, bg=self.colors["card"], padx=10, pady=10)
        settings_tabs.add(modules_frame, text="📦 จัดการโมดูล (Module Manager)")
        self.build_module_manager(modules_frame)

        # Save Button at the bottom
        tk.Button(card, text="บันทึกการตั้งค่าทั้งหมด 💾", command=self.save_settings, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=12).pack(fill="x", pady=(10, 0))

    def build_general_settings(self, parent):
        self.set_theme = self.create_input(parent, "ธีม (dark/light)")
        self.set_theme.insert(0, self.dm.config.get("theme", "dark"))
        
        tk.Label(parent, text="AI Provider:", font=("Segoe UI", 9, "bold"), bg=parent["bg"], fg=self.colors["accent"]).pack(anchor="w", pady=(10, 5))
        self.set_provider = ttk.Combobox(parent, values=["gemini", "groq"])
        self.set_provider.pack(fill="x", pady=(0, 10))
        self.set_provider.set(self.dm.config.get("ai_provider", "gemini"))

        self.set_api = self.create_input(parent, "Gemini API Key")
        self.set_api.insert(0, self.dm.config.get("api_key", ""))
        
        self.set_groq_api = self.create_input(parent, "Groq API Key")
        self.set_groq_api.insert(0, self.dm.config.get("groq_api_key", ""))

    def build_tab_management(self, parent):
        tk.Label(parent, text="เลือกเมนูที่ต้องการแสดงสำหรับโลกนี้:", font=("Segoe UI", 10, "bold"), bg=parent["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 10))
        
        self.tab_vars = {}
        all_tabs = [
            ("wizard", "✨ วิถีแห่งสวรรค์ (Guided)"), 
            ("chat", "💬 สนทนาทวยเทพ"),
            ("world", "🌍 กำเนิดโลก"), 
            ("lore", "📜 ตำนานและประวัติศาสตร์ (Core)"),
            ("chars", "👤 โรงหล่อตัวละคร (Core)"),
            ("items", "⚔️ คลังไอเทม/อาวุธ"), 
            ("plot", "📜 โครงเรื่องสวรรค์"),
            ("editor", "📝 แก้ไขเนื้อเรื่อง"), 
            ("memory", "🧠 ธนาคารความจำ"),
            ("review", "🔍 ตรวจสอบคัมภีร์"), 
            ("export", "🚀 AI และส่งออก"),
        ]
        
        enabled = self.dm.data.get("enabled_tabs", [])
        
        # Grid layout for checkboxes
        grid_frame = tk.Frame(parent, bg=parent["bg"])
        grid_frame.pack(fill="both", expand=True)
        
        for i, (key, label) in enumerate(all_tabs):
            var = tk.BooleanVar(value=key in enabled)
            self.tab_vars[key] = var
            cb = tk.Checkbutton(grid_frame, text=label, variable=var, bg=parent["bg"], fg=self.colors["text"], selectcolor=self.colors["sidebar"], activebackground=parent["bg"], activeforeground=self.colors["accent"], font=("Segoe UI", 9))
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=20, pady=5)

    def build_module_manager(self, parent):
        from tkinter import scrolledtext
        tk.Label(parent, text="สร้างและจัดการโมดูลข้อมูลของคุณเอง:", font=("Segoe UI", 10, "bold"), bg=parent["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 10))
        
        # List of current modules
        self.mod_listbox = tk.Listbox(parent, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 9), height=5)
        self.mod_listbox.pack(fill="x", pady=5)
        self.refresh_mod_list()
        
        btn_frame = tk.Frame(parent, bg=parent["bg"])
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="+ เพิ่มโมดูลใหม่", command=self.add_new_module, bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, padx=10, pady=5).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ ลบโมดูล", command=self.delete_module, bg=self.colors["danger"], fg="white", bd=0, padx=10, pady=5).pack(side="left", padx=5)

    def refresh_mod_list(self):
        self.mod_listbox.delete(0, tk.END)
        modules = self.dm.data.get("modules", {})
        for mod_id, mod_config in modules.items():
            label = mod_config.get("display_name", mod_id)
            self.mod_listbox.insert(tk.END, f"{mod_id} ({label})")

    def add_new_module(self):
        from tkinter import scrolledtext
        # Simple dialog to add a module
        dialog = tk.Toplevel(self.parent)
        dialog.title("เพิ่มโมดูลใหม่")
        dialog.geometry("400x500")
        dialog.configure(bg=self.colors["bg"])
        
        tk.Label(dialog, text="ID โมดูล (ภาษาอังกฤษเท่านั้น):", bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=(10, 0))
        id_entry = tk.Entry(dialog, bg=self.colors["input"], fg=self.colors["text"])
        id_entry.pack(pady=5, padx=20, fill="x")
        
        tk.Label(dialog, text="ชื่อที่แสดง (Display Name):", bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=(10, 0))
        name_entry = tk.Entry(dialog, bg=self.colors["input"], fg=self.colors["text"])
        name_entry.pack(pady=5, padx=20, fill="x")
        
        tk.Label(dialog, text="ไอคอน (Emoji):", bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=(10, 0))
        icon_entry = tk.Entry(dialog, bg=self.colors["input"], fg=self.colors["text"])
        icon_entry.insert(0, "📦")
        icon_entry.pack(pady=5, padx=20, fill="x")
        
        tk.Label(dialog, text="ฟิลด์ข้อมูล (Key:Label, หนึ่งบรรทัดต่อหนึ่งฟิลด์):", bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=(10, 0))
        fields_text = scrolledtext.ScrolledText(dialog, bg=self.colors["input"], fg=self.colors["text"], height=10)
        fields_text.insert("1.0", "name:ชื่อ\ndescription:คำอธิบาย")
        fields_text.pack(pady=5, padx=20, fill="both", expand=True)

        def save():
            m_id = id_entry.get().strip().lower()
            m_name = name_entry.get().strip()
            m_icon = icon_entry.get().strip()
            m_fields_raw = fields_text.get("1.0", tk.END).strip().split("\n")
            
            if not m_id or not m_name:
                messagebox.showerror("Error", "กรุณาระบุ ID และชื่อโมดูล")
                return
            
            fields = []
            for line in m_fields_raw:
                if ":" in line:
                    parts = line.split(":", 1)
                    k = parts[0].strip()
                    l = parts[1].strip()
                    fields.append({"key": k, "label": l, "type": "textarea" if "คำอธิบาย" in l or "ประวัติ" in l else "text"})
            
            if not fields:
                messagebox.showerror("Error", "กรุณาระบุอย่างน้อยหนึ่งฟิลด์")
                return
                
            if "modules" not in self.dm.data: self.dm.data["modules"] = {}
            self.dm.data["modules"][m_id] = {
                "display_name": m_name,
                "icon": m_icon,
                "fields": fields,
                "entries": []
            }
            self.dm.save_all()
            self.refresh_mod_list()
            self.refresh_sidebar()
            dialog.destroy()
            messagebox.showinfo("สำเร็จ", f"เพิ่มโมดูล '{m_name}' เรียบร้อยแล้ว")

        tk.Button(dialog, text="สร้างโมดูล 🚀", command=save, bg=self.colors["success"], fg="white").pack(pady=20)

    def delete_module(self):
        selection = self.mod_listbox.curselection()
        if not selection: return
        
        text = self.mod_listbox.get(selection[0])
        m_id = text.split(" (")[0]
        
        if messagebox.askyesno("ยืนยัน", f"คุณต้องการลบโมดูล '{m_id}' ใช่หรือไม่? ข้อมูลทั้งหมดในโมดูลจะหายไป"):
            del self.dm.data["modules"][m_id]
            self.dm.save_all()
            self.refresh_mod_list()
            self.refresh_sidebar()
            messagebox.showinfo("สำเร็จ", "ลบโมดูลเรียบร้อยแล้ว")

    def save_settings(self):
        log_info("Saving settings from form")
        
        # Save General
        theme = self.set_theme.get().strip()
        api_key = self.set_api.get().strip()
        groq_api_key = self.set_groq_api.get().strip()
        provider = self.set_provider.get().strip()
        
        self.dm.config["theme"] = theme
        self.dm.config["api_key"] = api_key
        self.dm.config["groq_api_key"] = groq_api_key
        self.dm.config["ai_provider"] = provider
        
        # Save Tabs
        new_enabled = []
        for key, var in self.tab_vars.items():
            if var.get():
                new_enabled.append(key)
        
        # Always include settings
        if "settings" not in new_enabled:
            new_enabled.append("settings")
            
        self.dm.data["enabled_tabs"] = new_enabled
        self.dm.save_all()
        
        self.refresh_sidebar()
        messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่าและอัปเดตเมนูเรียบร้อยแล้ว")
