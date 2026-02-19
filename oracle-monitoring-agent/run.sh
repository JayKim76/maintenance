#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Run Agent
# Replace with your DB Creds
export DB_USER=system
export DB_PASSWORD=oracle
export DB_DSN=localhost/XE

python main.py
