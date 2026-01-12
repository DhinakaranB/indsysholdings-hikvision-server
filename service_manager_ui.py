import customtkinter as ctk
import json
import os
import sys
import subprocess
import threading
import time
import webbrowser
from PIL import Image
import pystray
import ctypes
from pystray import MenuItem as item
# Standard Python UI popups
import shutil
import ssl
from tkinter import messagebox, filedialog

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

        # Compact Window Geometry
        self.title("VMS Service Controller")
        self.geometry("750x480") 
        self.resizable(False, False)


        self.iconbitmap(ICON_PATH)
        
        # Outer Window Background
        self.configure(fg_color="#F0F2F5") 

        # Handle Window Close (Minimize to Tray)
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.last_known_status = None
        self.current_ui_state = None # Prevents flickering
        
        # Inner Rounded Container
        self.main_container = ctk.CTkFrame(self, fg_color="#D1D5DB", corner_radius=20)
        self.main_container.pack(padx=25, pady=(15, 5), fill="both", expand=True)

        # Tabview Styling
        self.tabview = ctk.CTkTabview(self.main_container, width=680, height=360, 
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

        # Copyright Footer
        self.footer = ctk.CTkLabel(self, text="© 2025 Copyright by Indsys Holdings", 
                                   text_color="#6B7280", font=ctk.CTkFont(size=12))
        self.footer.pack(side="bottom", pady=8)

        # Initialize Tray and Monitoring
        self.setup_tray_icon()
        self.stop_event = threading.Event()
        threading.Thread(target=self.monitor_service, daemon=True).start()

    # --- TRAY LOGIC ---

    def start_http_from_tray(self, icon, item):
        if hasattr(self, 'protocol_var'): self.protocol_var.set("HTTP")
        self.save_protocol_only("HTTP")
        self.start_service()

    def start_https_from_tray(self, icon, item):
        if hasattr(self, 'protocol_var'): self.protocol_var.set("HTTPS")
        self.save_protocol_only("HTTPS")
        self.start_service()

    def minimize_to_tray(self):
        self.withdraw()

    def get_tray_status_text(self, item):
        # Uses Bold Text Symbols instead of emojis for professional look
        status = self.last_known_status if self.last_known_status else "SERVICE_STOPPED"
        proto = self.protocol_var.get() if hasattr(self, 'protocol_var') else "HTTP"
        if "SERVICE_RUNNING" in status:
            return f"✔  {proto} Service: Running" 
        return f"✘  {proto} Service: Stopped"

    def setup_tray_icon(self):
        if os.path.exists(ICON_PATH):
            taskbar_img = Image.open(ICON_PATH)
        else:
            print(f"Warning: Could not find icon at {ICON_PATH}")
            taskbar_img = Image.new('RGB', (64, 64), color=(0, 0, 0))

        menu = pystray.Menu(
            item(lambda i: self.get_tray_status_text(i), None, enabled=False),
            pystray.Menu.SEPARATOR,
            item('▶ Start HTTP Service', self.start_http_from_tray, enabled=lambda i: not self.is_service_running()),
            item('▶ Start HTTPS Service', self.start_https_from_tray, enabled=lambda i: not self.is_service_running()),
            item('⏹ Stop Service', self.on_tray_stop, enabled=lambda i: self.is_service_running()),
            pystray.Menu.SEPARATOR,
            item('Open Manager', self.show_window, default=True),
            item('Quit', self.quit_app)
        )
        self.tray_icon = pystray.Icon("VMS", taskbar_img, "VMS Controller", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.after(0, self.deiconify)

    def quit_app(self):
        if hasattr(self, 'tray_icon'): self.tray_icon.stop()
        self.stop_event.set()
        self.destroy()
        sys.exit()

    # --- UI SETUP ---

    def setup_integration_keys_tab(self):
        card = ctk.CTkFrame(self.tab_keys, fg_color="#FFFFFF", corner_radius=15)
        card.pack(expand=True, fill="both", padx=20, pady=15)
        ctk.CTkLabel(card, text="Integration Credentials", text_color="#1F2937", 
                      font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15, 20))
        self.entry_key = self.create_input_row(card, "Partner Key")
        self.entry_secret = self.create_input_row(card, "Partner Secret", True)
        self.save_btn = ctk.CTkButton(card, text="Sign in", fg_color="#3498DB", 
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
        # 1. Main Card: Compact padding
        card = ctk.CTkFrame(self.tab_control, fg_color="#FFFFFF", corner_radius=15)
        card.pack(expand=True, fill="both", padx=20, pady=5)

        # --- Header ---
        header = ctk.CTkFrame(card, fg_color="#DBEAFE", height=40, corner_radius=10)
        header.pack(fill="x", padx=15, pady=(5, 5)) # Reduced top gap
        header.columnconfigure(0, weight=2); header.columnconfigure(1, weight=2); header.columnconfigure(2, weight=1)
        ctk.CTkLabel(header, text="SERVICE NAME", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1E40AF").grid(row=0, column=0, pady=8, sticky="w", padx=25)
        ctk.CTkLabel(header, text="IP / PORT", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1E40AF").grid(row=0, column=1, pady=8)
        ctk.CTkLabel(header, text="STATUS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1E40AF").grid(row=0, column=2, pady=8, sticky="e", padx=25)
        
        # --- Info Row ---
        row = ctk.CTkFrame(card, fg_color="#F3F4F6", corner_radius=10)
        row.pack(fill="x", padx=15, pady=5)
        row.columnconfigure(0, weight=2); row.columnconfigure(1, weight=2); row.columnconfigure(2, weight=1)
        ctk.CTkLabel(row, text="VMS API Service", text_color="#111827", font=ctk.CTkFont(size=13)).grid(row=0, column=0, pady=10, sticky="w", padx=25)
        self.ip_link = ctk.CTkLabel(row, text="http://127.0.0.1:8000", text_color="#3498DB", font=ctk.CTkFont(size=14, underline=True), cursor="hand2")
        self.ip_link.grid(row=0, column=1, pady=10)
        self.ip_link.bind("<Button-1>", self.open_endpoint)
        self.status_indicator = ctk.CTkLabel(row, text="STOPPED...", text_color="#DC2626", font=ctk.CTkFont(size=13, weight="bold"))
        self.status_indicator.grid(row=0, column=2, pady=10, sticky="e", padx=25)

        # --- HTTPS File Upload Area (Hidden by default) ---
        self.ssl_frame = ctk.CTkFrame(card, fg_color="transparent")
        
        # 1. INSTRUCTION LABEL (Compact)
        self.lbl_instruction = ctk.CTkLabel(self.ssl_frame, text="Please upload certificate from your system:", 
                                            text_color="#374151", font=("Arial", 12, "bold"))
        self.lbl_instruction.grid(row=0, column=0, columnspan=3, pady=(0, 2), sticky="w", padx=10) # Changed pady to 2

        # 2. Certificate Row
        self.cert_path = None
        self.btn_cert = ctk.CTkButton(self.ssl_frame, text="Certificate File", width=140, fg_color="#6B7280", command=self.select_cert)
        self.btn_cert.grid(row=1, column=0, padx=10, pady=2) # Changed pady from 5 to 2
        self.lbl_cert = ctk.CTkLabel(self.ssl_frame, text="No file selected", text_color="gray", font=("Arial", 11))
        self.lbl_cert.grid(row=1, column=1, padx=10, sticky="w")
        self.btn_clear_cert = ctk.CTkButton(self.ssl_frame, text="X", width=30, fg_color="#EF4444", hover_color="#DC2626", command=self.clear_cert)
        self.btn_clear_cert.grid(row=1, column=2, padx=5)
        self.btn_clear_cert.grid_remove() 

        # 3. Key Row
        self.key_path = None
        self.btn_key = ctk.CTkButton(self.ssl_frame, text="Key File", width=140, fg_color="#6B7280", command=self.select_key)
        self.btn_key.grid(row=2, column=0, padx=10, pady=2) # Changed pady from 5 to 2
        self.lbl_key = ctk.CTkLabel(self.ssl_frame, text="No file selected", text_color="gray", font=("Arial", 11))
        self.lbl_key.grid(row=2, column=1, padx=10, sticky="w")
        self.btn_clear_key = ctk.CTkButton(self.ssl_frame, text="X", width=30, fg_color="#EF4444", hover_color="#DC2626", command=self.clear_key)
        self.btn_clear_key.grid(row=2, column=2, padx=5)
        self.btn_clear_key.grid_remove() 
        
        # 4. VALIDATION ICON (Compact)
        self.lbl_validation = ctk.CTkLabel(self.ssl_frame, text="✔ Certificate Validated", text_color="#10B981", font=("Arial", 14, "bold"))
        self.lbl_validation.grid(row=3, column=0, columnspan=3, pady=2) # Changed pady from 10 to 2
        self.lbl_validation.grid_remove()

        # --- Protocol Switch ---
        self.p_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.p_frame.pack(pady=5) # Minimal padding
        
        self.protocol_var = ctk.StringVar(value="HTTP")
        self.protocol_switch = ctk.CTkSegmentedButton(self.p_frame, values=["HTTP", "HTTPS"], 
                                                      variable=self.protocol_var, 
                                                      command=self.toggle_https_ui)
        self.protocol_switch.pack()

        # --- Start/Stop Buttons ---
        self.btn_container = ctk.CTkFrame(card, fg_color="transparent")
        self.btn_container.pack(pady=(5, 10)) # Reduced top to 5, bottom to 10
        
        self.start_btn = ctk.CTkButton(self.btn_container, text="START", fg_color="#10B981", 
                                       hover_color="#059669", width=120, height=32, corner_radius=20,
                                       command=self.validate_and_start)
        
        self.stop_btn = ctk.CTkButton(self.btn_container, text="STOP", fg_color="#EF4444", 
                                      hover_color="#DC2626", width=120, height=32, corner_radius=20,
                                      command=self.stop_service)
        
    def toggle_https_ui(self, val):
        self.save_protocol_only(val)
        if val == "HTTPS":
            self.ssl_frame.pack(after=self.p_frame, pady=10)
        else:
            self.ssl_frame.pack_forget()
        
        # Reset validation status when toggling
        self.lbl_validation.grid_remove()
        
    def select_cert(self):
        filename = filedialog.askopenfilename(filetypes=[("Certificate", "*.pem *.crt")])
        if filename:
            self.cert_path = filename
            self.lbl_cert.configure(text=os.path.basename(filename), text_color="black")
            # Show the X button
            self.btn_clear_cert.grid()
    
    def clear_cert(self):
        self.cert_path = None
        self.lbl_cert.configure(text="No file selected", text_color="gray")
        self.btn_clear_cert.grid_remove()
        self.lbl_validation.grid_remove() # Hide tick
    
    def select_key(self):
        filename = filedialog.askopenfilename(filetypes=[("Private Key", "*.pem *.key")])
        if filename:
            self.key_path = filename
            self.lbl_key.configure(text=os.path.basename(filename), text_color="black")
            # Show the X button
            self.btn_clear_key.grid()
    
    def clear_key(self):
        self.key_path = None
        self.lbl_key.configure(text="No file selected", text_color="gray")
        self.btn_clear_key.grid_remove()
        self.lbl_validation.grid_remove() # Hide tick

    def validate_and_start(self):
        """Validates Certs if HTTPS is selected, then starts."""
        mode = self.protocol_var.get()

        if mode == "HTTPS":
            # Hide tick initially in case they are re-trying
            self.lbl_validation.grid_remove()
            
            base_dir = os.getcwd() 
            dest_cert = os.path.join(base_dir, "cert.pem")
            dest_key = os.path.join(base_dir, "key.pem")

            # 1. Check if files are selected
            if not self.cert_path or not self.key_path:
                if os.path.exists(dest_cert) and os.path.exists(dest_key):
                     self.cert_path = dest_cert
                     self.key_path = dest_key
                else:
                    messagebox.showerror("Error", "Please upload both Certificate and Key files.")
                    return

            # 2. Validate using SSL Library
            try:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=self.cert_path, keyfile=self.key_path)
                
                # --- SHOW SUCCESS TICK ICON HERE ---
                self.lbl_validation.grid() 
                self.update_idletasks() # Force the UI to refresh immediately
                time.sleep(0.8) # Wait 0.8 seconds so user sees the tick!
                # -----------------------------------
                
                # 3. Copy files (Fixing SameFileError)
                if os.path.abspath(self.cert_path) != os.path.abspath(dest_cert):
                    shutil.copy(self.cert_path, dest_cert)
                if os.path.abspath(self.key_path) != os.path.abspath(dest_key):
                    shutil.copy(self.key_path, dest_key)

            except ssl.SSLError as e:
                messagebox.showerror("Validation Failed", f"Invalid Certificate/Key pair:\n{e}")
                return
            except Exception as e:
                if "same file" not in str(e).lower():
                    messagebox.showerror("Error", f"Could not load files:\n{e}")
                    return

        self.start_service()
        
    def open_endpoint(self, event):
        url = self.ip_link.cget("text")
        webbrowser.open(f"{url}/docs")

    def is_service_running(self):
        return self.last_known_status and "SERVICE_RUNNING" in self.last_known_status

    def on_tray_stop(self, icon, item):
        self.stop_service()
        
    def setup_version_log_tab(self):
        card = ctk.CTkFrame(self.tab_log, fg_color="#FFFFFF", corner_radius=15)
        card.pack(expand=True, fill="both", padx=20, pady=15)
        ctk.CTkLabel(card, text="VMS Controller Pro", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        log_box = ctk.CTkTextbox(card, width=580, height=140, fg_color="#F9FAFB", border_width=1)
        log_box.pack(pady=5)
        log_box.insert("0.0", "• [RELEASE] Final Client Demo Build\n• [UI] Fixed Alignment & Flickering\n• [PERF] Background Threading for Start/Stop")
        log_box.configure(state="disabled")

    # --- LOGIC & THREADING ---

    def save_protocol_only(self, val):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"protocol": val.lower()}, f)
        self.ip_link.configure(text=f"{val.lower()}://127.0.0.1:8000")

    def monitor_service(self):
        """Background Loop."""
        while not self.stop_event.is_set():
            try:
                result = subprocess.run([NSSM_EXE, "status", SERVICE_NAME], capture_output=True, text=True, creationflags=0x08000000)
                status = result.stdout.strip()
                if status != self.last_known_status:
                    self.last_known_status = status
                    self.after(0, self.update_ui_state, status)
            except: pass
            time.sleep(0.5)

    # def update_ui_state(self, status):
    #     """Updates UI only if state actually changed (Fixes Flickering)."""
    #     is_running = "SERVICE_RUNNING" in status
        
    #     # Determine desired state
    #     new_state = "RUNNING" if is_running else "STOPPED"
        
    #     # FIX: Only redraw if state is different from current UI
    #     if self.current_ui_state == new_state:
    #         return 
        
    #     self.current_ui_state = new_state

    #     if is_running:
    #         self.status_indicator.configure(text="RUNNING...", text_color="#059669")
    #         self.start_btn.pack_forget()
    #         self.stop_btn.pack()
    #         self.protocol_switch.configure(state="disabled")

    #     else:
    #         self.status_indicator.configure(text="STOPPED...", text_color="#DC2626")
    #         self.stop_btn.pack_forget()
    #         self.start_btn.pack()
    #         self.protocol_switch.configure(state="normal")

    def update_ui_state(self, status):
        """Updates UI only if state actually changed (Fixes Flickering)."""
        is_running = "SERVICE_RUNNING" in status
        
        # Determine desired state
        new_state = "RUNNING" if is_running else "STOPPED"
        
        # FIX: Only redraw if state is different from current UI
        if self.current_ui_state == new_state:
            return 
        
        self.current_ui_state = new_state

        if is_running:
            self.status_indicator.configure(text="RUNNING...", text_color="#059669")
            self.start_btn.pack_forget()
            self.stop_btn.pack()
            self.protocol_switch.configure(state="disabled") # Lock protocol switch
            
            # --- NEW: HIDE 'X' BUTTONS WHILE RUNNING ---
            self.btn_clear_cert.grid_remove()
            self.btn_clear_key.grid_remove()
            # -------------------------------------------

            if hasattr(self, 'tray_icon') and os.path.exists(CHECK_ICO):
                try: self.tray_icon.icon = Image.open(CHECK_ICO)
                except: pass

        else:
            self.status_indicator.configure(text="STOPPED...", text_color="#DC2626")
            self.stop_btn.pack_forget()
            self.start_btn.pack()
            self.protocol_switch.configure(state="normal")
            
            # --- NEW: RESTORE 'X' BUTTONS IF FILES EXIST ---
            # We only show the X if a file is actually currently selected
            if self.cert_path:
                self.btn_clear_cert.grid()
            if self.key_path:
                self.btn_clear_key.grid()
            # -----------------------------------------------

            if hasattr(self, 'tray_icon') and os.path.exists(NO_ICO):
                try: self.tray_icon.icon = Image.open(NO_ICO)
                except: pass

    def load_all_data(self):
        if os.path.exists(KEYS_FILE):
            with open(KEYS_FILE, 'r') as f:
                data = json.load(f); self.entry_key.insert(0, data.get("partner_key", "")); self.entry_secret.insert(0, data.get("partner_secret", ""))
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                proto = json.load(f).get("protocol", "http"); self.protocol_var.set(proto.upper())
                self.ip_link.configure(text=f"{proto.lower()}://127.0.0.1:8000")

    def save_all_data(self):
        with open(KEYS_FILE, "w") as f: json.dump({"partner_key": self.entry_key.get(), "partner_secret": self.entry_secret.get()}, f, indent=4)
        self.save_protocol_only(self.protocol_var.get())

    # --- FIX: THREADED START/STOP TO PREVENT HANGING ---

    def _run_command_threaded(self, command):
        """Runs subprocess in background so UI doesn't freeze."""
        def task():
            subprocess.run(command, creationflags=0x08000000)
        threading.Thread(target=task, daemon=True).start()

    def start_service(self):
        # 1. Instant Visual Feedback
        self.last_known_status = "SERVICE_RUNNING"
        self.update_ui_state("SERVICE_RUNNING")
        # 2. Run actual command in background
        self._run_command_threaded([NSSM_EXE, "start", SERVICE_NAME])

    def stop_service(self):
        # 1. Instant Visual Feedback
        self.last_known_status = "SERVICE_STOPPED"
        self.update_ui_state("SERVICE_STOPPED")
        # 2. Run actual command in background
        self._run_command_threaded([NSSM_EXE, "stop", SERVICE_NAME])

if __name__ == "__main__":

    myappid = 'indsys.vms.controller.1.0' 
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
    
    app = VMSControllerUI()
    app.mainloop()