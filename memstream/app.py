from flask import Flask, request, jsonify
import os
import time
from threading import Lock

app = Flask(__name__)

# Simple in-memory state
state = {
    "ram_used_percent": 45.0,
    "ram_free_gb": 4.2,
    "tokens_per_sec": 0.0,
    "current_mode": "idle",
    "pressure": "🟢 LOW",
    "timestamp": time.time()
}
state_lock = Lock()

@app.route('/health/memstream', methods=['GET'])
def health_memstream():
    with state_lock:
        # Update timestamp
        state["timestamp"] = time.time()
        return jsonify(state)

@app.route('/throttle', methods=['POST'])
def throttle():
    data = request.get_json()
    if not data or 'delay_ms' not in data:
        return jsonify({"error": "Missing delay_ms"}), 400

    delay_ms = data['delay_ms']
    # In a real implementation, this would affect inference speed
    # For our mock, we just acknowledge it
    app.logger.info(f"Received throttle command: {delay_ms}ms delay")

    return jsonify({"ok": True, "delay_ms": delay_ms})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "memstream-mock"})

if __name__ == '__main__':
    port = int(os.getenv('MEMSTREAM_HEALTH_PORT', 8009))
    app.run(host='0.0.0.0', port=port, debug=False)