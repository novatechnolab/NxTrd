#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║   Nxtrd — Persistent Background Termux Runner        ║
# ║   Runs server in tmux with auto-restart resilience.  ║
# ╚══════════════════════════════════════════════════════╝

# Prevent Android CPU sleep when screen is locked
termux-wake-lock 2>/dev/null || true

SESSION="nxtrd"
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$( cd -P "$( dirname "$SOURCE" )" &> /dev/null && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" &> /dev/null && pwd )"

# Kill existing session if any
tmux kill-session -t $SESSION 2>/dev/null || true

# Start background tmux session running nxtrd in an auto-restart loop
tmux new-session -d -s $SESSION -n "main" "cd \"$DIR\" && while true; do
  ./nxtrd
  echo -e '\n[!] Server stopped. Restarting in 3 seconds...'
  sleep 3
done"

echo -e "\033[1;32m✅ Nxtrd started in background tmux session '$SESSION'.\033[0m"
echo -e "   ➜ Attach to logs:  \033[1;33mtmux attach -t $SESSION\033[0m"
echo -e "   ➜ Detach screen:   \033[1;36mCtrl+b, then d\033[0m"
echo -e "   ➜ Stop server:     \033[1;31mtmux kill-session -t $SESSION\033[0m"
