// ApprovalWidget.js - Vanilla JS version for current dashboard
class ApprovalWidget {
    constructor(containerId, orchestratorUrl = 'ws://localhost:8080/ws/approvals') {
        this.container = document.getElementById(containerId);
        this.orchestratorUrl = orchestratorUrl;
        this.approvals = [];
        this.init();
    }

    init() {
        this.render();
        this.connectWebSocket();
    }

    connectWebSocket() {
        this.ws = new WebSocket(this.orchestratorUrl);
        
        this.ws.onopen = () => {
            console.log('✅ Connected to Approval System');
            this.updateStatus('Connected', 'green');
        };

        this.ws.onmessage = (event) => {
            const approval = JSON.parse(event.data);
            this.addApproval(approval);
        };

        this.ws.onclose = () => {
            console.log('❌ Disconnected from Approval System');
            this.updateStatus('Disconnected', 'red');
            setTimeout(() => this.connectWebSocket(), 5000); // Reconnect
        };
    }

    addApproval(approval) {
        // Avoid duplicates
        if (!this.approvals.find(a => a.id === approval.id)) {
            this.approvals.push(approval);
            this.render();
            this.playNotification();
        }
    }

    removeApproval(id) {
        this.approvals = this.approvals.filter(a => a.id !== id);
        this.render();
    }

    async respond(id, status, modifications = null) {
        try {
            await fetch('http://localhost:8080/approvals/respond', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    approval_id: id,
                    status: status,
                    modifications: modifications
                })
            });
            this.removeApproval(id);
        } catch (error) {
            console.error('Failed to respond:', error);
            alert('Failed to send response. Check console.');
        }
    }

    playNotification() {
        // Simple beep or visual cue
        if (window.Notification && Notification.permission === "granted") {
            new Notification("New Approval Request");
        }
    }

    updateStatus(text, color) {
        const statusEl = document.getElementById('approval-status');
        if (statusEl) {
            statusEl.innerText = text;
            statusEl.style.color = color;
        }
    }

    render() {
        if (!this.container) return;

        if (this.approvals.length === 0) {
            this.container.innerHTML = '<div class="text-gray-500 text-center p-4">No pending approvals</div>';
            return;
        }

        this.container.innerHTML = this.approvals.map(approval => `
            <div class="bg-gray-800 border border-blue-500 rounded p-4 mb-4 shadow-lg">
                <div class="flex justify-between items-center mb-2">
                    <span class="font-bold text-blue-400">${approval.agent}</span>
                    <span class="text-xs text-gray-400">${new Date(approval.created_at).toLocaleTimeString()}</span>
                </div>
                <div class="mb-2">
                    <span class="bg-blue-900 text-xs px-2 py-1 rounded text-white">${approval.action_type}</span>
                </div>
                <pre class="bg-black p-2 rounded text-xs text-green-400 overflow-x-auto mb-4 max-h-40">
${JSON.stringify(approval.details, null, 2)}
                </pre>
                <div class="flex gap-2">
                    <button onclick="approvalWidget.respond('${approval.id}', 'approved')" 
                        class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm flex-1">
                        ✅ Approve
                    </button>
                    <button onclick="approvalWidget.respond('${approval.id}', 'rejected')" 
                        class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm flex-1">
                        ❌ Reject
                    </button>
                </div>
            </div>
        `).join('');
    }
}

// Global instance
window.approvalWidget = null;
document.addEventListener('DOMContentLoaded', () => {
    window.approvalWidget = new ApprovalWidget('approval-container');
});
