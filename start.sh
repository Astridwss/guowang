#!/bin/bash
conda deactivate
cd ./api
python -m uvicorn main:app --host 0.0.0.0 --port 8000