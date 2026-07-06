# NISAP - National Intelligent School Assistance Platform

<p align="center">
  <img src="static/NEP.png" alt="NISAP Logo" width="180">
</p>

## 📖 Overview

NISAP (National Intelligent School Assistance Platform) is an AI-powered school management and assistance platform designed to help educational institutions digitize their workflow while aligning with India's National Education Policy (NEP) 2020.

The platform combines Artificial Intelligence, OCR, and cloud technologies to simplify school administration, automate data entry, and provide intelligent policy guidance.

---

## ✨ Features

### 🤖 AI NEP Assistant
- AI-powered chatbot for NEP 2020 guidance
- Instant answers to policy-related questions
- Context-aware educational assistance

### 📄 OCR Document Processing
- Extracts school information from uploaded forms
- AI-powered handwriting and printed text recognition
- Automatically converts extracted data into structured format

### 🏫 School Management
- School profile management
- Secure authentication system
- Cloud-based database integration

### ☁️ Cloud Database
- Powered by Supabase
- Secure user authentication
- Real-time data storage

### 🔐 Authentication
- User Registration
- Login System
- Password Hashing
- Session Management

---

## 🛠️ Tech Stack

### Backend
- Python
- Flask
- Flask-CORS

### Artificial Intelligence
- Google Gemini API
- Groq API

### Database
- Supabase

### Frontend
- HTML
- CSS
- JavaScript

### OCR
- Pillow (PIL)
- Google Gemini Vision

---

## 📂 Project Structure

```
NISAP/
│
├── app.py                  # Main Flask application
├── setupdb.py              # Database setup
├── LICENSE
│
├── static/
│   ├── CSS files
│   ├── JavaScript files
│   ├── Images
│   └── Documents
│
├── templates/
│   ├── HTML pages
│   ├── Authentication
│   ├── Dashboard
│   └── AI Interface
│
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/NISAP.git

cd NISAP
```

### 2. Create a virtual environment

Windows

```bash
python -m venv venv
venv\Scripts\activate
```

Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables

Create a `.env` file.

```env
FLASK_SECRET_KEY=your_secret_key

SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

GEMINI_API_KEY=your_gemini_api_key

GROQ_API_KEY=your_groq_api_key
```

---

### 5. Run the application

```bash
python app.py
```

Open:

```
http://127.0.0.1:5000
```

---

## 📸 Main Modules

- Landing Page
- User Authentication
- AI NEP Assistant
- OCR Data Extraction
- School Dashboard
- Profile Management

---

## 🔒 Security Notes

Before deploying or publishing:

- Remove all hardcoded API keys.
- Store secrets in environment variables.
- Never commit `.env` files.
- Rotate any API keys that have already been exposed.

---

## 🚀 Future Improvements

- Student Dashboard
- Teacher Dashboard
- Attendance Management
- Analytics Dashboard
- PDF Report Generation
- Multi-language Support
- Voice-enabled AI Assistant
- Mobile Application

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the Apache License 2.0.

---

## 👨‍💻 Author

**Shis Maheta**

National-Level Hackathon Winner | Full Stack Developer | AI Developer

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
