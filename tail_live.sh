#!/bin/bash
# tail_live.sh - Simple live tail with color highlighting

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              LIVE OUTPUT - Following terminal output               ║${NC}"
echo -e "${BLUE}║                    Press Ctrl+C to stop                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Follow terminal output with color highlighting
tail -f /home/wmaass/.cursor/projects/home-wmaass-Dokumente-github-ER26/terminals/1.txt 2>/dev/null | \
    while IFS= read -r line; do
        # Highlight progress bars
        if [[ "$line" =~ "Processing tasks" ]] || [[ "$line" =~ "%" ]]; then
            echo -e "${GREEN}$line${NC}"
        # Highlight completions
        elif [[ "$line" =~ "Completed" ]] || [[ "$line" =~ "✓" ]]; then
            echo -e "${YELLOW}$line${NC}"
        # Highlight errors
        elif [[ "$line" =~ "Error" ]] || [[ "$line" =~ "Failed" ]]; then
            echo -e "${RED}$line${NC}"
        # Highlight loading
        elif [[ "$line" =~ "Loading" ]]; then
            echo -e "${BLUE}$line${NC}"
        else
            echo "$line"
        fi
    done

