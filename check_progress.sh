#!/bin/bash
echo "Tasks completed: $(wc -l < data/results_raw/high_formal_mistral_7b.jsonl 2>/dev/null || echo 0)/100"
echo "File size: $(ls -lh data/results_raw/high_formal_mistral_7b.jsonl 2>/dev/null | awk '{print $5}')"
echo "CPU usage: $(ps aux | grep 878944 | grep -v grep | awk '{print $3}')%"
echo "Runtime: $(ps -p 878944 -o etime= 2>/dev/null || echo 'N/A')"
