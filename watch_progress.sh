#!/bin/bash
# watch_progress.sh - Continuous live monitoring with auto-refresh

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

while true; do
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         EXPERIMENT PROGRESS MONITOR - Live Updates                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check if process is running
    if ps aux | grep -q "[r]un_with_model"; then
        PID=$(ps aux | grep '[r]un_with_model' | awk 'NR==2{print $2}')
        echo -e "${GREEN}✓ Status: RUNNING${NC} (PID: $PID)"
        
        # CPU and Memory usage
        CPU=$(ps aux | grep '[r]un_with_model' | awk 'NR==2{print $3}')
        MEM=$(ps aux | grep '[r]un_with_model' | awk 'NR==2{print $4}')
        echo -e "${YELLOW}  CPU: ${CPU}% | Memory: ${MEM}%${NC}"
    else
        echo -e "${RED}✗ Status: NOT RUNNING${NC}"
        echo ""
        echo "Experiment may have completed or stopped."
        break
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Latest Output (last 25 lines):${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Show terminal output
    tail -n 25 /home/wmaass/.cursor/projects/home-wmaass-Dokumente-github-ER26/terminals/1.txt 2>/dev/null | \
        grep -E "Processing|Loading|Completed|tasks|%|it/s" || echo "Waiting for output..."
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check for completed results
    if [ -f "data/results_raw/high_formal_mistral_7b.jsonl" ]; then
        COUNT=$(wc -l < data/results_raw/high_formal_mistral_7b.jsonl)
        echo -e "${GREEN}✓ High-formal results: ${COUNT}/100 tasks${NC}"
    fi
    
    if [ -f "data/results_raw/semi_formal_mistral_7b.jsonl" ]; then
        COUNT=$(wc -l < data/results_raw/semi_formal_mistral_7b.jsonl)
        echo -e "${GREEN}✓ Semi-formal results: ${COUNT}/100 tasks${NC}"
    fi
    
    if [ -f "data/results_raw/low_formal_mistral_7b.jsonl" ]; then
        COUNT=$(wc -l < data/results_raw/low_formal_mistral_7b.jsonl)
        echo -e "${GREEN}✓ Low-formal results: ${COUNT}/100 tasks${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Refreshing in 3 seconds... (Press Ctrl+C to exit)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    sleep 3
done

echo ""
echo -e "${GREEN}Monitoring stopped.${NC}"

