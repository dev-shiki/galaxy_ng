#!/bin/bash
set -e

# Upgrade pip and install wheel
python -m pip install --upgrade pip setuptools wheel

# Install test dependencies
pip install tox tox-gh-actions pytest pytest-cov coverage

# Install requirements files if they exist
for req_file in dev_requirements.txt unittest_requirements.txt lint_requirements.txt; do
  if [ -f "$req_file" ]; then
    echo "Installing dependencies from $req_file"
    pip install -r "$req_file" || echo "Warning: Some packages in $req_file failed to install"
  fi
done

# Install the package in development mode
# We use --no-deps to avoid reinstalling dependencies that might conflict
pip install --no-deps -e .

# Check if orionutils is required but not installed, try installing it separately
if grep -q "orionutils" *.txt 2>/dev/null || grep -q "orionutils" setup.py 2>/dev/null; then
  echo "Attempting to install orionutils separately"
  pip install orionutils || echo "Warning: orionutils installation failed, but continuing workflow"
fi

echo "Dependencies installation completed"