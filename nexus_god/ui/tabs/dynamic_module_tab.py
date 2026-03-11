import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from nexus_god.core.logging_utils import log_debug, log_info

class DynamicModuleTab:
    def __init__(self, parent, dm, colors, build_card, create_input, mod_id):
        self.parent = parent
        self.dm = dm
        self.colors = colors
        self.build_card = build_card
        self.create_input = create_input
        self.mod_id = mod_id
        self.mod_config = self.dm.data["modules"].get(mod_id, {})
        self.entries = self.mod_config.get("entries", [])
        self.fields = self.mod_config.get("fields", [])

    def build(self):
        log_debug(f"Building dynamic module tab for: {self.mod_id}")
        title = self.mod_config.get("display_name", self.mod_id.capitalize())
        icon = self.mod_config.get("icon", "📦")
        
        card = self.build_card(self.parent, f"{icon} {title}")
        
        # Split layout: List on left, Form on right
        paned = tk.PanedWindow(card, orient="horizontal", bg=self.colors["card"], bd=0, sashwidth=4)
        paned.pack(fill="both", expand=True)
        
        # Left: List
        list_frame = tk.Frame(paned, bg=self.colors["card"])
        paned.add(list_frame, width=350)
        
        tk.Label(list_frame, text="รายการทั้งหมด", font=("Segoe UI", 10, "bold"), bg=self.colors["card"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 10))
        
        self.listbox = tk.Listbox(list_frame, bg=self.colors["input"], fg=self.colors["text"], font=("Segoe UI", 10), bd=0, highlightthickness=0, selectbackground=self.colors["accent"], selectforeground="black")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        
        btn_frame = tk.Frame(list_frame, bg=self.colors["card"], pady=10)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="+ เพิ่มใหม่", command=self.clear_form, bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, padx=15, pady=8).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ ลบ", command=self.delete_entry, bg=self.colors["danger"], fg="white", bd=0, padx=15, pady=8).pack(side="left", padx=5)
        
        # Right: Form
        self.form_frame = tk.Frame(paned, bg=self.colors["card"], padx=20)
        paned.add(self.form_frame)
        
        self.inputs = {}
        self.build_form()
        
        tk.Button(self.form_frame, text="บันทึกข้อมูล 💾", command=self.save_entry, bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=12).pack(fill="x", pady=20)
        
        self.refresh_list()

    def build_form(self):
        for w in self.form_frame.winfo_children():
            if not isinstance(w, tk.Button): w.destroy()
            
        for field in self.fields:
            key = field["key"]
            label = field["label"]
            f_type = field.get("type", "text")
            
            if f_type == "textarea":
                self.inputs[key] = self.create_input(self.form_frame, label, height=5)
            else:
                self.inputs[key] = self.create_input(self.form_frame, label)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        self.entries = self.mod_config.get("entries", [])
        for entry in self.entries:
            # Try to find a good display name
            display = entry.get("name") or entry.get("title") or "ไม่มีชื่อ"
            self.listbox.insert(tk.END, display)

    def on_select(self, event):
        selection = self.listbox.curselection()
        if not selection: return
        
        idx = selection[0]
        entry = self.entries[idx]
        
        for field in self.fields:
            key = field["key"]
            val = entry.get(key, "")
            inp = self.inputs[key]
            
            if isinstance(inp, tk.Entry):
                inp.delete(0, tk.END)
                inp.insert(0, val)
            elif isinstance(inp, scrolledtext.ScrolledText):
                inp.delete("1.0", tk.END)
                inp.insert("1.0", val)

    def clear_form(self):
        self.listbox.selection_clear(0, tk.END)
        for inp in self.inputs.values():
            if isinstance(inp, tk.Entry):
                inp.delete(0, tk.END)
            elif isinstance(inp, scrolledtext.ScrolledText):
                inp.delete("1.0", tk.END)

    def save_entry(self):
        entry = {}
        for key, inp in self.inputs.items():
            if isinstance(inp, tk.Entry):
                entry[key] = inp.get()
            elif isinstance(inp, scrolledtext.ScrolledText):
                entry[key] = inp.get("1.0", tk.END).strip()
        
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.entries[idx] = entry
        else:
            self.entries.append(entry)
            
        self.mod_config["entries"] = self.entries
        self.dm.save_all()
        self.refresh_list()
        messagebox.showinfo("สำเร็จ", "บันทึกข้อมูลเรียบร้อยแล้ว")

    def delete_entry(self):
        selection = self.listbox.curselection()
        if not selection: return
        
        if messagebox.askyesno("ยืนยัน", "คุณต้องการลบข้อมูลนี้ใช่หรือไม่?"):
            idx = selection[0]
            self.entries.pop(idx)
            self.mod_config["entries"] = self.entries
            self.dm.save_all()
            self.refresh_list()
            self.clear_form()
