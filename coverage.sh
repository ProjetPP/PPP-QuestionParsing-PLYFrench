#!/bin/bash
python3-coverage run --source=ppp_french_parser run_tests.py
python3-coverage html
xdg-open htmlcov/index.html
