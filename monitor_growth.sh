#!/bin/bash
# Quick monitoring script for autonomous growth

echo "========================================================================"
echo "🔍 AUTONOMOUS GROWTH MONITOR"
echo "========================================================================"

# Check if daemon is running
if [ -f growth_daemon.pid ]; then
    PID=$(cat growth_daemon.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Growth daemon is RUNNING (PID: $PID)"
    else
        echo "❌ Growth daemon is NOT running (stale PID file)"
    fi
else
    echo "⚪ Growth daemon not started"
fi

echo ""
echo "📊 Current Dataset Stats:"
python check_dataset_stats.py | grep -E "(Total questions|Models selected|Total predictions|Average|High risk|Medium risk|Low risk)"

echo ""
echo "📝 Recent Log Activity (last 10 lines):"
if [ -f continuous_growth.log ]; then
    tail -10 continuous_growth.log
else
    echo "  No log file yet"
fi

echo ""
echo "========================================================================"
echo "Commands:"
echo "  Monitor logs:  tail -f continuous_growth.log"
echo "  Stop daemon:   kill \$(cat growth_daemon.pid) && rm growth_daemon.pid"
echo "  View stats:    python check_dataset_stats.py"
echo "  Manual run:    python autonomous_benchmark_grower.py 12000"
echo "========================================================================"
