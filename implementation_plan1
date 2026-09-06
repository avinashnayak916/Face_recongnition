# Step 3: Biometric Face Attendance GUI (`app.py`)

Our goal for Step 3 is to integrate the backend modules (`db_manager.py` and `model_trainer.py`) into a fully functional, production-grade desktop application using `customtkinter`. 

The application will feature a dark-mode theme, a real-time Kiosk interface for logging attendance, and a protected Admin Dashboard for managing users, training the AI, and exporting data.

## User Review Required

Please review the proposed architecture and threading strategy below. If you agree with this plan, click **"Proceed"** so we can write and execute `app.py`.

> [!IMPORTANT]  
> Tkinter GUIs freeze if long tasks (like Model Training or a `while True` camera loop) run on the main thread. To prevent this, we will use Tkinter's `.after()` method for the Kiosk live feed, and `threading.Thread` for the User Enrollment/Training process.

## Open Questions

1. **CSV Export Name**: By default, I will configure the "Export to CSV" button to save as `Attendance_YYYY-MM-DD.csv`. Does this sound good?
2. **Camera Resource**: When an Admin is registering a new user, `model_trainer.py` opens its own temporary OpenCV window. I will ensure the main Kiosk camera feed is explicitly stopped and released before training begins so the webcam isn't locked by two processes.

## Proposed Changes

### [NEW] `app.py`

We will create a massive object-oriented application structure: `class FaceAttendanceApp(ctk.CTk)`

#### 1. Core State Management
- `self.mode`: Tracks if we are in `"KIOSK"` or `"ADMIN"` mode.
- `self.recognizer`: The LBPH model loaded from `models/trained_model.yml` (if it exists).
- `self.cap`: The global `cv2.VideoCapture(0)` object.

#### 2. Kiosk Mode UI
- **Left Frame**: A large `CTkLabel` where we will pipe the OpenCV frames using `PIL.ImageTk.PhotoImage`.
- **Right Frame**: 
  - **KPI Cards**: 4 blocks showing Total Users, Present, Absent, and Percentage.
  - **Punch Stream**: A scrollable `CTkTextbox` or `CTkScrollableFrame` showing the live logs (e.g., `10:15 AM - Rahul (EMP01)`).
  - **Admin Login Button**: Triggers the modal popup.

#### 3. Real-Time Recognition Loop
- We will use `self.after(15, self.update_camera)` to loop the feed at ~60FPS.
- It will convert frames to grayscale, detect faces, predict using LBPH, check if `confidence < 70`, and call `db_manager.mark_attendance()`.
- If attendance is newly marked, it will flash a UI banner and refresh the KPI cards.

#### 4. Admin Dashboard UI
- **Login Modal**: A `CTkToplevel` window asking for credentials, checked against `db_manager.verify_admin()`.
- **Tabview (`ctk.CTkTabview`)**:
  - **Tab 1 (Enrollment)**: Entries for ID/Name, and a "Capture & Train" button. It will spawn a background thread to call `capture_face_samples()` and `train_custom_model()` without freezing the GUI.
  - **Tab 2 (Records)**: A display of `db_manager.get_all_users()` and `db_manager.get_today_attendance()`, plus the CSV Export button.

## Verification Plan

### Manual Verification
1. Run `python app.py` to launch the GUI.
2. Verify the Kiosk mode shows the live camera feed and live stats.
3. Click Admin Login, test bad credentials, then test `admin / admin123`.
4. Register a new user in the Admin Dashboard and verify the model retrains.
5. Log out of Admin mode, step in front of the camera, and verify attendance is marked on the screen.
6. Export the CSV and verify the file contents.
