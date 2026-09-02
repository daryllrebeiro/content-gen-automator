"use client";

import { useEffect } from "react";
import { faroTracker } from "../lib/faro";

export default function FaroInitializer() {
  useEffect(() => {
    faroTracker.init();
    faroTracker.trackEvent("studio_session_start", { timestamp: new Date().toISOString() });
  }, []);

  return null;
}
