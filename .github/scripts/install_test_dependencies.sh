#!/bin/bash
set -e

echo "Starting dependency installation..."

# Upgrade pip and install basic tools
python -m pip install --upgrade pip setuptools wheel
pip install tox tox-gh-actions pytest pytest-cov coverage

# Create a list of problematic packages that need special handling
SPECIAL_PACKAGES=(
  "pulp-smash"
  "orionutils"
)

# Function to check if a package is in the special list
is_special_package() {
  local pkg="$1"
  for special in "${SPECIAL_PACKAGES[@]}"; do
    if [[ "$pkg" == "$special" ]]; then
      return 0
    fi
  done
  return 1
}

# Handle pulp-smash installation from source
if grep -q "pulp-smash" *.txt 2>/dev/null || grep -q "pulp-smash" setup.py 2>/dev/null; then
  echo "Installing pulp-smash from source..."
  if [ ! -d "pulp-smash" ]; then
    git clone https://github.com/pulp/pulp-smash.git || echo "Warning: Failed to clone pulp-smash"
  fi
  
  if [ -d "pulp-smash" ]; then
    cd pulp-smash
    pip install -e . || echo "Warning: pulp-smash installation failed but continuing"
    cd ..
  fi
fi

# Process requirement files
for req_file in dev_requirements.txt unittest_requirements.txt lint_requirements.txt functest_requirements.txt integration_requirements.txt; do
  if [ -f "$req_file" ]; then
    echo "Processing $req_file..."
    
    # Create a filtered version without special packages
    filtered_file="${req_file}.filtered"
    > "$filtered_file"
    
    while IFS= read -r line || [[ -n "$line" ]]; do
      # Skip empty lines and comments
      if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
        echo "$line" >> "$filtered_file"
        continue
      fi
      
      # Extract package name (handle various formats like pkg==1.0, pkg>=1.0, etc.)
      pkg=$(echo "$line" | sed -E 's/([a-zA-Z0-9_.-]+).*$/\1/')
      
      if is_special_package "$pkg"; then
        echo "# Skipping special package: $line" >> "$filtered_file"
        echo "Skipping special package $pkg from $req_file"
      else
        echo "$line" >> "$filtered_file"
      fi
    done < "$req_file"
    
    # Install filtered requirements
    echo "Installing filtered requirements from $req_file..."
    pip install -r "$filtered_file" || echo "Warning: Some packages in $req_file failed to install"
  fi
done

# Finally, install the package itself in development mode
echo "Installing package in development mode..."
pip install --no-deps -e .

echo "Dependency installation completed"