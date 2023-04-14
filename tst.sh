#!/bin/bash

# exit when any command fails
set -e

python -m pytest test  --cov=package --junitxml=report.xml --cov-report html:coverage --cov-report term -v --color=yes
