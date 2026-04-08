import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApprovalModal } from "../components/ApprovalModal";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getApprovalsWebSocketUrl: vi.fn(() => "ws://localhost/ws"),
  respondToApproval: vi.fn(),
}));

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: () => void = () => {};
  onmessage: (e: MessageEvent) => void = () => {};
  onclose: () => void = () => {};
  onerror: (e: Event) => void = () => {};
  close = vi.fn();
  send = vi.fn();
  readyState = 1;

  constructor(url: string) {
    MockWebSocket.instances.push(this);
    // Simulate connection
    setTimeout(() => this.onopen(), 10);
  }
}

(MockWebSocket as any).CONNECTING = 0;
(MockWebSocket as any).OPEN = 1;
(MockWebSocket as any).CLOSING = 2;
(MockWebSocket as any).CLOSED = 3;

global.WebSocket = MockWebSocket as unknown as typeof WebSocket;

describe("ApprovalModal Component", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing initially", () => {
    const { container } = render(<ApprovalModal />);
    expect(container.firstChild).toBeNull();
  });

  it("shows modal when receiving approval request and calls respondToApproval", async () => {
    render(<ApprovalModal />);

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0]!;
    await act(async () => {
      socket.onmessage({
        data: JSON.stringify({
          id: "a1",
          task_id: "42",
          description: "Ship the feature",
          agent: "architect",
          risk_level: "low",
        }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(screen.getByText("Authorization Required")).toBeTruthy();
      expect(screen.getByText("42")).toBeTruthy();
      expect(screen.getByText("Ship the feature")).toBeTruthy();
    });

    await act(async () => {
      screen.getByRole("button", { name: /Authorize/i }).click();
    });

    await waitFor(() => {
      expect(api.respondToApproval).toHaveBeenCalledWith("a1", "approved");
    });
  });
});
