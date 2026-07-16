import csv
import os
from datetime import datetime

USAGE_CSV = "token_usage.csv"

def init_usage_file():
    """Create CSV file with headers if it doesn't exist."""
    if not os.path.exists(USAGE_CSV):
        with open(USAGE_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "question",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "model"
            ])

def log_usage(question: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, model: str):
    """Append a usage record to the CSV file."""
    init_usage_file()
    with open(USAGE_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            question[:100],  # truncate long questions
            prompt_tokens,
            completion_tokens,
            total_tokens,
            model
        ])

def get_total_usage_today():
    """Calculate total tokens used today."""
    init_usage_file()
    today = datetime.now().date()
    total = 0
    with open(USAGE_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_date = datetime.fromisoformat(row['timestamp']).date()
            if row_date == today:
                total += int(row['total_tokens'])
    return total

def get_usage_summary():
    """Return a summary of all usage."""
    init_usage_file()
    total_tokens = 0
    total_requests = 0
    with open(USAGE_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_tokens += int(row['total_tokens'])
            total_requests += 1
    return {"total_tokens": total_tokens, "total_requests": total_requests}