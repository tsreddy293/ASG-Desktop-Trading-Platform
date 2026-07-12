# AI Stock Guardian (ASG)

AI Stock Guardian is a professional desktop trading application foundation built with Python, PySide6, SQLite, and SQLAlchemy.

## Features

- Modern dark desktop UI
- Configuration management from JSON
- Structured logging with loguru
- SQLite-backed database initialization
- Multi-language support for English, Hindi, and Telugu
- Dashboard layout with market, broker, portfolio, and risk indicators

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

```text
ASG/
├── main.py
├── requirements.txt
├── README.md
├── config/
├── database/
├── logs/
├── src/
│   ├── app.py
│   ├── core/
│   ├── ui/
│   ├── localization/
│   └── ...
```
