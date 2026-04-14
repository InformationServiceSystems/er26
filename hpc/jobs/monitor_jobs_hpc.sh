#!/usr/bin/env bash
# Monitor HTCondor jobs for er26 — run directly on HPC
# Usage: ./monitor_jobs_hpc.sh [job_id1 job_id2 ...]
#        ./monitor_jobs_hpc.sh              # auto-discover all queued jobs
#        REFRESH=60 ./monitor_jobs_hpc.sh   # custom refresh interval

set -o pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/er26}"
REFRESH="${REFRESH:-30}"
LOG_DIR="hpc/logs"

cd "$PROJECT_DIR" || { echo "Cannot cd to $PROJECT_DIR"; exit 1; }

# Colors
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' C='\033[0;36m' W='\033[1;37m' DIM='\033[2m' NC='\033[0m'

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

human_time() {
    local secs="$1"
    secs="${secs%.*}"
    if [ -z "$secs" ] || [ "$secs" = "0" ]; then
        echo "0s"
        return
    fi
    local h=$((secs / 3600))
    local m=$(( (secs % 3600) / 60 ))
    local s=$((secs % 60))
    if [ "$h" -gt 0 ]; then
        printf "%dh %dm %ds" "$h" "$m" "$s"
    elif [ "$m" -gt 0 ]; then
        printf "%dm %ds" "$m" "$s"
    else
        printf "%ds" "$s"
    fi
}

human_size() {
    local file="$1"
    if [ ! -f "$file" ]; then echo "—"; return; fi
    local bytes
    bytes=$(wc -c < "$file" 2>/dev/null | tr -d ' ')
    if [ "$bytes" -ge 1048576 ]; then
        echo "$((bytes / 1048576))M"
    elif [ "$bytes" -ge 1024 ]; then
        echo "$((bytes / 1024))K"
    else
        echo "${bytes}B"
    fi
}

lookup_kv() {
    local file="$1" key="$2"
    grep "^${key}|" "$file" 2>/dev/null | head -1 | sed "s/^${key}|//"
}

monitor() {
    local iteration=0
    local ids_arg="$*"

    while true; do
        clear
        echo -e "${B}════════════════════════════════════════════════════════════════${NC}"
        echo -e "${W} er26 — HPC Monitor${NC}  $(date '+%Y-%m-%d %H:%M:%S')"
        echo -e "${B}════════════════════════════════════════════════════════════════${NC}"
        echo ""

        # ── Discover job IDs ──
        local IDS
        if [ -n "$ids_arg" ]; then
            IDS="$ids_arg"
        else
            IDS=$(condor_q -nobatch 2>/dev/null | awk 'NR>4 && NF>=7 && $1 ~ /^[0-9]/ {split($1,a,"."); print a[1]}' | sort -un | tr "\n" " ")
            if [ -z "$IDS" ]; then
                IDS=$(condor_history -limit 8 -format "%d\n" ClusterId 2>/dev/null | sort -rn | uniq | tr "\n" " ")
            fi
        fi

        # ── Collect job info ──
        local jobs_file="/tmp/er26_jobs_$$"
        local progress_file="/tmp/er26_progress_$$"
        local errors_file="/tmp/er26_errors_$$"
        local detail_file="/tmp/er26_detail_$$"
        rm -f "$jobs_file" "$progress_file" "$errors_file" "$detail_file" 2>/dev/null
        touch "$jobs_file" "$progress_file" "$errors_file" "$detail_file"

        for cid in $IDS; do
            # Job status + host
            LINE=$(condor_q "$cid" -format '%d|' ClusterId -format '%s|' Cmd -format '%d|' JobStatus -format '%s|' RemoteWallClockTime -format '%s\n' RemoteHost -nobatch 2>/dev/null | head -1)
            if [ -n "$LINE" ]; then
                echo "$LINE" >> "$jobs_file"
            else
                HLINE=$(condor_history "$cid" -limit 1 -format '%d|' ClusterId -format '%s|' Cmd -format '%d|' ExitCode -format 'hist|' -format '%s\n' LastRemoteHost -nobatch 2>/dev/null | head -1)
                [ -n "$HLINE" ] && echo "$HLINE" >> "$jobs_file"
            fi

            # Log file details
            OUT=$(ls ${LOG_DIR}/*_${cid}.out 2>/dev/null | head -1)
            ERR=$(ls ${LOG_DIR}/*_${cid}.err 2>/dev/null | head -1)
            LOG=$(ls ${LOG_DIR}/*_${cid}.log 2>/dev/null | head -1)

            local out_info="—" err_info="—" log_info="—"
            if [ -n "$OUT" ] && [ -f "$OUT" ]; then
                out_info="$(human_size "$OUT") $(wc -l < "$OUT" | tr -d ' ')L"
            fi
            if [ -n "$ERR" ] && [ -f "$ERR" ]; then
                err_info="$(human_size "$ERR") $(wc -l < "$ERR" | tr -d ' ')L"
            fi
            if [ -n "$LOG" ] && [ -f "$LOG" ]; then
                log_info="$(human_size "$LOG") $(wc -l < "$LOG" | tr -d ' ')L"
            fi
            echo "${cid}|${out_info}|${err_info}|${log_info}" >> "$detail_file"

            # Progress from .out file
            if [ -z "$OUT" ] || [ ! -s "$OUT" ]; then
                echo "${cid}|No output yet" >> "$progress_file"
                continue
            fi

            if grep -q 'Traceback (most recent call last)' "$OUT" 2>/dev/null; then
                ERR_LINE=$(grep -E 'Error:|Exception:' "$OUT" 2>/dev/null | tail -1 | head -c 120)
                echo "${cid}|FAILED: ${ERR_LINE}" >> "$progress_file"
            elif grep -q 'Completed!' "$OUT" 2>/dev/null; then
                RESULT=$(grep 'Completed!' "$OUT" | tail -1 | head -c 120)
                echo "${cid}|DONE: ${RESULT}" >> "$progress_file"
            elif grep -q 'exit code:' "$OUT" 2>/dev/null; then
                EXIT_LINE=$(grep 'exit code:' "$OUT" | tail -1)
                CODE=$(echo "$EXIT_LINE" | grep -oE '[0-9]+$')
                if [ "$CODE" = "0" ]; then
                    echo "${cid}|DONE (exit 0)" >> "$progress_file"
                else
                    echo "${cid}|FAILED (exit $CODE)" >> "$progress_file"
                fi
            else
                TQDM=$(grep -oE 'Processing tasks:.*' "$OUT" 2>/dev/null | tail -1 | tr '\r' '\n' | grep -v '^$' | tail -1 | sed 's/\x1b\[[0-9;]*m//g' | head -c 120)
                if [ -n "$TQDM" ]; then
                    echo "${cid}|${TQDM}" >> "$progress_file"
                elif grep -q 'Model loaded' "$OUT" 2>/dev/null; then
                    echo "${cid}|Model loaded, generating..." >> "$progress_file"
                elif grep -q 'Loading model' "$OUT" 2>/dev/null; then
                    echo "${cid}|Loading model..." >> "$progress_file"
                elif grep -q 'Successfully installed' "$OUT" 2>/dev/null; then
                    echo "${cid}|Deps installed, starting..." >> "$progress_file"
                elif grep -q 'Installing collected' "$OUT" 2>/dev/null; then
                    echo "${cid}|Installing dependencies..." >> "$progress_file"
                else
                    LAST=$(tail -3 "$OUT" | grep -v '^$' | tail -1 | head -c 120)
                    echo "${cid}|${LAST:-(starting...)}" >> "$progress_file"
                fi
            fi

            # Errors from .err file
            if [ -n "$ERR" ] && [ -s "$ERR" ]; then
                REAL=$(grep -cv 'DEPRECATION\|notice\|WARNING\|^$' "$ERR" 2>/dev/null)
                if [ "$REAL" -gt 0 ] 2>/dev/null; then
                    echo "${cid}|HAS_ERRORS" >> "$errors_file"
                    grep -v 'DEPRECATION\|notice\|WARNING\|^$' "$ERR" 2>/dev/null | tail -3 | while IFS= read -r eline; do
                        echo "${cid}|  $eline" >> "$errors_file"
                    done
                fi
            fi
        done

        # ── Display jobs ──
        local job_count
        job_count=$(wc -l < "$jobs_file" | tr -d ' ')

        if [ "$job_count" -eq 0 ]; then
            echo -e "  ${Y}No jobs found.${NC}"
        else
            while IFS= read -r jline; do
                IFS='|' read -r j_cid j_cmd j_state j_runtime j_host <<< "$jline"

                local jname
                jname=$(basename "$j_cmd" .sh)
                jname="${jname#run_}"

                local is_hist=""
                if [ "$j_runtime" = "hist" ]; then
                    is_hist="1"
                    if [ "$j_state" = "0" ]; then
                        j_state="4"
                    else
                        j_state="3"
                    fi
                    j_runtime="(finished)"
                else
                    j_runtime=$(human_time "$j_runtime")
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

                # Extract host short name
                local host_short="—"
                if [ -n "$j_host" ] && [ "$j_host" != "undefined" ]; then
                    host_short=$(echo "$j_host" | sed 's/slot[0-9_]*@//;s/\.hpc\.uni-saarland\.de//')
                fi

                echo -e "  ${W}${j_cid}${NC}  ${C}${jname}${NC}"
                echo -e "    State: ${scolor}${slabel}${NC}  |  Runtime: ${W}${j_runtime}${NC}  |  Host: ${W}${host_short}${NC}"

                # File info
                local finfo
                finfo=$(lookup_kv "$detail_file" "$j_cid")
                if [ -n "$finfo" ]; then
                    IFS='|' read -r f_out f_err f_log <<< "$finfo"
                    echo -e "    Files: .out=${DIM}${f_out}${NC}  .err=${DIM}${f_err}${NC}  .log=${DIM}${f_log}${NC}"
                fi

                # Progress
                echo -e "    Activity: ${pcolor}${prog}${NC}"

                # Show errors
                local has_err
                has_err=$(grep "^${j_cid}|HAS_ERRORS" "$errors_file" 2>/dev/null)
                if [ -n "$has_err" ]; then
                    grep "^${j_cid}|  " "$errors_file" 2>/dev/null | while IFS= read -r eline; do
                        local emsg="${eline#*|}"
                        [ -n "$emsg" ] && echo -e "    ${R}${emsg}${NC}"
                    done
                fi

                # Last 2 lines of stdout (live tail)
                local outfile
                outfile=$(ls ${LOG_DIR}/*_${j_cid}.out 2>/dev/null | head -1)
                if [ -n "$outfile" ] && [ -s "$outfile" ]; then
                    echo -e "    ${DIM}── last output ──${NC}"
                    tail -2 "$outfile" | grep -v '^$' | while IFS= read -r tline; do
                        echo -e "    ${DIM}$(echo "$tline" | head -c 100)${NC}"
                    done
                fi

                echo ""
            done < "$jobs_file"
        fi

        # ── Results ──
        echo -e "${B}── Results (data/results_raw/) ──${NC}"
        if ls data/results_raw/*.jsonl >/dev/null 2>&1; then
            printf "  ${Y}%-45s %8s %8s${NC}\n" "File" "Size" "Lines"
            printf "  ${DIM}%-45s %8s %8s${NC}\n" "─────────────────────────────────────────────" "────────" "────────"
            for f in data/results_raw/*.jsonl; do
                local fname fsize flines
                fname=$(basename "$f")
                fsize=$(human_size "$f")
                flines=$(wc -l < "$f" | tr -d ' ')
                printf "  %-45s %8s %8s\n" "$fname" "$fsize" "$flines"
            done
        else
            echo -e "  ${Y}No result files yet.${NC}"
        fi

        rm -f "$jobs_file" "$progress_file" "$errors_file" "$detail_file" 2>/dev/null

        iteration=$((iteration + 1))
        echo ""
        echo -e "${C}Refresh #${iteration} | Next in ${REFRESH}s | Ctrl+C to stop${NC}"
        sleep "$REFRESH"
    done
}

trap 'rm -f /tmp/er26_jobs_$$ /tmp/er26_progress_$$ /tmp/er26_errors_$$ /tmp/er26_detail_$$ 2>/dev/null' EXIT

IDS_ARG=""
for arg in "$@"; do
    id=$(echo "$arg" | tr -cd '0-9')
    [ -n "$id" ] && IDS_ARG="$IDS_ARG $id"
done

monitor $IDS_ARG
