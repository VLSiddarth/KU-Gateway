#!/bin/bash
export $(cat .env | xargs)
uvicorn ku_gateway.main:app --host 0.0.0.0 --port 8000 --reload