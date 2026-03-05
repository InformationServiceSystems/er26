#!/bin/bash
# monitor_progress.sh - Monitor experiment progress

echo "=== Experiment Progress Monitor ==="
echo ""

# Check if process is running
if ps aux | grep -q "[r]un_with_model"; then
    echo "✓ Experiment is RUNNING"
    echo ""
else
    echo "✗ No experiment running"
    exit 1
fi

# Show last 30 lines of terminal output
echo "--- Last 30 lines of output ---"
tail -n 30 /home/wmaass/.cursor/projects/home-wmaass-Dokumente-github-ER26/terminals/1.txt 2>/dev/null || echo "No output yet"

echo ""
echo "--- Log file (if exists) ---"
tail -n 10 logs/mistral_high_formal.log 2>/dev/null || echo "No log file yet"

echo ""
echo "To monitor live: tail -f /home/wmaass/.cursor/projects/home-wmaass-Dokumente-github-ER26/terminals/1.txt"

