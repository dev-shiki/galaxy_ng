#!/bin/bash
# Install all dependencies required for test generation and validation

# Core testing libraries
pip install pytest pytest-cov coverage[toml] tox tox-gh-actions

# API and networking libraries
pip install requests

# Data processing libraries
pip install numpy pandas

# Pulp-specific testing libraries
pip install pulp-smash

# Django and REST framework (likely already in requirements but ensuring they're here)
pip install django djangorestframework django-filter

# Handle problematic packages separately
pip install orionutils || echo "Warning: orionutils installation failed, but continuing workflow"

# Install any requirements files
for req_file in dev_requirements.txt unittest_requirements.txt lint_requirements.txt integration_requirements.txt; do
  if [ -f "$req_file" ]; then
    echo "Installing dependencies from $req_file"
    # Use --no-deps to avoid conflicts with already installed packages
    grep -v "pulp-smash\|orionutils" "$req_file" | xargs pip install -U || true
  fi
done

# Install the package in development mode
pip install -e .

echo "Dependencies installation completed"