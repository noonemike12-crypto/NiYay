import tkinter as tk
from nexus_god.core.logging_utils import log_debug, log_info
from tkinter import messagebox, filedialog

class MemoryTab:
    def __init__(self, parent, dm, colors, build_card, create_input):
        self.parent = parent
        self.dm = dm
        self.colors = colors
        self.build_card = build_card
        self.create_input = create_input

    def build(self):
        log_debug("Building memory content")
        card = self.build_card(self.parent, "ธนาคารความจำ (Memory Bank)")
        
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

    def refresh_memory_list(self):
        log_debug("Refreshing facts listbox")
        self.memory_listbox.delete(0, tk.END)
        facts = self.dm.data.get("facts", [])
        for fact in facts:
            if isinstance(fact, dict):
                display = fact.get("id") or fact.get("content")[:20] + "..."
                self.memory_listbox.insert(tk.END, display)

    def on_memory_select(self, event):
        sel = self.memory_listbox.curselection()
        if not sel: return
        idx = sel[0]
        self.build_memory_form(idx)

    def build_memory_form(self, idx):
        for w in self.memory_form.winfo_children(): w.destroy()
        
        fact = self.dm.data.get("facts", [])[idx]
        
        tk.Label(self.memory_form, text=f"ข้อเท็จจริง (Fact) #{idx+1}", font=("Segoe UI", 12, "bold"), bg=self.memory_form["bg"], fg=self.colors["accent"]).pack(anchor="w", pady=(0, 15))
        
        self.mem_id_input = self.create_input(self.memory_form, "ID/หัวข้อ")
        self.mem_id_input.insert(0, fact.get("id", ""))
        
        self.mem_content_input = self.create_input(self.memory_form, "เนื้อหา/ข้อเท็จจริง", 5)
        self.mem_content_input.insert("1.0", fact.get("content", ""))
        
        # Category and Importance
        row = tk.Frame(self.memory_form, bg=self.memory_form["bg"])
        row.pack(fill="x", pady=5)
        
        tk.Label(row, text="หมวดหมู่:", bg=row["bg"], fg=self.colors["muted"]).pack(side="left")
        self.mem_cat_input = tk.Entry(row, bg=self.colors["input"], fg="white", bd=0)
        self.mem_cat_input.insert(0, fact.get("category", "ทั่วไป"))
        self.mem_cat_input.pack(side="left", padx=10, fill="x", expand=True)
        
        tk.Label(row, text="ความสำคัญ:", bg=row["bg"], fg=self.colors["muted"]).pack(side="left")
        self.mem_imp_input = ttk.Combobox(row, values=["ต่ำ", "ปานกลาง", "สูง", "วิกฤต"], width=10)
        self.mem_imp_input.set(fact.get("importance", "ปานกลาง"))
        self.mem_imp_input.pack(side="left", padx=10)
        
        tk.Button(self.memory_form, text="บันทึกข้อเท็จจริง 💾", command=lambda: self.save_memory(idx), bg=self.colors["success"], fg="white", bd=0, pady=10).pack(fill="x", pady=20)

    def add_memory(self):
        from tkinter import simpledialog
        key = simpledialog.askstring("เพิ่มความจำ", "กรุณาใส่หัวข้อความจำ (เช่น ชื่อเมือง, ตำนาน):")
        if key:
            if "facts" not in self.dm.data: self.dm.data["facts"] = []
            self.dm.data["facts"].append({
                "id": key,
                "content": "",
                "category": "ทั่วไป",
                "importance": "ปานกลาง"
            })
            self.refresh_memory_list()
            self.dm.save_all()

    def delete_memory(self):
        sel = self.memory_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if messagebox.askyesno("ยืนยัน", "ลบข้อเท็จจริงนี้?"):
            self.dm.data["facts"].pop(idx)
            self.refresh_memory_list()
            for w in self.memory_form.winfo_children(): w.destroy()
            self.dm.save_all()

    def save_memory(self, idx):
        new_id = self.mem_id_input.get().strip()
        new_content = self.mem_content_input.get("1.0", tk.END).strip()
        new_cat = self.mem_cat_input.get().strip()
        new_imp = self.mem_imp_input.get()
        
        self.dm.data["facts"][idx] = {
            "id": new_id,
            "content": new_content,
            "category": new_cat,
            "importance": new_imp
        }
        
        # Update compatibility memory dict
        self.dm.data["memory"] = {f["id"]: f["content"] for f in self.dm.data["facts"] if isinstance(f, dict) and "id" in f}
        
        self.dm.save_all()
        self.refresh_memory_list()
        messagebox.showinfo("สำเร็จ", "บันทึกข้อเท็จจริงแล้ว")
