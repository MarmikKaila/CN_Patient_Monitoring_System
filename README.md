## 🩺 Real-Time Patient Monitoring System – Overview

The **Real-Time Patient Monitoring System** is a multi-protocol healthcare simulation platform designed to demonstrate how medical devices transmit patient vitals in real time using different network protocols based on reliability and speed requirements. It models how hospitals monitor multiple patients simultaneously and deliver live updates to doctors through a dashboard.

---

## 🎯 Purpose of the Project

- To **simulate real-time vital sign transmission** for multiple patients.
- To demonstrate **different network protocols (UDP, TCP, WebSocket)** and their real-world use cases.
- To show how **telemetry, alerts, and dashboard updates** can be handled efficiently in modern systems.
- To provide a **practical educational tool** for learning:
  - Networking concepts  
  - Real-time systems  
  - Asynchronous programming  
  - Healthcare data workflows  
- To create a **scalable and modular architecture** suitable for expansion (IoT, AI, cloud).

---

## ⚙️ What This Project Does

- Generates real-time vitals (heart rate, SpO2, temperature, BP)
- Sends them via **UDP** for fast telemetry
- Sends alerts via **TCP** for guaranteed delivery
- Updates the dashboard via **WebSocket** for live sync
- Displays all vitals and alerts on an interactive web dashboard
- Handles multiple patient streams simultaneously

---

## 🧰 Technologies & Tools Used

### 🖥 Backend (Server)
- **Python 3.9+**
- **FastAPI** (WebSocket server + API)
- **Asyncio** (for concurrency)
- **UDP** (telemetry)
- **TCP** (alerts)
- **WebSocket** (real-time dashboard updates)
- **Uvicorn** (ASGI server)

### 👤 Client (Simulators)
- Python scripts generating live vitals  
- Sends data to the backend over UDP and TCP

### 🌐 Frontend (Dashboard)
- **HTML5, CSS3**
- **JavaScript**
- **Chart.js** (real-time graphs)
- WebSocket-based live updates

### 🧪 Development & Documentation
- Wireshark (optional – packet capture)
- Logs + diagrams (optional in `/docs`)

---

## 📌 Summary

This project demonstrates a complete real-time healthcare data pipeline using modern networking techniques.  
It showcases how hospitals handle different types of data—telemetry, alerts, and live dashboards—each using a protocol best suited for that purpose.  
The system is modular, scalable, and designed for learning, experimentation, and future expansion.

## Live Demo 

```
https://drive.google.com/file/d/15lyc-WrCTvhi_fBEMDE8yj4I7hK5CpYT/view?usp=drive_link
```

