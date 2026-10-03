# Portable Wireless Clinical EEG/ECG System

A low-cost, real-time wireless bio-signal acquisition system designed for continuous monitoring and clinical analysis of ECG (Electrocardiogram) and EEG (Electroencephalogram) signals.

The project features a **modular Python desktop application** paired with an **ESP8266 + AD8232** hardware stack, communicating wirelessly over a local TCP/IP network.

---

## Key Features

### Clinical Dashboard (Python)
* **Secure Patient Profiles:** A dedicated sign-in screen backed by a local **SQLite database** (`patients.db`) securely manages user profiles, hashing passwords, and generating permanent Device IDs (`DEV-XXXXXX`).
* **Hardware Lead-Off Detection:** Automatically halts calculations and alerts the user on-screen if an electrode loses contact with the skin.
* **Advanced ECG Analytics:** 
  * **Pan-Tompkins QRS Detection:** Uses 5-15Hz bandpass isolation, signal squaring, and dynamic thresholding for clinical-grade heartbeat detection.
  * **Heart Rate Variability (HRV):** Calculates micro-second beat variations (RMSSD algorithm) to drive a live **Stress Level Indicator**.
* **Real-Time EEG Analytics:** Features a live 1D FFT (Fast Fourier Transform) frequency spectrum, separating brainwave energy into Delta, Theta, Alpha, and Beta power bands.
* **Automated Data Export:** Records timestamped sessions directly to CSV format, automatically embedding the patient's profile metadata and filter configurations into the file header.

### Hardware Stack
* **Analog Front-End:** Uses the **AD8232** bio-signal chip for 100× hardware amplification and 0.5Hz – 40Hz analog filtering.
* **Microcontroller:** **ESP8266** continuously samples the analog signal via its 10-bit ADC at ~250 Hz, reading digital states for Lead-Off detection, and streaming everything via WiFi.

---

## Repository Structure

The software has been professionally organized into a modular Python application:

```text
/eeg
├── main.py                # Main executable entry point
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore rules for DBs, CSVs, and caches
└── app/
    ├── __init__.py        
    ├── ui.py              # Clinical Dashboard, PyQt5 UI, and DSP Analytics
    ├── network.py         # Background TCP Server Thread
    └── db.py              # SQLite database and authentication logic
```

---

## Hardware Wiring Guide

To build the sensor, wire the **AD8232** to the **ESP8266** as follows:

| AD8232 Pin | ESP8266 Pin | Description |
| :--- | :--- | :--- |
| **GND** | `GND` | Ground |
| **3.3V** | `3V3` | Power Supply |
| **OUTPUT** | `A0` | Analog bio-signal output |
| **LO+** | `D1` (GPIO 5) | Lead-Off Positive (Digital) |
| **LO-** | `D2` (GPIO 4) | Lead-Off Negative (Digital) |

*Note: Ensure your Arduino sketch (`sketch_oct3a.ino`) is configured to send data in the `value,lo+,lo-\n` comma-separated format.*

---

## Getting Started

### 1. Hardware Setup
1. Wire the circuit according to the table above.
2. Open the ESP8266 sketch in the Arduino IDE.
3. Modify the `serverIP` to match the IPv4 address of the computer running the Python app.
4. Upload the code to your ESP8266.

### 2. Software Setup
Ensure you have Python 3.8+ installed. It is highly recommended to use a virtual environment.

```bash
# Navigate to the application directory
cd eeg

# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Running the Application
```bash
python main.py
```

### 4. Usage Flow
1. **Sign In / Register:** Enter your Name, Age, Gender, Gmail, and Password. If it's your first time, the system will seamlessly register you in the local database.
2. **Power On Device:** Power up your ESP8266. It will automatically connect to the Python TCP Server.
3. **Monitor:** Use the tabs to switch between the heavily filtered **ECG Analysis** and the high-bandwidth **EEG Analysis**.
4. **Record:** Click the green **Start Recording** button to lock the session and dump clinical data directly to CSV.

---

## Future Roadmap (Phase 2 & 3)
* Upgrade to a **24-bit ADC** (e.g., ADS1299) for high-fidelity microvolt brainwave capture.
* Upgrade from ESP8266 to ESP32 to support multi-channel (8+) spatial mapping.
* Implement 2D rolling Spectrograms (Waterfall plots) for sleep staging.
* Integrate standard **EDF+** clinical exporting.
