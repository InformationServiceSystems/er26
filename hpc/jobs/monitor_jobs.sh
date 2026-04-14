#!/usr/bin/env bash
# Monitor HTCondor jobs for er26 formalization experiment
# Usage: ./monitor_jobs.sh [job_id1 job_id2 ...]
#        ./monitor_jobs.sh              # auto-discover all queued jobs
#        REFRESH=60 ./monitor_jobs.sh   # custom refresh interval

set -o pipefail

CLUSTER_USER="${CLUSTER_USER:-wolfgang.maass}"
CLUSTER_HOST="${CLUSTER_HOST:-conduit.hpc.uni-saarland.de}"
CLUSTER_DIR="${CLUSTER_DIR:-~/er26}"
REFRESH="${REFRESH:-30}"
LOG_DIR="hpc/logs"

# Colors
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' C='\033[0;36m' W='\033[1;37m' DIM='\033[2m' NC='\033[0m'

ssh_cmd() {
    ssh -o ConnectTimeout=10 -o BatchMode=yes "${CLUSTER_USER}@${CLUSTER_HOST}" "cd ${CLUSTER_DIR} && $1" 2>/dev/null
}

state_label() {
    case "$1" in
        1) echo "IDLE";;    2) echo "RUNNING";; 3) echo "REMOVED";;
        4) echo "DONE";;    5) echo "HELD";;    6) echo "XFER";;
        7) echo "SUSPEND";; *) echo "?";;
    esac
}
state_color() {
    case "$1" in
        RUNNING|DONE) echo -e "${G}";;
        IDLE|XFER|SUSPEND) echo -e "${Y}";;
        *) echo -e "${R}";;
    esac
}

# Lookup value from a "key|value" list stored in a temp file
# Usage: lookup_kv /tmp/file key
lookup_kv() {
    local file="$1" key="$2"
    grep "^${key}|" "$file" 2>/dev/null | head -1 | sed "s/^${key}|//"
}

# Main monitor loop
monitor() {
    local iteration=0
    local ids_arg="$*"

    while true; do
        clear
        echo -e "${B}================================================================${NC}"
        echo -e "${W} er26 — HPC Monitor${NC}  $(date '+%Y-%m-%d %H:%M:%S')"
        echo -e "${B}================================================================${NC}"
        echo ""

        # Build the IDS logic for the remote side
        local ids_block
        if [ -n "$ids_arg" ]; then
            ids_block="IDS='${ids_arg}'"
        else
            ids_block='IDS=$(condor_q -nobatch 2>/dev/null | awk '"'"'NR>4 && NF>=7 && $1 ~ /^[0-9]/ {split($1,a,"."); print a[1]}'"'"' | sort -un | tr "\n" " ")
            if [ -z "$IDS" ]; then
                IDS=$(condor_history -limit 8 -format "%d\n" ClusterId 2>/dev/null | sort -rn | uniq | tr "\n" " ")
            fi'
        fi

        # ── Collect all data in ONE SSH call ──
        local all_data
        all_data=$(ssh_cmd "${ids_block}

            echo '===JOBS==='
            for cid in \$IDS; do
                LINE=\$(condor_q \$cid -format '%d|' ClusterId -format '%s|' Cmd -format '%d|' JobStatus -format '%s\n' RemoteWallClockTime -nobatch 2>/dev/null | head -1)
                if [ -n \"\$LINE\" ]; then
                    echo \"\$LINE\"
                else
                    HLINE=\$(condor_history \$cid -limit 1 -format '%d|' ClusterId -format '%s|' Cmd -format '%d|' ExitCode -format 'hist\n' -nobatch 2>/dev/null | head -1)
                    [ -n \"\$HLINE\" ] && echo \"\$HLINE\"
                fi
            done

            echo '===PROGRESS==='
            for cid in \$IDS; do
                OUT=\$(ls ${LOG_DIR}/*_\${cid}.out 2>/dev/null | head -1)
                if [ -z \"\$OUT\" ] || [ ! -s \"\$OUT\" ]; then
                    echo \"\${cid}|No output yet\"
                    continue
                fi

                if grep -q 'Traceback (most recent call last)' \"\$OUT\" 2>/dev/null; then
                    ERR_LINE=\$(grep -E 'Error:|Exception:' \"\$OUT\" 2>/dev/null | tail -1 | head -c 120)
                    echo \"\${cid}|FAILED: \${ERR_LINE}\"
                    continue
                fi

                if grep -q 'Completed!' \"\$OUT\" 2>/dev/null; then
                    RESULT=\$(grep 'Completed!' \"\$OUT\" | tail -1 | head -c 120)
                    echo \"\${cid}|DONE: \${RESULT}\"
                    continue
                fi

                EXIT_LINE=\$(grep 'exit code:' \"\$OUT\" 2>/dev/null | tail -1)
                if [ -n \"\$EXIT_LINE\" ]; then
                    CODE=\$(echo \"\$EXIT_LINE\" | grep -oE '[0-9]+\$')
                    if [ \"\$CODE\" = '0' ]; then
                        echo \"\${cid}|DONE (exit 0)\"
                    else
                        echo \"\${cid}|FAILED (exit \$CODE)\"
                    fi
                    continue
                fi

                TQDM=\$(grep -oE 'Processing tasks:.*' \"\$OUT\" 2>/dev/null | tail -1 | tr '\r' '\n' | grep -v '^\$' | tail -1 | sed 's/\x1b\[[0-9;]*m//g' | head -c 120)
                if [ -n \"\$TQDM\" ]; then
                    echo \"\${cid}|\${TQDM}\"
                    continue
                fi

                if grep -q 'Model loaded' \"\$OUT\" 2>/dev/null; then
                    echo \"\${cid}|Model loaded, generating...\"
                elif grep -q 'Loading model' \"\$OUT\" 2>/dev/null; then
                    echo \"\${cid}|Loading model...\"
                elif grep -q 'Successfully installed' \"\$OUT\" 2>/dev/null; then
                    echo \"\${cid}|Deps installed, starting...\"
                elif grep -q 'Installing collected' \"\$OUT\" 2>/dev/null; then
                    echo \"\${cid}|Installing dependencies...\"
                else
                    LAST=\$(tail -3 \"\$OUT\" | grep -v '^\$' | tail -1 | head -c 120)
                    echo \"\${cid}|\${LAST:-(starting...)}\"
                fi
            done

            echo '===ERRORS==='
            for cid in \$IDS; do
                ERR=\$(ls ${LOG_DIR}/*_\${cid}.err 2>/dev/null | head -1)
                if [ -n \"\$ERR\" ] && [ -s \"\$ERR\" ]; then
                    REAL=\$(grep -v 'DEPRECATION\|notice\|WARNING\|^\$' \"\$ERR\" 2>/dev/null | tail -3)
                    if [ -n \"\$REAL\" ]; then
                        echo \"\${cid}|HAS_ERRORS\"
                        echo \"\$REAL\" | while IFS= read -r eline; do
                            echo \"\${cid}|  \$eline\"
                        done
                    fi
                fi
            done

            echo '===RESULTS==='
            ls -lh data/results_raw/*.jsonl 2>/dev/null | awk '{printf \"%s %s %s %s\n\", \$NF, \$5, \$6, \$7}'
            echo '===LINECOUNTS==='
            wc -l data/results_raw/*.jsonl 2>/dev/null
        ")

        # ── Parse sections using temp files (Bash 3.2 compatible) ──
        local section=""
        local progress_file="/tmp/er26_progress_$$"
        local errors_file="/tmp/er26_errors_$$"
        local results_file="/tmp/er26_results_$$"
        local counts_file="/tmp/er26_counts_$$"
        local jobs_file="/tmp/er26_jobs_$$"

        rm -f "$progress_file" "$errors_file" "$results_file" "$counts_file" "$jobs_file" 2>/dev/null
        touch "$progress_file" "$errors_file" "$jobs_file"

        while IFS= read -r line; do
            case "$line" in
                '===JOBS===')       section="jobs";;
                '===PROGRESS===')   section="progress";;
                '===ERRORS===')     section="errors";;
                '===RESULTS===')    section="results";;
                '===LINECOUNTS===') section="counts";;
                *)
                    case "$section" in
                        jobs)     [ -n "$line" ] && echo "$line" >> "$jobs_file";;
                        progress) [ -n "$line" ] && echo "$line" >> "$progress_file";;
                        errors)   [ -n "$line" ] && echo "$line" >> "$errors_file";;
                        results)  [ -n "$line" ] && echo -e "  ${DIM}${line}${NC}" >> "$results_file";;
                        counts)   [ -n "$line" ] && echo "  $line" >> "$counts_file";;
                    esac
                    ;;
            esac
        done <<< "$all_data"

        # ── Display jobs ──
        local job_count
        job_count=$(wc -l < "$jobs_file" | tr -d ' ')

        if [ "$job_count" -eq 0 ]; then
            echo -e "  ${Y}No jobs found.${NC}"
        else
            printf "  ${Y}%-7s %-22s %-10s %-14s  %s${NC}\n" "ID" "Job" "State" "Runtime" "Progress"
            printf "  ${DIM}%-7s %-22s %-10s %-14s  %s${NC}\n" "-------" "----------------------" "----------" "--------------" "--------------------"

            while IFS= read -r jline; do
                IFS='|' read -r j_cid j_cmd j_state j_runtime <<< "$jline"

                local jname
                jname=$(basename "$j_cmd" .sh)
                jname="${jname#run_}"

                if [ "$j_runtime" = "hist" ]; then
                    if [ "$j_state" = "0" ]; then
                        j_state="4"
                    else
                        j_state="3"
                    fi
                    j_runtime="(finished)"
                fi

                local slabel scolor
                slabel=$(state_label "$j_state")
                scolor=$(state_color "$slabel")

                local prog pcolor
                prog=$(lookup_kv "$progress_file" "$j_cid")
                pcolor="${C}"
                if echo "$prog" | grep -q "^FAILED"; then
                    pcolor="${R}"
                elif echo "$prog" | grep -q "^DONE"; then
                    pcolor="${G}"
                fi

                printf "  ${W}%-7s${NC} %-22s ${scolor}%-10s${NC} %-14s  ${pcolor}%s${NC}\n" \
                    "$j_cid" "$jname" "$slabel" "$j_runtime" "$prog"

                # Show errors if any
                local has_err
                has_err=$(grep "^${j_cid}|HAS_ERRORS" "$errors_file" 2>/dev/null)
                if [ -n "$has_err" ]; then
                    grep "^${j_cid}|  " "$errors_file" 2>/dev/null | while IFS= read -r eline; do
                        local emsg="${eline#*|}"
                        [ -n "$emsg" ] && printf "         ${R}%s${NC}\n" "$emsg"
                    done
                fi
            done < "$jobs_file"
        fi

        # ── Results ──
        echo ""
        echo -e "${B}--- Results (data/results_raw/) ---${NC}"
        if [ -s "$results_file" ]; then
            cat "$results_file"
            echo ""
            [ -s "$counts_file" ] && cat "$counts_file"
        else
            echo -e "  ${Y}No result files yet.${NC}"
        fi

        rm -f "$progress_file" "$errors_file" "$results_file" "$counts_file" "$jobs_file" 2>/dev/null

        iteration=$((iteration + 1))
        echo ""
        echo -e "${C}Refresh #${iteration} | Next in ${REFRESH}s | Ctrl+C to stop${NC}"
        sleep "$REFRESH"
    done
}

# Cleanup temp files on exit
trap 'rm -f /tmp/er26_progress_$$ /tmp/er26_errors_$$ /tmp/er26_results_$$ /tmp/er26_counts_$$ /tmp/er26_jobs_$$ 2>/dev/null' EXIT

# Parse args
IDS_ARG=""
for arg in "$@"; do
    id=$(echo "$arg" | tr -cd '0-9')
    [ -n "$id" ] && IDS_ARG="$IDS_ARG $id"
done

monitor $IDS_ARG
