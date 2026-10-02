import csv
import uuid
import hashlib
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QTabWidget, QLineEdit, 
                             QFormLayout, QFrame, QGroupBox, QComboBox, QSpinBox,
                             QStackedWidget)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg
from scipy.signal import iirnotch, butter, filtfilt, find_peaks

from .network import TCPServerThread
from .db import init_db, get_or_create_patient

# ==========================================
# WIDGET 1: SIGN-IN SCREEN
# ==========================================
class SignInWidget(QWidget):
    login_successful = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        
        # Initialize SQLite database
        init_db()
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        
        container = QFrame()
        container.setFixedSize(500, 450)
        container.setStyleSheet("background-color: #f8f9fa; border-radius: 10px; border: 1px solid #dee2e6;")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title = QLabel("Clinical System Login")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Auto-generate Patient ID based on login device (MAC hash)
        mac_node = uuid.getnode()
        device_hash = hashlib.md5(str(mac_node).encode()).hexdigest()[:6].upper()
        self.auto_id = f"DEV-{device_hash}"

        form = QFormLayout()
        form.setSpacing(15)
        
        self.patient_id = QLineEdit(self.auto_id)
        self.patient_id.setReadOnly(True)
        self.patient_id.setStyleSheet("background-color: #e9ecef; color: #495057; font-weight: bold; padding: 5px;")
        
        self.patient_name = QLineEdit()
        self.patient_name.setPlaceholderText("Enter full name")
        self.patient_name.setStyleSheet("padding: 5px;")
        
        self.age = QSpinBox()
        self.age.setRange(1, 120)
        self.age.setValue(25)
        self.age.setStyleSheet("padding: 5px;")
        
        self.gender = QComboBox()
        self.gender.addItems(["Male", "Female", "Other", "Prefer not to say"])
        self.gender.setStyleSheet("padding: 5px;")
        
        self.gmail = QLineEdit()
        self.gmail.setPlaceholderText("patient@gmail.com")
        self.gmail.setStyleSheet("padding: 5px;")
        
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Enter secure password")
        self.password.setStyleSheet("padding: 5px;")
        
        form.addRow("Patient ID (Device):", self.patient_id)
        form.addRow("Full Name:", self.patient_name)
        form.addRow("Age:", self.age)
        form.addRow("Gender:", self.gender)
        form.addRow("Gmail Address:", self.gmail)
        form.addRow("Password:", self.password)
        
        layout.addLayout(form)
        
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)
        
        self.login_btn = QPushButton("Sign In / Register")
        self.login_btn.setFixedSize(440, 45)
        self.login_btn.setStyleSheet("background-color: #0d6efd; color: white; font-size: 16px; font-weight: bold; border-radius: 5px;")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        main_layout.addWidget(container)

    def handle_login(self):
        gmail = self.gmail.text().strip()
        pwd = self.password.text().strip()
        name = self.patient_name.text().strip()
        
        if not gmail or not pwd or not name:
            self.error_label.setText("Please fill out Name, Gmail, and Password.")
            return
            
        if "@gmail.com" not in gmail.lower():
            self.error_label.setText("Please enter a valid Gmail address.")
            return

        # Authenticate with SQLite DB
        success, msg, patient_data = get_or_create_patient(
            self.auto_id, 
            name, 
            self.age.value(), 
            self.gender.currentText(), 
            gmail, 
            pwd
        )
        
        if success:
            self.error_label.setText("")
            self.login_successful.emit(patient_data)
        else:
            self.error_label.setText(msg)


# ==========================================
# WIDGET 2: MAIN DASHBOARD
# ==========================================
class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.patient_data = {}
        
        main_layout = QVBoxLayout(self)

        # ------------------------------------------
        # TOP PANEL: Read-Only Patient Header
        # ------------------------------------------
        top_panel = QGroupBox("Active Patient Session")
        top_layout = QHBoxLayout(top_panel)
        
        self.header_label = QLabel("Loading patient data...")
        self.header_label.setStyleSheet("font-size: 16px; color: #333;")
        top_layout.addWidget(self.header_label)
        
        top_layout.addStretch()

        status_layout = QVBoxLayout()
        self.status_label = QLabel("Monitoring...")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        status_layout.addWidget(self.status_label, alignment=Qt.AlignRight)
        
        self.record_btn = QPushButton("[REC] Start Recording Session")
        self.record_btn.setFixedSize(220, 45)
        self.record_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
        self.record_btn.clicked.connect(self.toggle_recording)
        status_layout.addWidget(self.record_btn, alignment=Qt.AlignRight)
        top_layout.addLayout(status_layout)

        main_layout.addWidget(top_panel)

        # ------------------------------------------
        # TABS: Separate ECG and EEG Panels
        # ------------------------------------------
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        pg.setConfigOptions(antialias=True, background='#ffffff', foreground='#333333')

        # --- TAB 1: ECG ANALYSIS ---
        self.ecg_tab = QWidget()
        ecg_layout = QHBoxLayout(self.ecg_tab)
        
        self.ecg_plot = pg.PlotWidget(title="Live ECG Waveform")
        self.ecg_plot.setYRange(0, 1024)
        self.ecg_plot.setLabel('left', 'Amplitude', units='ADC Counts')
        self.ecg_plot.setLabel('bottom', 'Samples', units='(250 Hz)')
        self.ecg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ecg_curve = self.ecg_plot.plot(pen=pg.mkPen('#e63946', width=2))
        ecg_layout.addWidget(self.ecg_plot, stretch=3)
        
        ecg_stats_layout = QVBoxLayout()
        
        self.bpm_frame = QFrame()
        self.bpm_frame.setStyleSheet("background-color: #f8d7da; border-radius: 10px; padding: 20px;")
        bpm_layout = QVBoxLayout(self.bpm_frame)
        self.bpm_val = QLabel("-- BPM")
        self.bpm_val.setAlignment(Qt.AlignCenter)
        self.bpm_val.setFont(QFont("Arial", 36, QFont.Bold))
        bpm_layout.addWidget(QLabel("Heart Rate"))
        bpm_layout.addWidget(self.bpm_val)
        ecg_stats_layout.addWidget(self.bpm_frame)

        self.hrv_frame = QFrame()
        self.hrv_frame.setStyleSheet("background-color: #d1ecf1; border-radius: 10px; padding: 20px;")
        hrv_layout = QVBoxLayout(self.hrv_frame)
        self.hrv_val = QLabel("-- ms")
        self.hrv_val.setAlignment(Qt.AlignCenter)
        self.hrv_val.setFont(QFont("Arial", 28, QFont.Bold))
        self.stress_val = QLabel("Awaiting Data")
        self.stress_val.setAlignment(Qt.AlignCenter)
        self.stress_val.setFont(QFont("Arial", 14, QFont.Bold))
        hrv_layout.addWidget(QLabel("HRV (Stress)"))
        hrv_layout.addWidget(self.hrv_val)
        hrv_layout.addWidget(self.stress_val)
        ecg_stats_layout.addWidget(self.hrv_frame)

        self.sq_frame = QFrame()
        self.sq_frame.setStyleSheet("background-color: #e2e3e5; border-radius: 10px; padding: 20px;")
        sq_layout = QVBoxLayout(self.sq_frame)
        self.sq_val = QLabel("Awaiting Data...")
        self.sq_val.setAlignment(Qt.AlignCenter)
        self.sq_val.setFont(QFont("Arial", 16, QFont.Bold))
        sq_layout.addWidget(QLabel("Signal Quality"))
        sq_layout.addWidget(self.sq_val)
        ecg_stats_layout.addWidget(self.sq_frame)
        
        ecg_stats_layout.addStretch()
        ecg_layout.addLayout(ecg_stats_layout, stretch=1)
        self.tabs.addTab(self.ecg_tab, "ECG Analysis")

        # --- TAB 2: EEG ANALYSIS ---
        self.eeg_tab = QWidget()
        eeg_layout = QVBoxLayout(self.eeg_tab)
        
        self.eeg_plot = pg.PlotWidget(title="Live EEG Waveform")
        self.eeg_plot.setYRange(0, 1024)
        self.eeg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.eeg_curve = self.eeg_plot.plot(pen=pg.mkPen('#457b9d', width=2))
        eeg_layout.addWidget(self.eeg_plot, stretch=1)

        eeg_bottom_layout = QHBoxLayout()
        
        self.fft_plot = pg.PlotWidget(title="Frequency Spectrum (0-40 Hz)")
        self.fft_plot.setXRange(0, 40)
        self.fft_plot.setLabel('left', 'Magnitude')
        self.fft_plot.showGrid(x=True, y=True, alpha=0.3)
        self.fft_curve = self.fft_plot.plot(pen=pg.mkPen('#1d3557', width=2), fillLevel=0, brush=(29,53,87,100))
        eeg_bottom_layout.addWidget(self.fft_plot, stretch=2)

        self.band_plot = pg.PlotWidget(title="Brainwave Power Bands")
        self.band_plot.setYRange(0, 100) 
        self.band_plot.getAxis('bottom').setTicks([[(1, 'Delta'), (2, 'Theta'), (3, 'Alpha'), (4, 'Beta')]])
        self.band_bars = pg.BarGraphItem(x=[1, 2, 3, 4], height=[0, 0, 0, 0], width=0.6, 
                                         brushes=['#2a9d8f', '#e9c46a', '#f4a261', '#e76f51'])
        self.band_plot.addItem(self.band_bars)
        eeg_bottom_layout.addWidget(self.band_plot, stretch=1)

        eeg_layout.addLayout(eeg_bottom_layout, stretch=1)
        self.tabs.addTab(self.eeg_tab, "EEG Analysis")

        # ------------------------------------------
        # DATA & SYSTEM INITIALIZATION
        # ------------------------------------------
        self.fs = 250.0
        self.max_points = int(self.fs * 4) 
        self.data_buffer = np.zeros(self.max_points)
        self.ptr = 0

        self.current_lo_p = 0
        self.current_lo_m = 0

        self.is_recording = False
        self.recorded_data = []

        self.b_notch, self.a_notch = iirnotch(w0=50.0, Q=30.0, fs=self.fs)
        # Dedicated smooth filter for ECG (0.5 to 30 Hz, sharper N=4 order to eliminate muscle noise)
        self.b_ecg, self.a_ecg = butter(N=4, Wn=[0.5, 30.0], btype='band', fs=self.fs)
        # Wider filter for EEG to preserve Beta/Gamma brainwaves (0.5 to 40 Hz)
        self.b_eeg, self.a_eeg = butter(N=4, Wn=[0.5, 40.0], btype='band', fs=self.fs)

        self.server_thread = TCPServerThread()
        self.server_thread.data_received.connect(self.process_incoming_data)
        self.server_thread.status_update.connect(self.update_status)
        self.server_thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(33) 

    def set_patient_data(self, data):
        self.patient_data = data
        name = data.get("name")
        pid = data.get("id")
        age = data.get("age")
        gender = data.get("gender")
        gmail = data.get("gmail")
        
        header_html = f"""
        <b>Patient:</b> {name} &nbsp;|&nbsp; 
        <b>ID:</b> {pid} &nbsp;|&nbsp; 
        <b>Age:</b> {age} &nbsp;|&nbsp; 
        <b>Gender:</b> {gender} &nbsp;|&nbsp; 
        <b>Account:</b> {gmail}
        """
        self.header_label.setText(header_html)

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recorded_data = []
            self.record_btn.setText("[STOP] Stop & Save Session")
            self.record_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
            self.update_status("[REC] Recording active...")
        else:
            self.is_recording = False
            self.record_btn.setText("[REC] Start Recording Session")
            self.record_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
            self.save_recording()

    def save_recording(self):
        if len(self.recorded_data) == 0:
            self.update_status("WARNING: No data recorded.")
            return

        p_name = self.patient_data.get("name", "Unknown")
        p_id = self.patient_data.get("id", "0000")
        p_age = self.patient_data.get("age", "")
        p_gender = self.patient_data.get("gender", "")
        p_gmail = self.patient_data.get("gmail", "")
        
        mode = "ECG" if self.tabs.currentIndex() == 0 else "EEG"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{p_id}_{p_name.replace(' ', '_')}_{mode}_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='') as f:
                f.write(f"# Patient ID: {p_id}\n")
                f.write(f"# Patient Name: {p_name}\n")
                f.write(f"# Age: {p_age}\n")
                f.write(f"# Gender: {p_gender}\n")
                f.write(f"# Gmail: {p_gmail}\n")
                f.write(f"# Modality: {mode}\n")
                f.write(f"# Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Sampling Rate: {self.fs} Hz\n")
                f.write(f"# Filter: 50Hz Notch + 0.5-40Hz Bandpass\n")
                # Password deliberately omitted for security
                
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Filtered_ADC_Value", "Lead_Off_Plus", "Lead_Off_Minus"])
                writer.writerows(self.recorded_data)
                
            self.update_status(f"SUCCESS: Saved {len(self.recorded_data)} samples to {filename}")
        except Exception as e:
            self.update_status(f"ERROR: Error saving: {e}")
            
        self.recorded_data.clear()

    def process_incoming_data(self, val, lo_p, lo_m):
        if self.ptr == 0:
            self.data_buffer.fill(val)

        self.data_buffer[:-1] = self.data_buffer[1:]
        self.data_buffer[-1] = val
        self.ptr += 1
        
        self.current_lo_p = lo_p
        self.current_lo_m = lo_m

    def update_status(self, msg):
        self.status_label.setText(msg)

    def update_ui(self):
        if self.ptr < 10:
            return 

        raw_data = self.data_buffer.copy()
        current_tab = self.tabs.currentIndex()

        if np.std(raw_data) < 0.1:
            if current_tab == 0:
                self.ecg_curve.setData(raw_data)
                self.sq_val.setText("Flatline / DC")
                self.sq_val.setStyleSheet("color: red;")
                self.bpm_val.setText("-- BPM")
                if hasattr(self, 'smoothed_bpm'): del self.smoothed_bpm
            elif current_tab == 1:
                self.eeg_curve.setData(raw_data)
                self.fft_curve.setData([], [])
                self.band_bars.setOpts(height=[0, 0, 0, 0])
            return

        try:
            notched = filtfilt(self.b_notch, self.a_notch, raw_data)
            
            # Apply dedicated smoothing depending on the active tab
            if current_tab == 0:
                filtered = filtfilt(self.b_ecg, self.a_ecg, notched)
            else:
                filtered = filtfilt(self.b_eeg, self.a_eeg, notched)
                
            # Lock the baseline perfectly to the ADC center (512) instead of np.mean().
            # This completely stops the graph from "bouncing" violently up and down.
            display_filtered = filtered + 512
        except ValueError:
            return 
            
        if self.is_recording:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self.recorded_data.append([now_str, round(display_filtered[-1], 2), self.current_lo_p, self.current_lo_m])

        if current_tab == 0:
            self.ecg_curve.setData(display_filtered)
            p2p_amplitude = np.max(display_filtered) - np.min(display_filtered)
            
            if self.current_lo_p == 1 or self.current_lo_m == 1:
                self.sq_val.setText("ERROR: LEAD OFF\n(Check Electrodes)")
                self.sq_val.setStyleSheet("color: red;")
                self.bpm_val.setText("-- BPM")
                self.hrv_val.setText("-- ms")
                self.stress_val.setText("Awaiting Data")
                if hasattr(self, 'smoothed_bpm'): del self.smoothed_bpm
                if hasattr(self, 'smoothed_rmssd'): del self.smoothed_rmssd
                
            elif p2p_amplitude < 40 or np.std(raw_data) < 5:
                self.sq_val.setText("Disconnected / Flat")
                self.sq_val.setStyleSheet("color: orange;")
                self.bpm_val.setText("-- BPM")
                self.hrv_val.setText("-- ms")
                self.stress_val.setText("Awaiting Data")
                if hasattr(self, 'smoothed_bpm'): del self.smoothed_bpm
                if hasattr(self, 'smoothed_rmssd'): del self.smoothed_rmssd
                
            elif np.max(raw_data) > 1000 or np.min(raw_data) < 10:
                self.sq_val.setText("Poor / Clipping")
                self.sq_val.setStyleSheet("color: orange;")
                self.bpm_val.setText("-- BPM")
                self.hrv_val.setText("-- ms")
                self.stress_val.setText("Awaiting Data")
                if hasattr(self, 'smoothed_bpm'): del self.smoothed_bpm
                if hasattr(self, 'smoothed_rmssd'): del self.smoothed_rmssd
                
            else:
                self.sq_val.setText("Good")
                self.sq_val.setStyleSheet("color: green;")
                
                if not hasattr(self, 'qrs_b'):
                    self.qrs_b, self.qrs_a = butter(2, [5.0, 15.0], btype='band', fs=self.fs)
                
                try:
                    qrs_filtered = filtfilt(self.qrs_b, self.qrs_a, raw_data)
                    qrs_squared = qrs_filtered ** 2
                    threshold = np.mean(qrs_squared) * 2.5
                    peaks, _ = find_peaks(qrs_squared, distance=int(self.fs * 0.3), height=threshold)
                    
                    if len(peaks) > 1:
                        rr_intervals = np.diff(peaks) / self.fs
                        valid_rr = rr_intervals[(rr_intervals > 0.3) & (rr_intervals < 2.0)]
                        
                        if len(valid_rr) > 0:
                            # 1. Update BPM
                            current_bpm = 60.0 / np.mean(valid_rr)
                            if not hasattr(self, 'smoothed_bpm'):
                                self.smoothed_bpm = current_bpm
                            else:
                                self.smoothed_bpm = (0.05 * current_bpm) + (0.95 * self.smoothed_bpm)
                            self.bpm_val.setText(f"{int(self.smoothed_bpm)} BPM")
                            
                            # 2. Update HRV (RMSSD) if multiple intervals exist
                            if len(valid_rr) > 1:
                                rr_diff = np.diff(valid_rr) * 1000 # Convert to ms
                                current_rmssd = np.sqrt(np.mean(rr_diff**2))
                                
                                if not hasattr(self, 'smoothed_rmssd'):
                                    self.smoothed_rmssd = current_rmssd
                                else:
                                    self.smoothed_rmssd = (0.1 * current_rmssd) + (0.9 * self.smoothed_rmssd)
                                    
                                self.hrv_val.setText(f"{int(self.smoothed_rmssd)} ms")
                                
                                # Simple HRV Stress Indicator
                                if self.smoothed_rmssd > 40:
                                    self.stress_val.setText("Relaxed")
                                    self.stress_val.setStyleSheet("color: green;")
                                elif self.smoothed_rmssd > 20:
                                    self.stress_val.setText("Normal")
                                    self.stress_val.setStyleSheet("color: #d39e00;")
                                else:
                                    self.stress_val.setText("Stressed")
                                    self.stress_val.setStyleSheet("color: red;")
                except ValueError:
                    pass

        elif current_tab == 1:
            self.eeg_curve.setData(display_filtered)
            
            if self.current_lo_p == 1 or self.current_lo_m == 1:
                self.fft_curve.setData([], [])
                self.band_bars.setOpts(height=[0, 0, 0, 0])
                return

            windowed = filtered * np.hamming(len(filtered))
            fft_vals = np.abs(np.fft.rfft(windowed))
            fft_freqs = np.fft.rfftfreq(len(windowed), 1.0 / self.fs)
            
            self.fft_curve.setData(fft_freqs, fft_vals)

            def get_band_power(fmin, fmax):
                idx = np.where((fft_freqs >= fmin) & (fft_freqs < fmax))[0]
                return np.sum(fft_vals[idx]) if len(idx) > 0 else 0
                
            delta = get_band_power(0.5, 4.0)
            theta = get_band_power(4.0, 8.0)
            alpha = get_band_power(8.0, 13.0)
            beta  = get_band_power(13.0, 30.0)
            
            total_power = delta + theta + alpha + beta
            if total_power > 0:
                dp = (delta / total_power) * 100
                tp = (theta / total_power) * 100
                ap = (alpha / total_power) * 100
                bp = (beta / total_power) * 100
                self.band_bars.setOpts(height=[dp, tp, ap, bp])

    def close_threads(self):
        self.server_thread.stop()


# ==========================================
# ROOT WINDOW CONTROLLER
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clinical EEG/ECG System")
        self.resize(1280, 800)
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Initialize views
        self.sign_in_view = SignInWidget()
        self.dashboard_view = DashboardWidget()
        
        self.stack.addWidget(self.sign_in_view)
        self.stack.addWidget(self.dashboard_view)
        
        # Connect Login Event -> Transition to Dashboard
        self.sign_in_view.login_successful.connect(self.transition_to_dashboard)
        
    def transition_to_dashboard(self, patient_data):
        self.dashboard_view.set_patient_data(patient_data)
        self.stack.setCurrentWidget(self.dashboard_view)
        
    def closeEvent(self, event):
        self.dashboard_view.close_threads()
        event.accept()

