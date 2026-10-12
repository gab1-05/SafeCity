import { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Download,
  MessageSquare,
  ZoomIn,
  ZoomOut,
  Loader2,
  Film,
  FileText,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MediaLightboxProps {
  media: Array<{
    id: string;
    url: string;
    media_type: string;
    caption: string;
    mime_type: string;
  }>;
  initialIndex: number;
  onClose: () => void;
  onCommentOnMedia?: (mediaId: string) => void;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;
const SWIPE_PX = 50;

export function MediaLightbox({
  media,
  initialIndex,
  onClose,
  onCommentOnMedia,
}: MediaLightboxProps) {
  const safeLength = media.length;
  const [index, setIndex] = useState(() =>
    safeLength === 0 ? 0 : Math.min(Math.max(initialIndex, 0), safeLength - 1),
  );
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const touchX = useRef<number | null>(null);
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  const goTo = useCallback(
    (next: number) => {
      if (safeLength === 0) return;
      setIndex((next + safeLength) % safeLength);
    },
    [safeLength],
  );

  // Reset zoom/pan/loading state whenever the item changes.
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setLoaded(false);
    setFailed(false);
  }, [index]);

  // Lock body scroll while open; focus the dialog for keyboard users.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    containerRef.current?.focus();
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  // Track native fullscreen so the icon stays in sync when the user presses F11/Esc.
  useEffect(() => {
    const sync = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (safeLength === 0) return;
      if (e.key === "Escape") {
        if (document.fullscreenElement) void document.exitFullscreen();
        else onClose();
      }
      if (e.key === "ArrowLeft") goTo(index - 1);
      if (e.key === "ArrowRight") goTo(index + 1);
      if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(MAX_ZOOM, +(z + 0.5).toFixed(2)));
      if (e.key === "-") setZoom((z) => Math.max(MIN_ZOOM, +(z - 0.5).toFixed(2)));
      if (e.key === "0") {
        setZoom(1);
        setPan({ x: 0, y: 0 });
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [safeLength, onClose, index, goTo]);

  if (safeLength === 0) return null;

  const current = media[index];
  if (!current) return null;
  const isImage = current.media_type === "image";
  const isVideo = current.media_type === "video";

  const toggleFullscreen = () => {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement) void document.exitFullscreen();
    else if (el.requestFullscreen) {
      void el.requestFullscreen().catch(() => setIsFullscreen((v) => !v));
    } else {
      setIsFullscreen((v) => !v);
    }
  };

  const zoomBy = (delta: number) => {
    setZoom((z) => {
      const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, +(z + delta).toFixed(2)));
      if (next === 1) setPan({ x: 0, y: 0 });
      return next;
    });
  };

  const downloadMedia = () => {
    if (!current.url) return;
    const link = document.createElement("a");
    link.href = current.url;
    link.download = current.caption || `media-${current.id}`;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.click();
  };

  // Touch swipe (only at 1x zoom so it never fights panning).
  const onTouchStart = (e: React.TouchEvent) => {
    touchX.current = e.touches[0]?.clientX ?? null;
  };
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX.current === null || zoom !== 1 || safeLength < 2) return;
    const dx = (e.changedTouches[0]?.clientX ?? touchX.current) - touchX.current;
    if (dx > SWIPE_PX) goTo(index - 1);
    else if (dx < -SWIPE_PX) goTo(index + 1);
    touchX.current = null;
  };

  // Drag-to-pan when zoomed in.
  const onPointerDown = (e: React.PointerEvent) => {
    if (zoom === 1 || !isImage) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const limit = 240 * zoom;
    setPan({
      x: Math.max(-limit, Math.min(limit, drag.current.px + e.clientX - drag.current.x)),
      y: Math.max(-limit, Math.min(limit, drag.current.py + e.clientY - drag.current.y)),
    });
  };
  const onPointerUp = () => {
    drag.current = null;
  };

  return (
    <div
      ref={containerRef}
      tabIndex={-1}
      className={cn(
        "fixed inset-0 z-[10000] flex items-center justify-center bg-black/95 outline-none",
        isFullscreen && "bg-black",
      )}
      role="dialog"
      aria-modal="true"
      aria-label={`Media viewer, item ${index + 1} of ${safeLength}`}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between gap-2 bg-gradient-to-b from-black/70 to-transparent p-4">
        <div className="text-white/80 text-sm tabular-nums" aria-live="polite">
          {safeLength > 1
            ? `${index + 1} / ${safeLength}`
            : isVideo
              ? "Video"
              : isImage
                ? "Photo"
                : "File"}
        </div>
        <div className="flex items-center gap-1">
          {isImage && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="text-white/80 hover:text-white"
                onClick={() => zoomBy(-0.5)}
                disabled={zoom <= MIN_ZOOM}
                aria-label="Zoom out"
              >
                <ZoomOut className="h-5 w-5" />
              </Button>
              <span
                className="w-12 text-center text-xs text-white/70 tabular-nums"
                aria-live="polite"
              >
                {Math.round(zoom * 100)}%
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="text-white/80 hover:text-white"
                onClick={() => zoomBy(0.5)}
                disabled={zoom >= MAX_ZOOM}
                aria-label="Zoom in"
              >
                <ZoomIn className="h-5 w-5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="text-white/80 hover:text-white"
                onClick={() => {
                  setZoom(1);
                  setPan({ x: 0, y: 0 });
                }}
                disabled={zoom === 1}
                aria-label="Reset zoom"
              >
                <RotateCcw className="h-5 w-5" />
              </Button>
            </>
          )}
          {onCommentOnMedia && isImage && (
            <Button
              variant="ghost"
              size="icon"
              className="text-white/80 hover:text-white"
              onClick={() => onCommentOnMedia(current.id)}
              aria-label="Comment on this photo"
            >
              <MessageSquare className="h-5 w-5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="text-white/80 hover:text-white"
            onClick={downloadMedia}
            disabled={!current.url}
            aria-label="Download"
          >
            <Download className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-white/80 hover:text-white"
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="h-5 w-5" /> : <Maximize2 className="h-5 w-5" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-white/80 hover:text-white"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-6 w-6" />
          </Button>
        </div>
      </div>

      {/* Navigation */}
      {media.length > 1 && (
        <>
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-2 sm:left-4 z-10 h-12 w-12 rounded-full bg-black/40 text-white/90 hover:bg-black/60 hover:text-white"
            onClick={() => goTo(index - 1)}
            aria-label="Previous"
          >
            <ChevronLeft className="h-8 w-8" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-2 sm:right-4 z-10 h-12 w-12 rounded-full bg-black/40 text-white/90 hover:bg-black/60 hover:text-white"
            onClick={() => goTo(index + 1)}
            aria-label="Next"
          >
            <ChevronRight className="h-8 w-8" />
          </Button>
        </>
      )}

      {/* Media content */}
      <div className="relative flex max-h-[82vh] w-auto max-w-[92vw] items-center justify-center">
        {!current.url ? (
          <p className="text-sm text-white/70">
            This file is still processing — try again shortly.
          </p>
        ) : isImage ? (
          <div
            className={cn(
              "relative overflow-hidden",
              zoom > 1 ? "cursor-grab active:cursor-grabbing" : "cursor-zoom-in",
            )}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onDoubleClick={() => {
              if (zoom === 1) setZoom(2);
              else {
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }
            }}
          >
            {!loaded && !failed && (
              <div
                className="absolute inset-0 flex items-center justify-center"
                aria-label="Loading image"
              >
                <Loader2 className="h-10 w-10 animate-spin text-white/70" />
              </div>
            )}
            {failed ? (
              <div className="flex flex-col items-center gap-3 p-8 text-center">
                <p className="text-sm text-white/70">Couldn&apos;t load this photo.</p>
                <a
                  href={current.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary underline hover:opacity-80"
                >
                  Open original in new tab
                </a>
              </div>
            ) : (
              <img
                src={current.url}
                alt={current.caption || "Evidence photo"}
                draggable={false}
                onLoad={() => setLoaded(true)}
                onError={() => setFailed(true)}
                onClick={(e) => e.stopPropagation()}
                style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
                className={cn(
                  "max-h-[82vh] max-w-[92vw] touch-none object-contain transition-transform duration-150 select-none",
                  !loaded && "opacity-0",
                )}
              />
            )}
          </div>
        ) : isVideo ? (
          <video
            key={current.id}
            src={current.url}
            controls
            playsInline
            preload="metadata"
            className="max-h-[82vh] max-w-[92vw] rounded bg-black"
            aria-label={current.caption || "Evidence video"}
          />
        ) : (
          <div className="flex max-w-[92vw] flex-col items-center gap-4 rounded-lg bg-white/10 p-8 text-center">
            <FileText className="h-12 w-12 text-white/60" />
            <p className="text-lg capitalize text-white">{current.media_type} file</p>
            {current.caption && <p className="max-w-md text-sm text-white/70">{current.caption}</p>}
            <a
              href={current.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline hover:opacity-80"
            >
              Open in new tab
            </a>
          </div>
        )}
        {current.caption && current.url && !failed && (
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 pt-8 text-center text-white">
            <p className="text-sm">{current.caption}</p>
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {media.length > 1 && (
        <div className="absolute bottom-3 left-1/2 z-10 flex max-w-[94vw] -translate-x-1/2 gap-2 overflow-x-auto p-1">
          {media.map((m, i) => (
            <button
              key={m.id}
              onClick={() => goTo(i)}
              className={cn(
                "relative h-14 w-20 shrink-0 overflow-hidden rounded border-2 transition-all",
                i === index ? "border-primary" : "border-white/20 hover:border-white/50",
              )}
              aria-label={`View item ${i + 1}${m.media_type !== "image" ? ` (${m.media_type})` : ""}`}
              aria-current={i === index ? "true" : "false"}
            >
              {m.media_type === "image" && m.url ? (
                <img src={m.url} alt="" loading="lazy" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-white/10 text-white/70">
                  {m.media_type === "video" ? (
                    <Film className="h-5 w-5" />
                  ) : (
                    <FileText className="h-5 w-5" />
                  )}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
