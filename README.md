# 🛡️ AI Hybrid NIDS (Network Intrusion Detection System)

An **AI-powered Hybrid Network Intrusion Detection System (NIDS)** designed to monitor network traffic in real-time and detect malicious activities using both **signature-based** and **anomaly-based** detection techniques.

---

## 🚀 Features

* 🔍 Real-time packet capture and analysis
* 🧠 Machine Learning-based anomaly detection
* 🧾 Signature-based attack detection (SQLi, XSS, Port Scanning)
* 🔗 Hybrid detection engine (Fusion of ML + Rules)
* 📊 Desktop-based monitoring dashboard
* 🚨 Alert generation and logging system
* 🗄️ SQLite-based data storage
* ⚙️ Modular and scalable architecture

---

## 🏗️ Project Architecture

```
nids-desktop/
│
├── core/              # Detection engines (signature, anomaly, fusion)
├── ml/                # Machine learning pipeline
├── ui/                # Desktop interface
├── services/          # Background monitoring services
├── rules/             # Attack signatures
├── data/              # Captured packets & datasets
├── database/          # SQLite database
├── utils/             # Helper functions
└── run.py             # Main entry point
```

---

## ⚙️ Technologies Used

* Python
* Scapy (Packet Capture)
* Scikit-learn / ML Libraries
* SQLite
* PyQt / Tkinter (UI)

---

## 🧠 Detection Techniques

### 1. Signature-Based Detection

Detects known attacks using predefined rules:

* SQL Injection
* Cross-Site Scripting (XSS)
* Port Scanning

### 2. Anomaly-Based Detection

* Learns normal traffic behavior
* Detects unknown and zero-day attacks

### 3. Hybrid Engine

Combines both techniques to improve:

* Accuracy
* Detection rate
* False positive reduction

---

## ▶️ How to Run

```bash
git clone https://github.com/your-username/ai-hybrid-nids.git
cd ai-hybrid-nids
pip install -r requirements.txt
python run.py
```

---

## 📊 Use Cases

* University Lab Network Monitoring
* Small Enterprise Security
* Educational Cybersecurity Demonstrations

---

## 📌 Future Improvements

* 🌐 Web-based dashboard
* 🤖 Deep Learning models
* ☁️ Cloud deployment
* 📡 Distributed IDS support

---

## 👨‍🎓 Academic Info

This project is developed as a **Final Year Project (FYP)** to demonstrate practical implementation of modern intrusion detection techniques.

---

## 📜 License

This project is licensed under the MIT License.

---

## 🙌 Author

**Muhammad Abdullah**
Cybersecurity & DevOps Enthusiast

**Faizan Ali**
Software Developer / Artificial Intelligence Enthusiast
