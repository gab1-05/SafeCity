import { useEffect, useRef, useState } from "react";

/**
 * Google Identity Services (GIS) sign-in button.
 *
 * - Renders nothing until the GIS script confirms a client_id is configured
 *   (the backend exposes it via /api/v1/meta/config/ only when set).
 * - Calls onCredential with the Google ID token; the parent exchanges it for
 *   SafeCity JWTs via /auth/oauth/google/.
 * - Degrades to invisible when Google sign-in is not configured, so local
 *   development and self-hosted deployments are unaffected.
 */

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            use_fedcm_for_prompt?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: Record<string, unknown>,
          ) => void;
        };
      };
    };
  }
}

const GIS_SRC = "https://accounts.google.com/gsi/client";

interface MetaConfig {
  oauth?: { google_client_id?: string | null };
}

let metaConfigPromise: Promise<MetaConfig> | null = null;

function fetchMetaConfig(): Promise<MetaConfig> {
  if (!metaConfigPromise) {
    // Note: meta config lives at /api/meta/config/, outside the /api/v1/ tree.
    metaConfigPromise = fetch("/api/meta/config/").then((r) => {
      if (!r.ok) throw new Error("meta config unavailable");
      return r.json() as Promise<MetaConfig>;
    });
  }
  return metaConfigPromise;
}

function loadGisScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GIS_SRC}"]`,
    );
    if (existing) {
      if (existing.dataset.loaded === "true") resolve();
      else existing.addEventListener("load", () => resolve());
      return;
    }
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => reject(new Error("gis_script_failed"));
    document.head.appendChild(script);
  });
}

export function GoogleSignInButton({
  onCredential,
  onUnavailable,
  onError,
}: {
  onCredential: (idToken: string) => void;
  onUnavailable?: () => void;
  onError?: (message: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "hidden">("loading");
  const credentialRef = useRef(onCredential);
  credentialRef.current = onCredential;

  useEffect(() => {
    let cancelled = false;

    fetchMetaConfig()
      .then((config) => {
        const clientId = config.oauth?.google_client_id;
        if (!clientId) {
          setState("hidden");
          onUnavailable?.();
          return null;
        }
        return loadGisScript().then(() => clientId);
      })
      .then((clientId) => {
        if (cancelled || !clientId) return;
        if (!window.google?.accounts?.id || !containerRef.current) {
          if (!window.google?.accounts?.id) {
            onError?.("Google sign-in script loaded but unavailable.");
            setState("hidden");
            onUnavailable?.();
          }
          return;
        }
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => credentialRef.current(response.credential),
          use_fedcm_for_prompt: false,
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          theme: "outline",
          size: "large",
          width: 320,
          text: "continue_with",
          shape: "pill",
        });
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) {
          setState("hidden");
          onUnavailable?.();
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (state === "hidden") return null;

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        ref={containerRef}
        data-testid="google-signin"
        className="flex min-h-[44px] w-full justify-center"
      />
      {state === "loading" && (
        <p className="text-xs text-muted-foreground">Checking sign-in options…</p>
      )}
    </div>
  );
}
