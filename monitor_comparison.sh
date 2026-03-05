#!/bin/bash
# monitor_comparison.sh - Monitor Mistral vs Llama 3.1 comparison with 10s refresh

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to count completed tasks
count_tasks() {
    local file=$1
    if [ -f "$file" ]; then
        wc -l < "$file"
    else
        echo "0"
    fi
}

# Function to get percentage
get_percentage() {
    local completed=$1
    local total=100
    echo "scale=1; $completed * 100 / $total" | bc
}

while true; do
    clear
    
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   MISTRAL vs LLAMA 3.1 COMPARISON - 100 Use Cases per Task Type       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Get current timestamp
    echo -e "${CYAN}Last Update: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
    
    # Check if any experiment process is running
    RUNNING=0
    if ps aux | grep -q "[r]un.*model\|[p]ython.*scripts/run"; then
        RUNNING=1
        PID=$(ps aux | grep '[r]un.*model\|[p]ython.*scripts/run' | head -1 | awk '{print $2}')
        echo -e "${GREEN}✓ Status: EXPERIMENT RUNNING${NC} (PID: $PID)"
        
        # CPU and Memory usage
        CPU=$(ps aux | grep '[r]un.*model\|[p]ython.*scripts/run' | head -1 | awk '{print $3}')
        MEM=$(ps aux | grep '[r]un.*model\|[p]ython.*scripts/run' | head -1 | awk '{print $4}')
        echo -e "${YELLOW}  Resource Usage: CPU ${CPU}% | Memory: ${MEM}%${NC}"
    else
        echo -e "${RED}✗ Status: NO EXPERIMENT RUNNING${NC}"
        echo -e "${YELLOW}  (Experiments may have completed or not yet started)${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}                        MISTRAL 7B PROGRESS                             ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Mistral High-Formal
    MISTRAL_HIGH=$(count_tasks "data/results_raw/high_formal_mistral_7b.jsonl")
    MISTRAL_HIGH_PCT=$(get_percentage $MISTRAL_HIGH)
    if [ "$MISTRAL_HIGH" -eq 100 ]; then
        echo -e "${GREEN}✓ High-Formal (SQL):        ${MISTRAL_HIGH}/100 (${MISTRAL_HIGH_PCT}%) - COMPLETED${NC}"
    elif [ "$MISTRAL_HIGH" -gt 0 ]; then
        echo -e "${YELLOW}⟳ High-Formal (SQL):        ${MISTRAL_HIGH}/100 (${MISTRAL_HIGH_PCT}%) - IN PROGRESS${NC}"
    else
        echo -e "${RED}○ High-Formal (SQL):        ${MISTRAL_HIGH}/100 (0.0%) - PENDING${NC}"
    fi
    
    # Mistral Semi-Formal
    MISTRAL_SEMI=$(count_tasks "data/results_raw/semi_formal_mistral_7b.jsonl")
    MISTRAL_SEMI_PCT=$(get_percentage $MISTRAL_SEMI)
    if [ "$MISTRAL_SEMI" -eq 100 ]; then
        echo -e "${GREEN}✓ Semi-Formal (Extract):   ${MISTRAL_SEMI}/100 (${MISTRAL_SEMI_PCT}%) - COMPLETED${NC}"
    elif [ "$MISTRAL_SEMI" -gt 0 ]; then
        echo -e "${YELLOW}⟳ Semi-Formal (Extract):   ${MISTRAL_SEMI}/100 (${MISTRAL_SEMI_PCT}%) - IN PROGRESS${NC}"
    else
        echo -e "${RED}○ Semi-Formal (Extract):   ${MISTRAL_SEMI}/100 (0.0%) - PENDING${NC}"
    fi
    
    # Mistral Low-Formal
    MISTRAL_LOW=$(count_tasks "data/results_raw/low_formal_mistral_7b.jsonl")
    MISTRAL_LOW_PCT=$(get_percentage $MISTRAL_LOW)
    if [ "$MISTRAL_LOW" -eq 100 ]; then
        echo -e "${GREEN}✓ Low-Formal (Policy):     ${MISTRAL_LOW}/100 (${MISTRAL_LOW_PCT}%) - COMPLETED${NC}"
    elif [ "$MISTRAL_LOW" -gt 0 ]; then
        echo -e "${YELLOW}⟳ Low-Formal (Policy):     ${MISTRAL_LOW}/100 (${MISTRAL_LOW_PCT}%) - IN PROGRESS${NC}"
    else
        echo -e "${RED}○ Low-Formal (Policy):     ${MISTRAL_LOW}/100 (0.0%) - PENDING${NC}"
    fi
    
    MISTRAL_TOTAL=$((MISTRAL_HIGH + MISTRAL_SEMI + MISTRAL_LOW))
    echo -e "\n${CYAN}Total Mistral: ${MISTRAL_TOTAL}/300 tasks${NC}"
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}                       LLAMA 3.1 8B PROGRESS                           ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Llama High-Formal
    LLAMA_HIGH=$(count_tasks "data/results_raw/high_formal_llama_3_1_8b.jsonl")
    LLAMA_HIGH_PCT=$(get_percentage $LLAMA_HIGH)
    if [ "$LLAMA_HIGH" -eq 100 ]; then
        echo -e "${GREEN}✓ High-Formal (SQL):        ${LLAMA_HIGH}/100 (${LLAMA_HIGH_PCT}%) - COMPLETED${NC}"
    elif [ "$LLAMA_HIGH" -gt 0 ]; then
        echo -e "${YELLOW}⟳ High-Formal (SQL):        ${LLAMA_HIGH}/100 (${LLAMA_HIGH_PCT}%) - IN PROGRESS${NC}"
    else
        echo -e "${RED}○ High-Formal (SQL):        ${LLAMA_HIGH}/100 (0.0%) - PENDING${NC}"
    fi
    
    # Llama Semi-Formal
    LLAMA_SEMI=$(count_tasks "data/results_raw/semi_formal_llama_3_1_8b.jsonl")
    LLAMA_SEMI_PCT=$(get_percentage $LLAMA_SEMI)
    if [ "$LLAMA_SEMI" -eq 100 ]; then
        echo -e "${GREEN}✓ Semi-Formal (Extract):   ${LLAMA_SEMI}/100 (${LLAMA_SEMI_PCT}%) - COMPLETED${NC}"
    elif [ "$LLAMA_SEMI" -gt 0 ]; then
        echo -e "${YELLOW}⟳ Semi-Formal (Extract):   ${LLAMA_SEMI}/100 (${LLAMA_SEMI_PCT}%) - IN PROGRESS${NC}"
    else
        echo -e "${RED}○ Semi-Formal (Extract):   ${LLAMA_SEMI}/100 (0.0%) - PENDING${NC}"
    fi
    
    # Llama Low-Formal
    LLAMA_LOW=$(count_tasks "data/results_raw/low_formal_llama_3_1_8b.jsonl")
    LLAMA_LOW_PCT=$(get_percentage $LLAMA_LOW)
    if [ "$LLAMA_LOW" -eq 100 ]; then
        echo -e "${GREEN}✓ Low-Formal (Policy):     ${LLAMA_LOW}/100 (${LLAMA_LOW_PCT}%) - COMPLETED${NC}"
    elif [ "$LLAMA_LOW" -gt 0 ]; then
        echo -e "${YELLOW}⟳ Low-Formal (Policy):     ${LLAMA_LOW}/100 (${LLAMA_LOW_PCT}%) - IN PROGRESS${NC}"
    else
        echo -e "${RED}○ Low-Formal (Policy):     ${LLAMA_LOW}/100 (0.0%) - PENDING${NC}"
    fi
    
    LLAMA_TOTAL=$((LLAMA_HIGH + LLAMA_SEMI + LLAMA_LOW))
    echo -e "\n${CYAN}Total Llama: ${LLAMA_TOTAL}/300 tasks${NC}"
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}                         OVERALL PROGRESS                               ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    TOTAL_TASKS=$((MISTRAL_TOTAL + LLAMA_TOTAL))
    TOTAL_POSSIBLE=600
    OVERALL_PCT=$(echo "scale=1; $TOTAL_TASKS * 100 / $TOTAL_POSSIBLE" | bc)
    
    echo -e "${CYAN}Combined Progress: ${TOTAL_TASKS}/${TOTAL_POSSIBLE} tasks (${OVERALL_PCT}%)${NC}"
    
    # Progress bar
    PROGRESS_FILLED=$((TOTAL_TASKS * 60 / TOTAL_POSSIBLE))
    PROGRESS_EMPTY=$((60 - PROGRESS_FILLED))
    printf "${GREEN}"
    for i in $(seq 1 $PROGRESS_FILLED); do printf "█"; done
    printf "${RED}"
    for i in $(seq 1 $PROGRESS_EMPTY); do printf "░"; done
    printf "${NC}\n"
    
    echo ""
    
    # Latest terminal output (if running)
    if [ $RUNNING -eq 1 ]; then
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}Latest Console Output (last 10 lines):${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        # Try to find and tail the most recent terminal output
        LATEST_TERMINAL=$(ls -t /home/wmaass/.cursor/projects/home-wmaass-Dokumente-github-ER26/terminals/*.txt 2>/dev/null | head -1)
        if [ -n "$LATEST_TERMINAL" ]; then
            tail -n 10 "$LATEST_TERMINAL" 2>/dev/null | grep -E "Processing|Loading|Completed|tasks|%|it/s|Task|Model" || echo "  Waiting for output..."
        else
            echo "  No terminal output available yet..."
        fi
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Next refresh in 10 seconds... (Press Ctrl+C to exit)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    sleep 10
done

echo ""
echo -e "${GREEN}Monitoring stopped.${NC}"


