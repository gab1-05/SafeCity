import { useState, useEffect } from "react";
import { X, ChevronLeft, ChevronRight, Maximize2, Minimize2, Download, MessageSquare } from "lucide-react";
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

export function MediaLightbox({ media, initialIndex, onClose, onCommentOnMedia }: MediaLightboxProps) {
  const [index, setIndex] = useState(initialIndex);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") setIndex((i) => (i === 0 ? media.length - 1 : i - 1));
      if (e.key === "ArrowRight") setIndex((i) => (i === media.length - 1 ? 0 : i + 1));
      if (e.key === "f") setIsFullscreen((v) => !v);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [media.length, onClose]);

  const current = media[index];
  const isImage = current.media_type === "image";

  const downloadMedia = () => {
    const link = document.createElement("a");
    link.href = current.url;
    link.download = current.caption || `media-${current.id}`;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.click();
  };

  return (
    <div
      className={cn(
        "fixed inset-0 z-[10000] flex items-center justify-center bg-black/95",
        isFullscreen && "bg-black"
      )}
      role="dialog"
      aria-modal="true"
      aria-label="Media viewer"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {/* Close button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-4 right-4 z-10 text-white/80 hover:text-white"
        onClick={onClose}
        aria-label="Close"
      >
        <X className="h-6 w-6" />
      </Button>

      {/* Fullscreen toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-4 right-14 z-10 text-white/80 hover:text-white"
        onClick={() => setIsFullscreen((v) => !v)}
        aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
      >
        {isFullscreen ? <Minimize2 className="h-6 w-6" /> : <Maximize2 className="h-6 w-6" />}
      </Button>

      {/* Download button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-4 right-24 z-10 text-white/80 hover:text-white"
        onClick={downloadMedia}
        aria-label="Download"
      >
        <Download className="h-6 w-6" />
      </Button>

      {/* Comment on media button */}
      {onCommentOnMedia && isImage && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-4 right-34 z-10 text-white/80 hover:text-white"
          onClick={() => onCommentOnMedia(current.id)}
          aria-label="Comment on this photo"
        >
          <MessageSquare className="h-6 w-6" />
        </Button>
      )}

      {/* Navigation */}
      {media.length > 1 && (
        <>
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-4 z-10 text-white/80 hover:text-white hidden sm:flex"
            onClick={() => setIndex((i) => (i === 0 ? media.length - 1 : i - 1))}
            aria-label="Previous"
          >
            <ChevronLeft className="h-8 w-8" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-4 z-10 text-white/80 hover:text-white hidden sm:flex"
            onClick={() => setIndex((i) => (i === media.length - 1 ? 0 : i + 1))}
            aria-label="Next"
          >
            <ChevronRight className="h-8 w-8" />
          </Button>
        </>
      )}

      {/* Media content */}
      <div className="relative max-w-[90vw] max-h-[90vh] w-auto h-auto">
        {isImage ? (
          <img
            src={current.url}
            alt={current.caption || "Evidence photo"}
            className="max-w-[90vw] max-h-[85vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <div className="flex items-center justify-center gap-4 text-white w-[600px]">
            <p className="text-lg capitalize">{current.media_type} file</p>
            <a
              href={current.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline hover:opacity-80"
            >
              Open in new tab
            </a>
          </div>
        )}
        {current.caption && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 text-white text-center">
            <p className="text-sm">{current.caption}</p>
          </div>
        )}
      </div>

      {/* Counter */}
      {media.length > 1 && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
          {index + 1} / {media.length}
        </div>
      )}

      {/* Thumbnails */}
      {media.length > 1 && (
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex gap-2 pb-4">
          {media.map((m, i) => (
            <button
              key={m.id}
              onClick={() => setIndex(i)}
              className={cn(
                "relative h-16 w-24 rounded overflow-hidden border-2 transition-all",
                i === index ? "border-primary" : "border-white/20 hover:border-white/40"
              )}
              aria-label={`View image ${i + 1}`}
              aria-current={i === index ? "true" : "false"}
            >
              {m.media_type === "image" ? (
                <img src={m.url} alt="" className="h-full w-full object-cover" />
              ) : (
                <div className="h-full w-full flex items-center justify-center bg-muted text-xs">
                  {m.media_type}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}