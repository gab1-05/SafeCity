import { useEffect, useState, useRef } from "react";
import { Search, Keyboard, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { authApi } from "@/api/auth";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  shortcut?: string;
  icon?: React.ReactNode;
  action: () => void;
  section?: string;
  keywords?: string[];
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { user, theme, toggleTheme } = useAuthStore();

  const commands: CommandItem[] = [
    { id: "dashboard", label: "Dashboard", description: "Go to your dashboard", shortcut: "⌘1", icon: "🏠", action: () => navigate("/dashboard"), section: "Navigation", keywords: ["home", "main"] },
    { id: "report", label: "Report Incident", description: "Create a new incident report", shortcut: "⌘N", icon: "➕", action: () => navigate("/report"), section: "Navigation", keywords: ["create", "new", "incident"] },
    { id: "incidents", label: "My Reports", description: "View your incident reports", shortcut: "⌘2", icon: "📋", action: () => navigate("/incidents"), section: "Navigation", keywords: ["my", "reports", "list"] },
    { id: "map", label: "Live Map", description: "View incidents on the map", shortcut: "⌘M", icon: "🗺️", action: () => navigate("/map"), section: "Navigation", keywords: ["map", "location"] },
    { id: "notifications", label: "Notifications", description: "View all notifications", shortcut: "⌘3", icon: "🔔", action: () => navigate("/notifications"), section: "Navigation", keywords: ["alerts", "updates"] },
    { id: "profile", label: "Profile", description: "Manage your profile", shortcut: "⌘P", icon: "👤", action: () => navigate("/profile"), section: "Navigation", keywords: ["settings", "account"] },
    { id: "theme", label: "Toggle Theme", description: "Switch between light and dark mode", shortcut: "⌘T", icon: "🌓", action: () => toggleTheme(), section: "Actions", keywords: ["dark", "light", "mode"] },
    { id: "logout", label: "Log Out", description: "Sign out of your account", shortcut: "⌘L", icon: "🚪", action: () => { localStorage.removeItem("safecity.access"); localStorage.removeItem("safecity.user"); navigate("/login"); }, section: "Actions", keywords: ["signout", "exit"] },
  ];

  const roleCanViewAuthority = user?.role === "department_staff" || user?.role === "city_admin" || user?.role === "superuser";
  const roleCanManageSystem = user?.role === "city_admin" || user?.role === "superuser";

  const authorityCommands: CommandItem[] = roleCanViewAuthority ? [
    { id: "operations", label: "Operations Dashboard", description: "View operations overview", shortcut: "⌘O", icon: "📊", action: () => navigate("/operations"), section: "Authority", keywords: ["ops", "dashboard"] },
    { id: "queue", label: "Incident Queue", description: "Manage incident queue", shortcut: "⌘Q", icon: "📥", action: () => navigate("/queue"), section: "Authority", keywords: ["queue", "manage"] },
  ] : [];

  const adminCommands: CommandItem[] = roleCanManageSystem ? [
    { id: "admin", label: "Admin Overview", description: "System administration", shortcut: "⌘A", icon: "⚙️", action: () => navigate("/admin"), section: "Admin", keywords: ["admin", "system"] },
    { id: "users", label: "User Management", description: "Manage users", shortcut: "⌘U", icon: "👥", action: () => navigate("/admin/users"), section: "Admin", keywords: ["users", "manage"] },
  ] : [];

  const allCommands = [...commands, ...authorityCommands, ...adminCommands];

  const filteredCommands = allCommands
    .filter((cmd) => {
      const searchText = `${cmd.label} ${cmd.description} ${cmd.keywords?.join(" ")}`.toLowerCase();
      return searchText.includes(query.toLowerCase());
    })
    .sort((a, b) => {
      const aLabel = a.label.toLowerCase();
      const bLabel = b.label.toLowerCase();
      const q = query.toLowerCase();
      const aStarts = aLabel.startsWith(q);
      const bStarts = bLabel.startsWith(q);
      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;
      return 0;
    });

  const handleSelect = (cmd: CommandItem) => {
    cmd.action();
    setOpen(false);
    setQuery("");
    setSelectedIndex(0);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (filteredCommands[selectedIndex]) handleSelect(filteredCommands[selectedIndex]);
        break;
      case "Escape":
        setOpen(false);
        setQuery("");
        setSelectedIndex(0);
        break;
    }
  };

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelectedIndex(0);
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
  }, [open]);

  if (!open) return null;

  const grouped = new Map<string, CommandItem[]>();
  filteredCommands.forEach((cmd) => {
    const section = cmd.section || "Other";
    if (!grouped.has(section)) grouped.set(section, []);
    grouped.get(section)!.push(cmd);
  });
  const groupedArray = Array.from(grouped.entries());

  return (
    <div className="fixed inset-0 z-[1000] flex items-start justify-center pt-20" role="dialog" aria-modal="true" aria-label="Command palette">
      <div className="absolute inset-0 bg-black/50 animate-fade-in" onClick={() => setOpen(false)} aria-hidden />
      
      <div className="relative w-full max-w-2xl mx-4 animate-scale-in">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search... (⌘K to close)"
            className="w-full h-12 pl-12 pr-4 text-lg bg-card/95 backdrop-blur border border-border rounded-xl shadow-xl placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-label="Command palette search"
            autoComplete="off"
            spellCheck={false}
          />
          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2 text-xs text-muted-foreground">
            <Keyboard className="h-4 w-4" aria-hidden />
            <span>⌘K</span>
          </div>
        </div>

        {filteredCommands.length > 0 && (
          <div className="mt-2 rounded-xl border border-border bg-card overflow-hidden shadow-xl">
            {groupedArray.map(([section, cmds]) => (
              <div key={section} className="border-t first:border-t-0">
                <div className="px-4 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider bg-muted/50">
                  {section}
                </div>
                <div className="divide-y divide-border">
                  {cmds.map((cmd) => {
                    const globalIndex = filteredCommands.indexOf(cmd);
                    const isSelected = globalIndex === selectedIndex;
                    return (
                      <button
                        key={cmd.id}
                        onClick={() => handleSelect(cmd)}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                        className={cn(
                          "w-full px-4 py-3 text-left flex items-center gap-3 transition-colors",
                          isSelected ? "bg-primary/10 text-primary" : "hover:bg-accent"
                        )}
                        style={{ outline: isSelected ? "2px solid hsl(var(--primary))" : "none" }}
                      >
                        <span className="flex h-8 w-8 items-center justify-center text-lg">{cmd.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{cmd.label}</div>
                          {cmd.description && <div className="text-sm text-muted-foreground truncate">{cmd.description}</div>}
                        </div>
                        {cmd.shortcut && (
                          <span className="flex h-6 min-w-[60px] items-center justify-end rounded px-2 text-xs text-muted-foreground font-mono bg-muted">
                            {cmd.shortcut}
                          </span>
                        )}
                        {isSelected && <ChevronDown className="h-5 w-5 text-primary" aria-hidden />}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {filteredCommands.length === 0 && query && (
          <div className="mt-2 rounded-xl border border-border bg-card p-8 text-center text-muted-foreground">
            No commands found for "{query}"
          </div>
        )}

        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground px-1">
          <span>↑↓ Navigate · ⏎ Select · ⎋ Close</span>
          <span>⌘K Toggle</span>
        </div>
      </div>
    </div>
  );
}