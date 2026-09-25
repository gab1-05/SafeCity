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
          expanded ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none translate-y-2",
        )}
        role="menu"
        aria-orientation="vertical"
      >
        {actions.map((action, index) => (
          <div
            key={action.label}
            className={cn(
              "fab-action",
              position.includes("right") ? "mr-16" : "ml-16",
            )}
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
        className={cn(
          "fab-primary relative z-10",
          expanded && "rotate-45 bg-primary/80",
        )}
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
  return (
    <FloatingActionButton
      position="bottom-right"
      mainAction={{
        label: "Report Issue",
        icon: <Plus className="h-5 w-5" />,
        onClick: () => window.location.href = "/report",
      }}
      actions={[
        { label: "Current Location", icon: <MapPin className="h-4 w-4" />, onClick: () => { /* use geolocation */ } },
        { label: "Take Photo", icon: <Camera className="h-4 w-4" />, onClick: () => { /* open camera */ } },
        { label: "Text Only", icon: <MessageSquare className="h-4 w-4" />, onClick: () => window.location.href = "/report" },
      ]}
    />
  );
}