import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Download,
  X,
  RotateCcw,
  MessageSquare,
  Loader2,
  Film,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MediaItem {
  id: string;
  url: string;
  media_type: string;
  caption: string;
  mime_type: string;
}

interface InlineMediaGalleryProps {
  media: MediaItem[];
  initialIndex?: number;
  onCommentOnMedia?: (mediaId: string) => void;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;

export function InlineMediaGallery({ media, initialIndex = 0, onCommentOnMedia }: InlineMediaGalleryProps) {
  const safeLength = media.length;
  const [index, setIndex] = useState(() =>
    safeLength === 0 ? 0 : Math.min(Math.max(initialIndex, 0), safeLength - 1)
  );
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [showFullscreen, setShowFullscreen] = useState(false);
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  const goTo = useCallback(
    (next: number) => {
      if (safeLength === 0) return;
      setIndex((next + safeLength) % safeLength);
    },
    [safeLength]
  );

  // Reset zoom/pan/loading state whenever the item changes.
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setLoaded(false);
    setFailed(false);
  }, [index]);

  if (safeLength === 0) return null;

  const current = media[index];
  if (!current) return null;
  const isImage = current.media_type === "image";
  const isVideo = current.media_type === "video";

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

  const openFullscreen = () => {
    setShowFullscreen(true);
  };

  const closeFullscreen = () => {
    setShowFullscreen(false);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Fullscreen modal
  if (showFullscreen) {
    return (
      <div
        className="fixed inset-0 z-[10000] flex items-center justify-center bg-black outline-none"
        role="dialog"
        aria-modal="true"
        aria-label={`Media viewer, item ${index + 1} of ${safeLength}`}
        onClick={(e) => e.target === e.currentTarget && closeFullscreen()}
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
                <Button variant="ghost" size="icon" className="text-white/80 hover:text-white" onClick={() => zoomBy(-0.5)} disabled={zoom <= MIN_ZOOM} aria-label="Zoom out">
                  <ZoomOut className="h-5 w-5" />
                </Button>
                <span className="w-12 text-center text-xs text-white/70 tabular-nums" aria-live="polite">
                  {Math.round(zoom * 100)}%
                </span>
                <Button variant="ghost" size="icon" className="text-white/80 hover:text-white" onClick={() => zoomBy(0.5)} disabled={zoom >= MAX_ZOOM} aria-label="Zoom in">
                  <ZoomIn className="h-5 w-5" />
                </Button>
                <Button variant="ghost" size="icon" className="text-white/80 hover:text-white" onClick={() => { zoomBy(-zoom + 1); setPan({ x: 0, y: 0 }); }} disabled={zoom === 1} aria-label="Reset zoom">
                  <RotateCcw className="h-5 w-5" />
                </Button>
              </>
            )}
            {onCommentOnMedia && isImage && (
              <Button variant="ghost" size="icon" className="text-white/80 hover:text-white" onClick={() => { onCommentOnMedia?.(current.id); closeFullscreen(); }} aria-label="Comment on this photo">
                <MessageSquare className="h-5 w-5" />
              </Button>
            )}
            <Button variant="ghost" size="icon" className="text-white/80 hover:text-white" onClick={downloadMedia} disabled={!current.url} aria-label="Download">
              <Download className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" className="text-white/80 hover:text-white" onClick={closeFullscreen} aria-label="Exit fullscreen">
              <X className="h-6 w-6" />
            </Button>
          </div>

          {/* Navigation */}
          {media.length > 1 && (
            <>
              <Button variant="ghost" size="icon" className="absolute left-2 sm:left-4 z-10 h-12 w-12 rounded-full bg-black/40 text-white/90 hover:bg-black/60 hover:text-white" onClick={() => goTo(index - 1)} aria-label="Previous">
                <ChevronLeft className="h-8 w-8" />
              </Button>
              <Button variant="ghost" size="icon" className="absolute right-2 sm:right-4 z-10 h-12 w-12 rounded-full bg-black/40 text-white/90 hover:bg-black/60 hover:text-white" onClick={() => goTo(index + 1)} aria-label="Next">
                <ChevronRight className="h-8 w-8" />
              </Button>
            </>
          )}

        </div>
          {/* Media content */}
          <div className="relative flex h-full w-full items-center justify-center">
            {!current.url ? (
              <p className="text-sm text-white/70">This file is still processing — try again shortly.</p>
            ) : isImage ? (
              <div
                className={cn(
                  "relative overflow-hidden w-full h-full",
                  zoom > 1 ? "cursor-grab active:cursor-grabbing" : "cursor-zoom-in",
                )}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onDoubleClick={() => {
                  if (zoom === 1) setZoom(2);
                  else { setZoom(1); setPan({ x: 0, y: 0 }); }
                }}
              >
                {!loaded && !failed && (
                  <div className="absolute inset-0 flex items-center justify-center" aria-label="Loading image">
                    <Loader2 className="h-10 w-10 animate-spin text-white/70" />
                  </div>
                )}
                {failed ? (
                  <div className="flex flex-col items-center gap-3 p-8 text-center">
                    <p className="text-sm text-white/70">Couldn't load this photo.</p>
                    <a href={current.url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary underline hover:opacity-80">
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
                      "w-full h-full object-contain transition-transform duration-150 select-none",
                      !loaded && "opacity-0",
                    )}
                  />
                )}
              </div>
            ) : isVideo ? (
              <video key={current.id} src={current.url} controls playsInline preload="metadata" className="max-h-[82vh] max-w-[92vw] rounded bg-black" aria-label={current.caption || "Evidence video"} />
            ) : (
              <div className="flex max-w-[92vw] flex-col items-center gap-4 rounded-lg bg-white/10 p-8 text-center">
                <FileText className="h-12 w-12 text-white/60" />
                <p className="text-lg capitalize text-white">{current.media_type} file</p>
                {current.caption && <p className="max-w-md text-sm text-white/70">{current.caption}</p>}
                <a href={current.url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary underline hover:opacity-80">Open in new tab</a>
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
                      {m.media_type === "video" ? <Film className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
          <Button variant="ghost" size="icon" className="absolute bottom-2 right-2 z-10 h-10 w-10 rounded-full bg-black/40 text-white/90 hover:bg-black/60 hover:text-white" onClick={closeFullscreen} aria-label="Exit fullscreen">
            <X className="h-6 w-6" />
          </Button>
        </div>
    );
  }

// Inline view
  const currentItem = media[index];
  if (!currentItem) return null;
  const isImageInline = currentItem.media_type === "image";

  const handleImageClick = () => {
    if (isImageInline) openFullscreen();
  };

  return (
    <div className="space-y-3">
      {/* Main media display */}
      <div className="relative rounded-xl overflow-hidden bg-muted">
        {!currentItem.url ? (
          <div className="aspect-video flex items-center justify-center bg-muted">
            <p className="text-sm text-muted-foreground">Processing...</p>
          </div>
        ) : isImageInline ? (
          <div className="relative aspect-video overflow-hidden cursor-zoom-in" onClick={handleImageClick}>
            <img
              src={currentItem.url}
              alt={currentItem.caption || "Evidence photo"}
              className="w-full h-full object-cover transition-opacity duration-200"
              loading="lazy"
            />
            {/* Expand hint */}
            <div className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full bg-black/50 text-white text-xs">
              <Maximize2 className="h-3 w-3" />
              <span className="hidden sm:inline">Click to expand</span>
            </div>
            {currentItem.caption && (
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3 text-white text-sm">
                {currentItem.caption}
              </div>
            )}
          </div>
        ) : currentItem.media_type === "video" ? (
          <video
            src={currentItem.url}
            controls
            playsInline
            preload="metadata"
            className="w-full aspect-video bg-black rounded-xl"
            aria-label={currentItem.caption || "Evidence video"}
          />
        ) : (
          <div className="aspect-video flex flex-col items-center justify-center gap-2 rounded-xl bg-muted/50 p-6 text-center">
            <FileText className="h-10 w-10 text-muted-foreground" />
            <p className="text-base capitalize text-foreground">{currentItem.media_type} file</p>
            {currentItem.caption && <p className="max-w-md text-sm text-muted-foreground">{currentItem.caption}</p>}
            <a
              href={currentItem.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline hover:opacity-80"
            >
              Open in new tab
            </a>
          </div>
        )}
      </div>

      {/* Thumbnails / navigation */}
      {media.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {media.map((m, i) => (
            <button
              key={m.id}
              onClick={() => setIndex(i)}
              className={cn(
                "relative h-16 w-24 shrink-0 overflow-hidden rounded-lg border-2 transition-all flex-shrink-0",
                i === index ? "border-primary" : "border-transparent hover:border-primary/50"
              )}
              aria-label={`View item ${i + 1}${m.media_type !== "image" ? ` (${m.media_type})` : ""}`}
              aria-current={i === index ? "true" : "false"}
            >
              {m.media_type === "image" && m.url ? (
                <img src={m.url} alt="" loading="lazy" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-muted text-muted-foreground">
                  {m.media_type === "video" ? <Film className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Caption */}
      {currentItem.caption && !showFullscreen && (
        <p className="text-sm text-muted-foreground text-center">{currentItem.caption}</p>
      )}
    </div>
  );
}