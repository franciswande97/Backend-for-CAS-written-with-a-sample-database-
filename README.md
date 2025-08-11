CAS Backend API
📌 Overview
This is the backend API for the Career Advisory System (CAS).
It processes CV uploads, extracts skills and qualifications using OpenAI’s API, matches users with jobs from a MySQL database, and suggests relevant courses to improve missing skills.

Features
CV Parsing (PDF/DOCX support)

AI-powered skill extraction using OpenAI’s GPT model

Job Matching from a sample MySQL database

Course Recommendations for missing skills

RESTful API with JSON responses

Secure environment variable handling for sensitive keys

Tech Stack
Flask – Web framework

MySQL – Database

OpenAI API – AI-powered CV parsing

PyMuPDF – PDF text extraction

python-docx – DOCX file reading

JSON – Structured API responses

Project Structure
Backend/
│── app.py              # Main Flask app
│── requirements.txt    # Python dependencies
│── temp/               # Temporary uploaded files
│── .env                # Environment variables (not tracked in Git)
