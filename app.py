import customtkinter as ctk
import cv2
import os
import threading
import time
import csv
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import db_manager as db
import model_trainer as mt
from datetime import datetime

def parse_and_standardize_date(date_str):
    cleaned = date_str.strip()
    # Supported input variations
    allowed_formats = [
        '%Y-%m-%d',       # e.g. 2026-01-24
        '%d-%m-%Y',       # e.g. 24-01-2026
        '%d/%m/%Y',       # e.g. 24/01/2026
        '%d %b %Y',       # e.g. 24 Jan 2026
        '%d %B %Y',       # e.g. 24 January 2026
        '%d-%b-%Y',       # e.g. 24-Jan-2026
    ]
    for fmt in allowed_formats:
        try:
            parsed_dt = datetime.strptime(cleaned, fmt)
            # Normalize and return standard storage format
            return True, parsed_dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return False, None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FaceAttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Biometric Face Attendance & Management System")
        self.geometry("1100x720")
        self.minsize(1100, 720)
        
        # Application State
        self.mode = "KIOSK"
        self.cap = None
        self.camera_running = False
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.model_loaded = False
        self.is_admin_logged_in = False
        
        # Load Model
        self.load_model()
        
        # Set up UI
        self.setup_ui()
        
        # Handle Window Close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def load_model(self):
        if os.path.exists("models/trained_model.yml"):
            try:
                self.recognizer.read("models/trained_model.yml")
                self.model_loaded = True
            except Exception as e:
                print("Error loading model:", e)
                self.model_loaded = False
        else:
            self.model_loaded = False

    def setup_ui(self):
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()
            
        if self.mode == "KIOSK":
            self.setup_kiosk_ui()
            # Camera does not start automatically anymore
        else:
            self.setup_admin_ui()
            
    # ================== KIOSK MODE ==================
    def setup_kiosk_ui(self):
        # Left Panel (Camera)
        self.left_frame = ctk.CTkFrame(self, width=640, corner_radius=10)
        self.left_frame.pack(side="left", fill="y", padx=20, pady=20)
        
        self.video_label = ctk.CTkLabel(self.left_frame, text="Camera is Off - Click Start to Punch", width=640, height=480)
        self.video_label.pack(pady=(20, 10), padx=20)
        
        # Camera Controls
        self.cam_controls = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.cam_controls.pack(pady=5)
        
        self.start_btn = ctk.CTkButton(self.cam_controls, text="Start Attendance / Scan", command=self.start_camera, fg_color="green", hover_color="darkgreen")
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(self.cam_controls, text="Stop Camera", command=self.stop_camera, fg_color="red", hover_color="darkred")
        self.stop_btn.pack(side="left", padx=10)
        
        self.banner_label = ctk.CTkLabel(self.left_frame, text="", text_color="green", font=ctk.CTkFont(size=24, weight="bold"))
        self.banner_label.pack(pady=10)
        
        self.admin_btn = ctk.CTkButton(self.left_frame, text="Admin Login", command=self.open_admin_login)
        self.admin_btn.pack(side="bottom", pady=20)

        # Right Panel (Stats & Log)
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(0, 20), pady=20)
        
        # KPI Cards
        self.kpi_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=10, padx=10)
        
        self.total_label = ctk.CTkLabel(self.kpi_frame, text="Total Users: 0", font=ctk.CTkFont(size=16))
        self.total_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.present_label = ctk.CTkLabel(self.kpi_frame, text="Present Today: 0", font=ctk.CTkFont(size=16), text_color="green")
        self.present_label.grid(row=0, column=1, padx=10, pady=10)
        
        self.absent_label = ctk.CTkLabel(self.kpi_frame, text="Absent Today: 0", font=ctk.CTkFont(size=16), text_color="red")
        self.absent_label.grid(row=1, column=0, padx=10, pady=10)
        
        self.pct_label = ctk.CTkLabel(self.kpi_frame, text="Attendance: 0%", font=ctk.CTkFont(size=16, weight="bold"))
        self.pct_label.grid(row=1, column=1, padx=10, pady=10)
        
        # Live Log
        ctk.CTkLabel(self.right_frame, text="Today's Live Punch Log", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        self.log_textbox = ctk.CTkTextbox(self.right_frame, width=300, height=400, state="disabled")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.refresh_kpi_and_log()
        
    def refresh_kpi_and_log(self):
        stats = db.get_daily_attendance_stats()
        self.total_label.configure(text=f"Total Users: {stats['total']}")
        self.present_label.configure(text=f"Present Today: {stats['present']}")
        self.absent_label.configure(text=f"Absent Today: {stats['absent']}")
        self.pct_label.configure(text=f"Attendance: {stats['percentage']}%")
        
        records = db.get_today_attendance()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        for rec in records:
            self.log_textbox.insert("end", f"[{rec[2]} {rec[3]}] ✅ {rec[1]} ({rec[0]})\n")
        self.log_textbox.configure(state="disabled")

    def start_camera(self):
        if not self.camera_running:
            self.cap = cv2.VideoCapture(0)
            self.camera_running = True
            self.banner_label.configure(text="")
            self.update_camera()
        
    def update_camera(self):
        if not self.camera_running or self.mode != "KIOSK":
            return
            
        ret, frame = self.cap.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = mt.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
            
            face_verified = False
            
            for (x, y, w, h) in faces:
                if self.model_loaded:
                    face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                    id_, confidence = self.recognizer.predict(face_roi)
                    
                    if confidence < 70:
                        user_info = db.get_user_by_id(id_)
                        if user_info:
                            user_code, name = user_info
                            success, timestamp = db.mark_attendance(user_code, name)
                            
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(frame, f"{name} ({user_code}) - Conf: {round(100 - confidence)}%", 
                                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            
                            if success:
                                self.banner_label.configure(text=f"Attendance Marked: {name} at {timestamp}")
                            else:
                                self.banner_label.configure(text=f"Verified: {name} (Already Marked)")
                                
                            self.refresh_kpi_and_log()
                            face_verified = True
                            break # Process only the verified face and stop
                    else:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                        cv2.putText(frame, "Unknown Face", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    cv2.putText(frame, "No Model Loaded", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            # Convert for Tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            
            self.video_label.imgtk = ctk_img
            self.video_label.configure(image=ctk_img, text="")
            
            if face_verified:
                # Stop loop, hold frame for 1.5s, then release camera
                self.camera_running = False
                self.after(1500, self.release_camera_and_reset)
                return

        self.after(15, self.update_camera)

    def stop_camera(self):
        self.camera_running = False
        self.release_camera_and_reset()
        
    def release_camera_and_reset(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.mode == "KIOSK":
            self.video_label.configure(image="", text="Camera is Off - Click Start to Punch")
            self.banner_label.configure(text="")

    def open_admin_login(self):
        if self.is_admin_logged_in:
            self.stop_camera()
            self.mode = "ADMIN"
            self.setup_ui()
            return
            
        dialog = ctk.CTkToplevel(self)
        dialog.title("Admin Login")
        dialog.geometry("300x250")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Username").pack(pady=(20, 5))
        user_entry = ctk.CTkEntry(dialog)
        user_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Password").pack(pady=5)
        pass_entry = ctk.CTkEntry(dialog, show="*")
        pass_entry.pack(pady=5)
        
        def attempt_login():
            if db.verify_admin(user_entry.get(), pass_entry.get()):
                self.is_admin_logged_in = True
                dialog.destroy()
                self.stop_camera()
                self.mode = "ADMIN"
                self.setup_ui()
            else:
                messagebox.showerror("Error", "Invalid Credentials")
                
        ctk.CTkButton(dialog, text="Login", command=attempt_login).pack(pady=20)

    # ================== ADMIN DASHBOARD ==================
    def setup_admin_ui(self):
        header_frame = ctk.CTkFrame(self, height=60, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(header_frame, text="Admin Dashboard", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ctk.CTkButton(btn_frame, text="Back to Kiosk", command=lambda: self.go_kiosk(do_logout=False)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Logout", command=lambda: self.go_kiosk(do_logout=True), fg_color="red", hover_color="darkred").pack(side="left", padx=5)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tabview.add("User Enrollment & Model Training")
        self.tabview.add("Attendance Records & Export")
        self.tabview.add("User Attendance Reports")
        
        self.setup_tab_enrollment()
        self.setup_tab_records()
        self.setup_tab_reports()

    def go_kiosk(self, do_logout=False):
        if do_logout:
            self.is_admin_logged_in = False
        self.mode = "KIOSK"
        self.load_model()
        self.setup_ui()

    def setup_tab_enrollment(self):
        tab = self.tabview.tab("User Enrollment & Model Training")
        
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(input_frame, text="Employee/Student ID:").grid(row=0, column=0, padx=5, pady=10)
        self.emp_id_entry = ctk.CTkEntry(input_frame, width=120)
        self.emp_id_entry.grid(row=0, column=1, padx=5, pady=10)
        
        ctk.CTkLabel(input_frame, text="Full Name:").grid(row=0, column=2, padx=5, pady=10)
        self.emp_name_entry = ctk.CTkEntry(input_frame, width=120)
        self.emp_name_entry.grid(row=0, column=3, padx=5, pady=10)
        
        ctk.CTkLabel(input_frame, text="Reg. Date (e.g., 2026-01-24, 24-01-2026, 24 Jan 2026):").grid(row=0, column=4, padx=5, pady=10)
        self.reg_date_entry = ctk.CTkEntry(input_frame, width=100)
        self.reg_date_entry.grid(row=0, column=5, padx=5, pady=10)
        self.reg_date_entry.insert(0, time.strftime('%Y-%m-%d'))
        
        self.train_btn = ctk.CTkButton(input_frame, text="Capture Face & Auto-Train", command=self.start_enrollment)
        self.train_btn.grid(row=0, column=6, padx=5, pady=10)
        
        self.update_btn = ctk.CTkButton(input_frame, text="Update Details", command=self.update_user_details, state="disabled", fg_color="orange", hover_color="darkorange")
        self.update_btn.grid(row=0, column=7, padx=5, pady=10)
        
        self.clear_btn = ctk.CTkButton(input_frame, text="Clear Selection", command=self.clear_selection, fg_color="gray", width=100)
        self.clear_btn.grid(row=0, column=8, padx=5, pady=10)
        
        self.status_label = ctk.CTkLabel(tab, text="", text_color="yellow")
        self.status_label.pack(pady=5)
        
        ctk.CTkLabel(tab, text="Registered Users", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 5))
        self.users_textbox = ctk.CTkTextbox(tab, height=300, state="disabled")
        self.users_textbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.users_textbox.bind("<ButtonRelease-1>", self.on_user_select)
        self.selected_user_id = None
        
        self.refresh_users_table()

    def clear_selection(self):
        self.selected_user_id = None
        self.emp_id_entry.delete(0, 'end')
        self.emp_name_entry.delete(0, 'end')
        self.reg_date_entry.delete(0, 'end')
        self.reg_date_entry.insert(0, time.strftime('%Y-%m-%d'))
        self.status_label.configure(text="")
        self.train_btn.configure(state="normal")
        self.update_btn.configure(state="disabled")

    def on_user_select(self, event):
        try:
            index = self.users_textbox.index(f"@{event.x},{event.y}")
            line_index = index.split(".")[0]
            line_text = self.users_textbox.get(f"{line_index}.0", f"{line_index}.end").strip()
            
            if "|" in line_text and not line_text.startswith("Numeric ID") and not line_text.startswith("---"):
                parts = [p.strip() for p in line_text.split("|")]
                self.selected_user_id = int(parts[0])
                
                self.emp_id_entry.delete(0, 'end')
                self.emp_id_entry.insert(0, parts[1])
                
                self.emp_name_entry.delete(0, 'end')
                self.emp_name_entry.insert(0, parts[2])
                
                self.reg_date_entry.delete(0, 'end')
                self.reg_date_entry.insert(0, parts[3])
                
                self.status_label.configure(text=f"Selected: {parts[2]} (ID: {parts[0]})", text_color="cyan")
                self.train_btn.configure(state="disabled")
                self.update_btn.configure(state="normal")
        except Exception:
            pass

    def update_user_details(self):
        if not self.selected_user_id:
            return
            
        code = self.emp_id_entry.get().strip()
        name = self.emp_name_entry.get().strip()
        reg_date = self.reg_date_entry.get().strip()
        if not code or not name:
            messagebox.showerror("Error", "Please enter ID and Name")
            return
            
        if reg_date:
            is_valid, standard_date = parse_and_standardize_date(reg_date)
            if not is_valid:
                messagebox.showerror("Error", "Invalid Date! Please use formats like: YYYY-MM-DD, DD-MM-YYYY, or DD Mon YYYY (e.g., 24 Jan 2026).")
                return
            reg_date = standard_date
            
        success, msg = db.update_user(self.selected_user_id, code, name, reg_date)
        if success:
            self.status_label.configure(text="User updated successfully!", text_color="green")
            self.refresh_users_table()
            self.refresh_records_table()
            self.after(2000, self.clear_selection)
        else:
            messagebox.showerror("Error", msg)

    def start_enrollment(self):
        code = self.emp_id_entry.get().strip()
        name = self.emp_name_entry.get().strip()
        reg_date = self.reg_date_entry.get().strip()
        if not code or not name:
            messagebox.showerror("Error", "Please enter ID and Name")
            return
            
        if reg_date:
            is_valid, standard_date = parse_and_standardize_date(reg_date)
            if not is_valid:
                messagebox.showerror("Error", "Invalid Date! Please use formats like: YYYY-MM-DD, DD-MM-YYYY, or DD Mon YYYY (e.g., 24 Jan 2026).")
                return
            reg_date = standard_date
            
        self.train_btn.configure(state="disabled")
        self.status_label.configure(text="Processing...")
        threading.Thread(target=self.enrollment_thread, args=(code, name, reg_date), daemon=True).start()

    def enrollment_thread(self, code, name, reg_date):
        numeric_id = db.add_user(code, name, reg_date)
        if numeric_id == -1:
            self.after(0, lambda: messagebox.showerror("Error", "User Code already exists!"))
            self.after(0, lambda: self.train_btn.configure(state="normal"))
            self.after(0, lambda: self.status_label.configure(text=""))
            return
            
        self.after(0, lambda: self.status_label.configure(text=f"Capturing faces for {name}... Please look at the webcam."))
        
        success = mt.capture_face_samples(numeric_id, num_samples=40)
        if not success:
            self.after(0, lambda: messagebox.showerror("Error", "Face capture failed."))
            self.after(0, lambda: self.train_btn.configure(state="normal"))
            return
            
        self.after(0, lambda: self.status_label.configure(text="Training AI Model... Please wait."))
        
        success, msg = mt.train_custom_model()
        self.after(0, lambda: self.finish_enrollment(success, msg))

    def finish_enrollment(self, success, msg):
        self.train_btn.configure(state="normal")
        self.status_label.configure(text="")
        if success:
            messagebox.showinfo("Success", msg)
            self.emp_id_entry.delete(0, 'end')
            self.emp_name_entry.delete(0, 'end')
            self.refresh_users_table()
        else:
            messagebox.showerror("Error", msg)

    def refresh_users_table(self):
        users = db.get_all_users()
        self.users_textbox.configure(state="normal")
        self.users_textbox.delete("1.0", "end")
        self.users_textbox.insert("end", f"{'Numeric ID':<10} | {'User Code':<15} | {'Full Name':<20} | {'Registered Date'}\n")
        self.users_textbox.insert("end", "-"*70 + "\n")
        for u in users:
            self.users_textbox.insert("end", f"{u[0]:<10} | {u[1]:<15} | {u[2]:<20} | {u[3]}\n")
        self.users_textbox.configure(state="disabled")

    def setup_tab_records(self):
        tab = self.tabview.tab("Attendance Records & Export")
        
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(top_frame, text="Today's Attendance Records", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(top_frame, text="Export to CSV", command=self.export_csv).pack(side="right")
        
        self.records_textbox = ctk.CTkTextbox(tab, height=400, state="disabled")
        self.records_textbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.refresh_records_table()

    def refresh_records_table(self):
        records = db.get_today_attendance()
        self.records_textbox.configure(state="normal")
        self.records_textbox.delete("1.0", "end")
        self.records_textbox.insert("end", f"{'User Code':<15} | {'Name':<20} | {'Date':<12} | {'Time'}\n")
        self.records_textbox.insert("end", "-"*65 + "\n")
        for r in records:
            self.records_textbox.insert("end", f"{r[0]:<15} | {r[1]:<20} | {r[2]:<12} | {r[3]}\n")
        self.records_textbox.configure(state="disabled")

    def export_csv(self):
        records = db.get_today_attendance()
        if not records:
            messagebox.showinfo("Info", "No attendance records to export for today.")
            return
            
        today = time.strftime("%Y-%m-%d")
        default_filename = f"Attendance_{today}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            threading.Thread(target=self.csv_export_thread, args=(file_path, records), daemon=True).start()
            
    def csv_export_thread(self, file_path, records):
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["User Code", "Name", "Date", "Time"])
                writer.writerows(records)
            self.after(0, lambda: messagebox.showinfo("Success", f"Data exported to {file_path}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to export: {e}"))

    def setup_tab_reports(self):
        tab = self.tabview.tab("User Attendance Reports")
        
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(top_frame, text="Individual Attendance Summary", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(top_frame, text="Export Summary to CSV", command=self.export_reports_csv).pack(side="right")
        
        self.reports_textbox = ctk.CTkTextbox(tab, height=400, state="disabled")
        self.reports_textbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.refresh_reports_table()

    def refresh_reports_table(self):
        summary = db.get_user_attendance_summary()
        self.reports_textbox.configure(state="normal")
        self.reports_textbox.delete("1.0", "end")
        self.reports_textbox.insert("end", f"{'User Code':<15} | {'Name':<20} | {'Total Days':<12} | {'Present':<10} | {'Absent':<10} | {'Attendance %'}\n")
        self.reports_textbox.insert("end", "-"*95 + "\n")
        for s in summary:
            self.reports_textbox.insert("end", f"{s['user_code']:<15} | {s['name']:<20} | {s['total_days']:<12} | {s['present']:<10} | {s['absent']:<10} | {s['percentage']}\n")
        self.reports_textbox.configure(state="disabled")

    def export_reports_csv(self):
        summary = db.get_user_attendance_summary()
        if not summary:
            messagebox.showinfo("Info", "No data to export.")
            return
            
        today = time.strftime("%Y-%m-%d")
        default_filename = f"User_Attendance_Summary_{today}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            threading.Thread(target=self.csv_export_reports_thread, args=(file_path, summary), daemon=True).start()
            
    def csv_export_reports_thread(self, file_path, summary):
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["User Code", "Name", "Total Days", "Present", "Absent", "Attendance %"])
                for s in summary:
                    writer.writerow([s['user_code'], s['name'], s['total_days'], s['present'], s['absent'], s['percentage']])
            self.after(0, lambda: messagebox.showinfo("Success", f"Summary exported to {file_path}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to export: {e}"))

    def on_closing(self):
        self.stop_camera()
        self.destroy()

if __name__ == "__main__":
    app = FaceAttendanceApp()
    app.mainloop()
