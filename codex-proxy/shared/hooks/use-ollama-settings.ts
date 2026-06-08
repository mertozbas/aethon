import { useState, useEffect, useCallback } from "preact/hooks";
import { extractErrorMessage } from "../utils/extract-error";

export interface OllamaBridgeStatus {
  enabled: boolean;
  running: boolean;
  host: string;
  port: number;
  endpoint: string;
  version: string;
  disable_vision: boolean;
  upstream_base_url: string | null;
  started_at: string | null;
  error: string | null;
}

export interface OllamaSettingsData {
  enabled: boolean;
  host: string;
  port: number;
  version: string;
  disable_vision: boolean;
  status: OllamaBridgeStatus;
}

interface OllamaSettingsSaveResponse extends OllamaSettingsData {
  success: boolean;
}

export function useOllamaSettings(apiKey: string | null) {
  const [data, setData] = useState<OllamaSettingsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const resp = await fetch("/admin/ollama-settings");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const result = await resp.json() as OllamaSettingsData;
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const save = useCallback(async (patch: Partial<OllamaSettingsData>) => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
      const resp = await fetch("/admin/ollama-settings", {
        method: "POST",
        headers,
        body: JSON.stringify(patch),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        throw new Error(extractErrorMessage(body, `HTTP ${resp.status}`));
      }
      const result = await resp.json() as OllamaSettingsSaveResponse;
      setData({
        enabled: result.enabled,
        host: result.host,
        port: result.port,
        version: result.version,
        disable_vision: result.disable_vision,
        status: result.status,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }, [apiKey]);

  useEffect(() => { load(); }, [load]);

  return { data, saving, saved, error, load, save };
}
