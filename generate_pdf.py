from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Biometric Face Attendance & Management System', border=False, align='C')
        self.ln(10)
        self.set_font('helvetica', 'I', 12)
        self.cell(0, 10, 'Final Plan & Workflow Documentation', border=False, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, border=False, align='L', fill=True)
        self.ln(12)

    def chapter_body(self, text):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 8, text)
        self.ln(10)

pdf = PDF()
pdf.add_page()

pdf.chapter_title('1. Project Overview')
text_overview = (
    "This project is a Biometric Face Attendance System built using Python, OpenCV, and CustomTkinter. "
    "It provides a completely automated way to mark attendance by recognizing the faces of registered users. "
    "The application is divided into two primary modes: a 'Kiosk Mode' for users to mark attendance, and an "
    "'Admin Dashboard' for user management, dataset collection, model training, and reporting."
)
pdf.chapter_body(text_overview)

pdf.chapter_title('2. System Architecture & Components')
text_arch = (
    "The system consists of the following core components:\n"
    "- UI Module (app.py): Provides the Graphical User Interface using CustomTkinter with Dark Mode support.\n"
    "- Database Module (db_manager.py): Uses SQLite3 to manage users (ID, Name, Registration Date) and attendance logs.\n"
    "- ML/Vision Module (model_trainer.py): Uses OpenCV's Haar Cascade (haarcascade_frontalface_default.xml) for face detection, "
    "and LBPH (Local Binary Patterns Histograms) Face Recognizer for training and prediction."
)
pdf.chapter_body(text_arch)

pdf.chapter_title('3. Final Workflow')
text_workflow = (
    "A. User Enrollment (Admin Phase)\n"
    "1. The Administrator logs into the Admin Dashboard using secure credentials.\n"
    "2. In the 'User Enrollment' tab, the Admin enters a new user's Employee/Student ID, Full Name, and Registration Date.\n"
    "3. Upon clicking 'Capture Face & Auto-Train', the system activates the webcam and captures 40 distinct face samples.\n"
    "4. These images are pre-processed (grayscaled, cropped, resized) and saved into a local 'dataset/' folder.\n"
    "5. Once capture is complete, the LBPH face recognizer immediately trains on the updated dataset and saves the 'trained_model.yml'.\n\n"
    
    "B. Attendance Marking (Kiosk Phase)\n"
    "1. The application runs in Kiosk mode by default.\n"
    "2. A user approaches the kiosk and clicks 'Start Attendance / Scan'.\n"
    "3. The system scans the video feed, detects faces using Haar Cascades, and passes the cropped face to the LBPH model.\n"
    "4. If the confidence score is within the acceptable threshold, the user is identified.\n"
    "5. The system logs the punch-in time to the SQLite database (avoiding duplicate punches for the day).\n"
    "6. Real-time KPI metrics (Present Today, Absent Today, Attendance %) and the Live Log are instantly updated on the screen.\n\n"
    
    "C. Reporting and Export (Admin Phase)\n"
    "1. The Admin can navigate to the 'Attendance Records & Export' tab to view the day's attendance log.\n"
    "2. The 'User Attendance Reports' tab shows a comprehensive summary of total days, present, absent, and attendance percentages.\n"
    "3. All these records and summaries can be exported as CSV files for payroll or external record-keeping."
)
pdf.chapter_body(text_workflow)

pdf.chapter_title('4. Recent Fixes & Improvements')
text_fixes = (
    "- Camera Initialization Bug: Fixed the missing Haar Cascade XML file issue by downloading it locally and integrating it with the script, "
    "ensuring OpenCV can load the cascade detector reliably on any environment."
)
pdf.chapter_body(text_fixes)

pdf.output('Project_Final_Plan_and_Workflow.pdf')
