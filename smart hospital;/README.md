# Smart Hospital Bed Allocator

An advanced academic/demo hospital bed management application built with Flask, SQLite, Flask-Login, Bootstrap, and Chart.js.

## Features
- Secure login with hashed passwords and role-based access (Admin / Staff)
- Dashboard metrics and occupancy charts
- Patient registration and search
- Bed management by ward, type, and facilities
- Admission workflow with smart bed matching
- Discharge workflow that frees the bed
- Allocation audit history
- CSV report export
- Demo data seeding on first run

## Setup (Windows PowerShell)
```powershell
cd path\to\smart_hospital_bed_allocator
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

If PowerShell blocks activation, run this for the current terminal only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## First-run demo credentials
- Username: `admin`
- Password: `Admin@12345`

Change the demo password before any real deployment. The app uses a development secret key by default; set `SECRET_KEY` in your environment for deployments.

## Notes
This is an educational prototype, not a certified clinical system. Do not enter real patient data. Before any real-world use, add production-grade secrets, HTTPS, backups, audit review, privacy controls, security testing, and clinical validation.
