# 💰 Chatbot Personal Finance Manager

Personal Finance Manager is a web-based chatbot application that helps individuals manage their personal finances smarter. Users can log daily transactions manually or by scanning receipt photos, visualize spending patterns across categories, set monthly budgets, and chat with an AI assistant powered by Google Gemini for personalized financial advice.

## Live Demo
https://chatbot-personal-finance-manager.streamlit.app/

## Target Users
- Students and young professionals who want a simple way to track daily expenses
- Anyone looking to understand their spending habits and improve financial health
- Users who prefer a conversational interface over traditional budgeting spreadsheets

## Features
- Dashboard
- AI Finance Chatbot
- Add Transaction
- Category Management
- Authentication

## Tech Stack
1. **Frontend / UI:** 
- Streamlit

2. **AI / LLM:**
- Google Gemini API

3. **Database:**
- SQLite via SQLAlchemy

## Installation
1. **Clone the repository**
```bash
git clone https://github.com/your-username/personal-finance-manager.git
cd personal-finance-manager
``` 

2. **Create and activate a virtual environment**
```bash
python -m venv venv
source venv/bin/activate      
venv\Scripts\activate  
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**  
edit .env:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

5. **Run the app**
```bash
streamlit run app.py
```
