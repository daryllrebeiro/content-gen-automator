/**
 * Grafana Faro Frontend Real User Monitoring (RUM) Telemetry.
 * Tracks Director user experience, time-to-approve scenes, and drop-off funnels.
 */

export interface FaroTelemetryEvent {
  name: string;
  attributes?: Record<string, string | number | boolean>;
  timestamp?: number;
}

class GrafanaFaroTracker {
  private enabled: boolean = false;

  constructor() {
    if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_FARO_COLLECTOR_URL) {
      this.enabled = true;
      console.log("🔭 [Grafana Faro] Initialized RUM Telemetry.");
    }
  }

  public trackUserAction(name: string, attributes: Record<string, string | number | boolean> = {}) {
    if (!this.enabled) return;
    try {
      fetch(process.env.NEXT_PUBLIC_FARO_COLLECTOR_URL!, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "event",
          event: {
            name,
            attributes: { ...attributes, url: window.location.href },
            timestamp: Date.now(),
          },
        }),
      });
    } catch (e) {
      // Non-blocking telemetry
    }
  }

  public trackStageApproval(stage: string, durationSeconds: number) {
    this.trackUserAction("director_stage_approved", {
      stage,
      time_to_approve_sec: durationSeconds,
    });
  }
}

export const faroTracker = new GrafanaFaroTracker();
