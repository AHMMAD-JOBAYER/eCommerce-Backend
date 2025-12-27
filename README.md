

# Backend Project Documentation

**E-Commerce Management System (Backend)**

---

## 1. Project Overview

This project is the **backend implementation of an E-Commerce Management System**, developed in **Python** using **FastAPI**.
The backend exposes RESTful APIs for managing users, sellers, shops, products, orders, payments, and shipments.

The project is designed to run **reliably on Windows** using **`uv` (Astral)** as the package manager and environment manager, with dependencies defined in **`pyproject.toml`**.

---

## 2. Project Structure

The backend project follows a minimal and flat structure:

```
.
├── ecommerce.db
├── main.py
├── main.txt
├── pyproject.toml
├── README.md
└── uv.lock
```

### Description of Files

| File             | Purpose                                             |
| ---------------- | --------------------------------------------------- |
| `main.py`        | Entry point of the FastAPI application              |
| `ecommerce.db`   | SQLite database file (auto-created/used by backend) |
| `pyproject.toml` | Project metadata and dependency definitions         |
| `uv.lock`        | Locked dependency versions managed by `uv`          |
| `README.md`      | Project documentation                               |
| `main.txt`       | Supplementary notes or raw data (non-executable)    |


---

## 3. Technology Stack

| Component        | Technology          |
| ---------------- | ------------------- |
| Language         | Python 3.13         |
| Framework        | FastAPI             |
| ASGI Server      | Uvicorn             |
| Database         | SQLite              |
| Package Manager  | **uv (Astral)**     |
| Dependency Spec  | `pyproject.toml`    |
| Operating System | **Windows 10 / 11** |

---

## 4. System Requirements (Windows)

### Required Software

* Windows 10 or Windows 11
* Python **3.10 or higher** (Python 3.13 supported)
* PowerShell or Windows Terminal

Verify Python installation:

```powershell
python --version
```

---

## 5. Installing `uv` (Astral) on Windows

Install `uv` globally using `pip`:

```powershell
pip install uv
```

Verify installation:

```powershell
uv --version
```

---

## 6. Environment Setup Using `uv`

Navigate to the backend project directory:

```powershell
cd path\to\project
```

### 6.1 Create Virtual Environment

```powershell
uv venv
```

This creates a `.venv` directory managed by `uv`.

---

### 6.2 Activate the Virtual Environment (Windows)

```powershell
.venv\Scripts\activate
```

If PowerShell blocks activation, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## 7. Installing Dependencies

All dependencies are defined in `pyproject.toml` and locked in `uv.lock`.

Install dependencies using:

```powershell
uv sync
```

This ensures:

* Exact dependency versions
* Reproducible environment
* No need for `requirements.txt`

---

## 8. Running the Backend Server

Start the FastAPI application using Uvicorn:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### What Happens on Startup

* SQLite database `ecommerce.db` is loaded or created
* Required database tables are initialized
* API server starts listening on port **8000**

---

## 9. Accessing the API

### Base URL

```
http://127.0.0.1:8000
```

### API Documentation

* Swagger UI:

  ```
  http://127.0.0.1:8000/docs
  ```
* ReDoc:

  ```
  http://127.0.0.1:8000/redoc
  ```

---

## 10. Database Details

| Item            | Description            |
| --------------- | ---------------------- |
| Database Engine | SQLite                 |
| Database File   | `ecommerce.db`         |
| Location        | Project root directory |
| Creation        | Automatic              |

No external database server is required.

---

## 11. Stopping the Server

To stop the backend server:

```
CTRL + C
```

---

## 12. Why `uv` + `pyproject.toml` Is Used

* Faster dependency resolution
* Single source of truth for dependencies
* Cleaner Windows support
* No `requirements.txt` needed
* Industry-standard Python project layout

---

## 13. Notes and Best Practices

* Do not delete `uv.lock`
* Always activate `.venv` before running the server
* Keep `pyproject.toml` updated when adding dependencies

---

## 14. Project Status

| Feature              | Status |
| -------------------- | ------ |
| Windows Compatible   | Yes    |
| uv (Astral) Support  | Yes    |
| pyproject.toml Based | Yes    |
| SQLite Database      | Yes    |
| FastAPI Docs Enabled | Yes    |

---
