#!/bin/bash
# ARIS Environment Setup Script
export PYTHONPATH=/mnt/projects/aris-tool/src:$PYTHONPATH
source .venv/bin/activate
echo "✅ ARIS environment activated"
echo "PYTHONPATH: $PYTHONPATH"
echo "Python: $(which python)"
echo "Python version: $(python --version)"
