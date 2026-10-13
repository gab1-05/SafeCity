import { useState, useEffect } from "react";
import { Plus, X, MapPin, Camera, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FABAction {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  shortcut?: string;
}

export function FloatingActionButton({
  mainAction,
  actions = [],
  position = "bottom-right",
}: {
  mainAction: FABAction;
  actions?: FABAction[];
  position?: "bottom-right" | "bottom-left" | "top-right" | "top-left";
}) {
  const [expanded, setExpanded] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  const positionClasses = {
    "bottom-right": "bottom-6 right-6",
    "bottom-left": "bottom-6 left-6",
    "top-right": "top-20 right-6",
    "top-left": "top-20 left-6",
  };

  if (!mounted) return null;

  return (
    <div className={cn("fixed z-40", positionClasses[position])}>
      {/* Action buttons */}
      <div
        className={cn(
          "flex flex-col gap-2 transition-all duration-200",
          position.includes("bottom") ? "flex-col-reverse" : "flex-col",
          expanded
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none translate-y-2",
        )}
        role="menu"
        aria-orientation="vertical"
      >
        {actions.map((action, index) => (
          <div
            key={action.label}
            className={cn("fab-action", position.includes("right") ? "mr-16" : "ml-16")}
            style={{ animationDelay: `${index * 50}ms` }}
            role="menuitem"
          >
            <Button
              variant="default"
              className="gap-2"
              onClick={() => {
                action.onClick();
                setExpanded(false);
              }}
              leftIcon={action.icon}
            >
              {action.label}
            </Button>
            {action.shortcut && (
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                {action.shortcut}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Main FAB */}
      <Button
        variant="default"
        size="icon"
        className={cn("fab-primary relative z-10", expanded && "rotate-45 bg-primary/80")}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={expanded ? "Close quick actions" : mainAction.label}
        aria-haspopup="true"
      >
        {expanded ? <X className="h-5 w-5" /> : mainAction.icon}
      </Button>
    </div>
  );
}

export function MobileQuickReportFAB() {
  const captureLocation = () => {
    if (!navigator.geolocation) {
      window.location.href = "/report";
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        window.location.href = `/report?lat=${latitude.toFixed(6)}&lng=${longitude.toFixed(6)}`;
      },
      () => {
        window.location.href = "/report";
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  };

  const takePhoto = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = () => {
      window.location.href = "/report?media=1";
    };
    // If the user cancels the picker, still offer the report form.
    input.oncancel = () => {
      window.location.href = "/report";
    };
    input.click();
  };

  return (
    <FloatingActionButton
      position="bottom-right"
      mainAction={{
        label: "Report Issue",
        icon: <Plus className="h-5 w-5" />,
        onClick: () => (window.location.href = "/report"),
      }}
      actions={[
        {
          label: "Current Location",
          icon: <MapPin className="h-4 w-4" />,
          onClick: captureLocation,
        },
        { label: "Take Photo", icon: <Camera className="h-4 w-4" />, onClick: takePhoto },
        {
          label: "Text Only",
          icon: <MessageSquare className="h-4 w-4" />,
          onClick: () => (window.location.href = "/report"),
        },
      ]}
    />
  );
}
