import customtkinter as ctk
import json
import os
import sys
import subprocess
import threading
import time
import webbrowser
from tkinter import filedialog, messagebox
from PIL import Image
import pystray
from pystray import MenuItem as item
import shutil

# --- Configuration ---
SERVICE_NAME = "VMSController"
CONFIG_FILE = "server_config.json"
KEYS_FILE = "vms_keys.json"
NSSM_EXE = "nssm.exe"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Resource paths for icons
ICON_PATH = resource_path("VMS_App_Icon.ico")
CHECK_ICO = resource_path("check.ico")
NO_ICO = resource_path("no.ico")

# Theme Setup
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class VMSControllerUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Geometry - Increased height for certificate UI
        self.title("VMS Service Controller")
        self.geometry("750x600") 
        self.resizable(False, False)
        self.configure(fg_color="#F0F2F5") 

        # Set Window Icon
        if os.path.exists(ICON_PATH):
            self.iconbitmap(ICON_PATH)

        # Handle Window Close (Minimize to Tray)
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.last_known_status = None
        self.current_ui_state = None 
        
        # Inner Rounded Container
        self.main_container = ctk.CTkFrame(self, fg_color="#D1D5DB", corner_radius=20)
        self.main_container.pack(padx=25, pady=(15, 5), fill="both", expand=True)

        # Tabs
        self.tabview = ctk.CTkTabview(self.main_container, width=680, height=480, 
                                      fg_color="transparent",
                                      segmented_button_selected_color="#3498DB",
                                      segmented_button_unselected_color="#9CA3AF")
        self.tabview.pack(padx=15, pady=10, fill="both", expand=True)
        
        self.tab_keys = self.tabview.add("Integration Partner Keys")
        self.tab_control = self.tabview.add("Service Control")
        self.tab_log = self.tabview.add("Version Log")

        self.setup_integration_keys_tab()
        self.setup_service_control_tab()
        self.setup_version_log_tab()
        self.load_all_data()

        # Footer
        self.footer = ctk.CTkLabel(self, text="© 2025 Copyright by Indsys Holdings", 
                                   text_color="#6B7280", font=ctk.CTkFont(size=12))
        self.footer.pack(side="bottom", pady=8)

        # Tray and Monitoring
        self.setup_tray_icon()
        self.stop_event = threading.Event()
        threading.Thread(target=self.monitor_service, daemon=True).start()

    # --- TRAY LOGIC ---
    # (Same as before, simplified for brevity)
    def minimize_to_tray(self):
        self.withdraw()

    def show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)

    def quit_app(self, icon=None, item=None):
        if hasattr(self, 'tray_icon'): self.tray_icon.stop()
        self.stop_event.set()
        self.destroy()
        sys.exit()

    def setup_tray_icon(self):
        if os.path.exists(ICON_PATH):
            taskbar_img = Image.open(ICON_PATH)
        else:
            taskbar_img = Image.new('RGB', (64, 64), color=(0, 0, 0))

        menu = pystray.Menu(
            item('Open Manager', self.show_window, default=True),
            item('Quit', self.quit_app)
        )
        self.tray_icon = pystray.Icon("VMS", taskbar_img, "VMS Controller", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    # --- UI COMPONENTS ---

    def setup_integration_keys_tab(self):
        card = ctk.CTkFrame(self.tab_keys, fg_color="#FFFFFF", corner_radius=15)
        card.pack(expand=True, fill="both", padx=20, pady=15)
        ctk.CTkLabel(card, text="Integration Credentials", text_color="#1F2937", 
                      font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15, 20))
        self.entry_key = self.create_input_row(card, "Partner Key")
        self.entry_secret = self.create_input_row(card, "Partner Secret", True)
        self.save_btn = ctk.CTkButton(card, text="Save", fg_color="#3498DB", 
                                       width=140, height=32, corner_radius=6, command=self.save_all_data)
        self.save_btn.pack(pady=20)

    def create_input_row(self, parent, label_text, is_password=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=60, pady=8)
        ctk.CTkLabel(row, text=f"{label_text}:", text_color="#374151", width=110, anchor="e").pack(side="left", padx=(0, 15))
        entry = ctk.CTkEntry(row, width=280, height=30, fg_color="#F9FAFB", border_width=1, show="*" if is_password else "")
        entry.pack(side="left")
        return entry

    def setup_service_control_tab(self):
        card = ctk.CTkFrame(self.tab_control, fg_color="#FFFFFF", corner_radius=15)
        card.pack(expand=True, fill="both", padx=20, pady=15)

        # Header Info
        header = ctk.CTkFrame(card, fg_color="#DBEAFE", height=40, corner_radius=10)
        header.pack(fill="x", padx=15, pady=(15, 5))
        header.columnconfigure(0, weight=2); header.columnconfigure(1, weight=2); header.columnconfigure(2, weight=1)
        ctk.CTkLabel(header, text="SERVICE NAME", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1E40AF").grid(row=0, column=0, pady=8, sticky="w", padx=25)
        ctk.CTkLabel(header, text="IP / PORT", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1E40AF").grid(row=0, column=1, pady=8)
        ctk.CTkLabel(header, text="STATUS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1E40AF").grid(row=0, column=2, pady=8, sticky="e", padx=25)
        
        # Status Row
        row = ctk.CTkFrame(card, fg_color="#F3F4F6", corner_radius=10)
        row.pack(fill="x", padx=15, pady=5)
        row.columnconfigure(0, weight=2); row.columnconfigure(1, weight=2); row.columnconfigure(2, weight=1)
        ctk.CTkLabel(row, text="VMS API Service", text_color="#111827", font=ctk.CTkFont(size=13)).grid(row=0, column=0, pady=20, sticky="w", padx=25)
        self.ip_link = ctk.CTkLabel(row, text="http://127.0.0.1:8000", text_color="#3498DB", font=ctk.CTkFont(size=14, underline=True), cursor="hand2")
        self.ip_link.grid(row=0, column=1, pady=20)
        self.ip_link.bind("<Button-1>", self.open_endpoint)
        self.status_indicator = ctk.CTkLabel(row, text="STOPPED...", text_color="#DC2626", font=ctk.CTkFont(size=13, weight="bold"))
        self.status_indicator.grid(row=0, column=2, pady=20, sticky="e", padx=25)

        # Protocol Switch
        self.p_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.p_frame.pack(pady=(15, 5)) 
        
        self.protocol_var = ctk.StringVar(value="HTTP")
        self.protocol_switch = ctk.CTkSegmentedButton(self.p_frame, values=["HTTP", "HTTPS"], 
                                                      variable=self.protocol_var, 
                                                      command=self.toggle_protocol_ui)
        self.protocol_switch.pack()

        # --- CERTIFICATE MANAGER (Hidden by default) ---
        self.cert_frame = ctk.CTkFrame(card, fg_color="#F9FAFB", corner_radius=10, border_width=1, border_color="#E5E7EB")
        # Don't pack immediately, show only if HTTPS

        ctk.CTkLabel(self.cert_frame, text="Secure Certificate Setup", font=("Roboto", 12, "bold"), text_color="#374151").pack(pady=(10,5))
        
        # Cert Row
        c_row = ctk.CTkFrame(self.cert_frame, fg_color="transparent")
        c_row.pack(fill="x", padx=20, pady=5)
        self.lbl_cert = ctk.CTkLabel(c_row, text="Pending...", text_color="orange", font=("Arial", 11))
        self.lbl_cert.pack(side="right", padx=5)
        ctk.CTkButton(c_row, text="Upload cert.pem", width=120, height=28, fg_color="#4B5563", command=self.upload_cert).pack(side="left")
        
        # Key Row
        k_row = ctk.CTkFrame(self.cert_frame, fg_color="transparent")
        k_row.pack(fill="x", padx=20, pady=5)
        self.lbl_key = ctk.CTkLabel(k_row, text="Pending...", text_color="orange", font=("Arial", 11))
        self.lbl_key.pack(side="right", padx=5)
        ctk.CTkButton(k_row, text="Upload key.pem", width=120, height=28, fg_color="#4B5563", command=self.upload_key).pack(side="left")

        self.btn_validate = ctk.CTkButton(self.cert_frame, text="Validate Certificates", fg_color="#D97706", height=28, command=self.validate_certs)
        self.btn_validate.pack(pady=(5, 10))

        # Button Container
        self.btn_container = ctk.CTkFrame(card, fg_color="transparent")
        self.btn_container.pack(pady=20)
        
        self.start_btn = ctk.CTkButton(self.btn_container, text="START", fg_color="#10B981", 
                                       hover_color="#059669", width=120, height=32, corner_radius=20,
                                       command=self.start_service)
        
        self.stop_btn = ctk.CTkButton(self.btn_container, text="STOP", fg_color="#EF4444", 
                                      hover_color="#DC2626", width=120, height=32, corner_radius=20,
                                      command=self.stop_service)
        
    def setup_version_log_tab(self):
        card = ctk.CTkFrame(self.tab_log, fg_color="#FFFFFF", corner_radius=15)
        card.pack(expand=True, fill="both", padx=20, pady=15)
        ctk.CTkLabel(card, text="VMS Controller Pro", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        log_box = ctk.CTkTextbox(card, width=580, height=140, fg_color="#F9FAFB", border_width=1)
        log_box.pack(pady=5, fill="both", expand=True)
        log_box.insert("0.0", "• [UPDATE] Added HTTPS Support\n• [FEATURE] Certificate Upload & Validation")
        log_box.configure(state="disabled")

    # --- LOGIC ---

    def toggle_protocol_ui(self, val):
        if val == "HTTPS":
            self.cert_frame.pack(fill="x", padx=40, pady=10, after=self.p_frame)
            self.validate_certs(silent=True) # Check existing files
            self.ip_link.configure(text="https://127.0.0.1:8000")
        else:
            self.cert_frame.pack_forget()
            self.ip_link.configure(text="http://127.0.0.1:8000")
        
        # Save config immediately
        self.save_all_data()

    def upload_cert(self):
        filename = filedialog.askopenfilename(title="Select Certificate", filetypes=[("PEM Files", "*.pem"), ("All Files", "*.*")])
        if filename:
            try:
                shutil.copy(filename, "cert.pem")
                self.lbl_cert.configure(text="Uploaded ✔", text_color="green")
                messagebox.showinfo("Success", "Certificate uploaded successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload: {e}")

    def upload_key(self):
        filename = filedialog.askopenfilename(title="Select Private Key", filetypes=[("PEM Files", "*.pem"), ("All Files", "*.*")])
        if filename:
            try:
                shutil.copy(filename, "key.pem")
                self.lbl_key.configure(text="Uploaded ✔", text_color="green")
                messagebox.showinfo("Success", "Key uploaded successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload: {e}")

    def validate_certs(self, silent=False):
        has_cert = os.path.exists("cert.pem")
        has_key = os.path.exists("key.pem")

        if has_cert: self.lbl_cert.configure(text="Found ✔", text_color="green")
        else: self.lbl_cert.configure(text="Missing ✘", text_color="red")
        
        if has_key: self.lbl_key.configure(text="Found ✔", text_color="green")
        else: self.lbl_key.configure(text="Missing ✘", text_color="red")

        if has_cert and has_key:
            self.btn_validate.configure(text="Configuration Valid", fg_color="#10B981")
            return True
        else:
            self.btn_validate.configure(text="Validate Certificates", fg_color="#D97706")
            if not silent: messagebox.showwarning("Incomplete", "Please upload both cert.pem and key.pem for HTTPS.")
            return False

    def start_service(self):
        # Validation before start
        if self.protocol_var.get() == "HTTPS":
            if not self.validate_certs(silent=True):
                 messagebox.showerror("Cannot Start", "HTTPS mode requires valid certificates.")
                 return

        self.last_known_status = "SERVICE_RUNNING"
        self.update_ui_state("SERVICE_RUNNING")
        self._run_command_threaded([NSSM_EXE, "start", SERVICE_NAME])

    def stop_service(self):
        self.last_known_status = "SERVICE_STOPPED"
        self.update_ui_state("SERVICE_STOPPED")
        self._run_command_threaded([NSSM_EXE, "stop", SERVICE_NAME])

    def _run_command_threaded(self, command):
        def task():
            subprocess.run(command, creationflags=0x08000000)
        threading.Thread(target=task, daemon=True).start()

    def update_ui_state(self, status):
        is_running = "SERVICE_RUNNING" in status
        new_state = "RUNNING" if is_running else "STOPPED"
        
        if self.current_ui_state == new_state: return 
        self.current_ui_state = new_state

        if is_running:
            self.status_indicator.configure(text="RUNNING...", text_color="#059669")
            self.start_btn.pack_forget()
            self.stop_btn.pack()
            self.protocol_switch.configure(state="disabled")
            self.cert_frame.pack_forget() # Hide settings while running to prevent editing
            if hasattr(self, 'tray_icon') and os.path.exists(CHECK_ICO):
                self.tray_icon.icon = Image.open(CHECK_ICO)
        else:
            self.status_indicator.configure(text="STOPPED...", text_color="#DC2626")
            self.stop_btn.pack_forget()
            self.start_btn.pack()
            self.protocol_switch.configure(state="normal")
            
            # Show cert frame if HTTPS is selected
            if self.protocol_var.get() == "HTTPS":
                 self.cert_frame.pack(fill="x", padx=40, pady=10, after=self.p_frame)

            if hasattr(self, 'tray_icon') and os.path.exists(NO_ICO):
                self.tray_icon.icon = Image.open(NO_ICO)

    def open_endpoint(self, event):
        url = self.ip_link.cget("text")
        webbrowser.open(f"{url}/docs")

    def load_all_data(self):
        # Load Keys
        if os.path.exists(KEYS_FILE):
            try:
                with open(KEYS_FILE, 'r') as f:
                    data = json.load(f)
                    self.entry_key.insert(0, data.get("partner_key", ""))
                    self.entry_secret.insert(0, data.get("partner_secret", ""))
            except: pass
        
        # Load Config
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    proto = data.get("protocol", "http")
                    self.protocol_var.set(proto.upper())
                    self.toggle_protocol_ui(proto.upper())
            except: pass

    def save_all_data(self):
        # Save Keys
        with open(KEYS_FILE, "w") as f: 
            json.dump({"partner_key": self.entry_key.get(), "partner_secret": self.entry_secret.get()}, f, indent=4)
        
        # Save Protocol
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"protocol": self.protocol_var.get().lower()}, f)

    def monitor_service(self):
        while not self.stop_event.is_set():
            try:
                result = subprocess.run([NSSM_EXE, "status", SERVICE_NAME], capture_output=True, text=True, creationflags=0x08000000)
                status = result.stdout.strip()
                if status != self.last_known_status:
                    self.last_known_status = status
                    self.after(0, self.update_ui_state, status)
            except: pass
            time.sleep(0.5)

if __name__ == "__main__":
    app = VMSControllerUI()
    app.mainloop()