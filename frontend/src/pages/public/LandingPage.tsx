import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Droplets,
  Flame,
  Lightbulb,
  Construction,
  Trash2,
  MapPin,
  ShieldCheck,
  Users,
  Clock,
  Map,
  TrendingUp,
  Star,
  ArrowRight,
  MessageSquare,
  Heart,
  Share2,
  MoreHorizontal,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { incidentsApi } from "@/api/incidents";
import { timeAgo } from "@/lib/utils";
import { cn } from "@/lib/utils";

const CATEGORY_ICONS = [
  { icon: Construction, label: "Road damage", color: "bg-amber-500", href: "/report?category=road" },
  { icon: Droplets, label: "Flooding", color: "bg-blue-500", href: "/report?category=flooding" },
  { icon: Flame, label: "Fire hazard", color: "bg-red-500", href: "/report?category=fire" },
  { icon: Trash2, label: "Garbage", color: "bg-green-500", href: "/report?category=garbage" },
  { icon: Lightbulb, label: "Streetlights", color: "bg-yellow-500", href: "/report?category=streetlight" },
  { icon: Building2, label: "Building damage", color: "bg-slate-500", href: "/report?category=building" },
];

const FEATURES = [
  {
    icon: MapPin,
    title: "Precise Location",
    description: "Drop a pin on the map or use your current location for accurate reporting.",
  },
  {
    icon: ShieldCheck,
    title: "Verified & Routed",
    description: "Authorities verify reports and route them to the responsible department with SLA deadlines.",
  },
  {
    icon: Clock,
    title: "Real-time Tracking",
    description: "Follow the public timeline, get notified at every step, and confirm when fixed.",
  },
  {
    icon: Users,
    title: "Community Powered",
    description: "See nearby reports, upvote issues, and collaborate with neighbors for faster resolution.",
  },
];

const STATS = [
  { value: "50K+", label: "Issues Reported", icon: MapPin },
  { value: "92%", label: "Resolution Rate", icon: CheckCircle2 },
  { value: "24h", label: "Avg. Response", icon: Clock },
  { value: "500+", label: "Active Cities", icon: Map },
];

function CommunityFeed() {
  const { data, isPending } = useQuery({
    queryKey: ["landing-incidents"],
    queryFn: () => incidentsApi.list({ status: ["verified", "resolved"], page_size: 10 }),
    staleTime: 60_000,
  });

  const incidents = data?.results ?? [];

  if (isPending) {
    return (
      <Card variant="elevated">
        <CardHeader>
          <CardTitle className="text-base">Recent Community Reports</CardTitle>
          <CardDescription>Live incidents from your city</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 bg-muted rounded" />
                  <div className="h-3 w-1/2 bg-muted rounded" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (incidents.length === 0) {
    return (
      <Card variant="elevated">
        <CardHeader>
          <CardTitle className="text-base">Recent Community Reports</CardTitle>
          <CardDescription>Live incidents from your city</CardDescription>
        </CardHeader>
        <CardContent className="py-8 text-center">
          <MessageSquare className="mx-auto h-12 w-12 text-muted-foreground/50" />
          <p className="mt-2 text-muted-foreground">No public incidents yet. Be the first to report!</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Recent Community Reports</CardTitle>
            <CardDescription>Live incidents from your city — {incidents.length} shown</CardDescription>
          </div>
          <Link to="/map" className="text-sm text-primary hover:underline">
            View all on map →
          </Link>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-3">
          {incidents.map((incident) => (
            <Link
              key={incident.id}
              to={`/track?ref=${incident.reference_number}`}
              className="group flex items-start gap-3 p-3 rounded-lg border hover:bg-accent/50 transition-all"
            >
              <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                style={{ backgroundColor: incident.category ? `hsl(var(--severity-${incident.severity}))` : "hsl(var(--muted))" }}>
                <SeverityBadge severity={incident.severity as any} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium truncate">{incident.title}</p>
                  <StatusBadge status={incident.status as any} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground truncate">
                  {incident.category?.name} · {incident.ward_name ?? "Unknown area"} · {timeAgo(incident.created_at)}
                </p>
                <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3.5 w-3.5" />
                    {Math.floor(Math.random() * 20)} comments
                  </span>
                  <span className="flex items-center gap-1">
                    <Heart className="h-3.5 w-3.5" />
                    {Math.floor(Math.random() * 50)} upvotes
                  </span>
                  <span className="flex items-center gap-1">
                    <Share2 className="h-3.5 w-3.5" />
                    Share
                  </span>
                </div>
              </div>
              <MoreHorizontal className="h-5 w-5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function LandingPage() {
  return (
    <>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary/5 via-background to-background py-20 md:py-28 lg:py-32">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent" />
        <div className="relative container">
          <div className="mx-auto max-w-4xl text-center">
            <Badge variant="brand" className="mb-6 animate-fade-in">
              <Star className="h-3 w-3 mr-1" aria-hidden />
              New: Anonymous reporting now available
            </Badge>
            <h1 className="heading-1 text-balance">
              Report city problems.
              <span className="gradient-text-brand"> Track the fix.</span>
            </h1>
            <p className="mt-6 text-lead max-w-2xl mx-auto">
              SafeCity connects citizens with municipal departments — report potholes, flooding,
              broken streetlights and more, then follow every step until resolution.
            </p>
            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link to="/report">
                <Button size="lg" className="btn-brand w-full sm:w-auto gap-2" rightIcon={<ArrowRight className="h-4 w-4" />}>
                  Report an Incident
                </Button>
              </Link>
              <Link to="/map">
                <Button size="lg" variant="outline" className="w-full sm:w-auto gap-2" leftIcon={<Map className="h-4 w-4" />}>
                  Explore Live Map
                </Button>
              </Link>
            </div>
            <div className="mt-12 flex flex-wrap items-center justify-center gap-8 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
                <span>No account needed for anonymous reports</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-primary" aria-hidden />
                <span>Typical response: under 24 hours</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" aria-hidden />
                <span>Track progress in real-time</span>
              </div>
            </div>
          </div>
        </div>

        {/* Floating Stats */}
        <div className="absolute bottom-[-2rem] left-1/2 -translate-x-1/2 flex flex-wrap items-center justify-center gap-6 md:gap-10 px-4 animate-slide-up">
          {STATS.map((stat) => (
            <div key={stat.label} className="flex flex-col items-center gap-1 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <stat.icon className="h-6 w-6" aria-hidden />
              </div>
              <div className="text-2xl font-bold text-foreground">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Community Feed - Social Media Style */}
      <section className="section container">
        <div className="mx-auto max-w-3xl">
          <CommunityFeed />
        </div>
      </section>

      {/* Categories */}
      <section className="section container">
        <div className="mx-auto max-w-3xl text-center mb-12">
          <h2 className="heading-2">What can you report?</h2>
          <p className="mt-3 text-lead">Choose a category to get started — each report makes your city safer.</p>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {CATEGORY_ICONS.map(({ icon: Icon, label, color, href }) => (
            <Link
              key={label}
              to={href}
              className="group card-interactive flex flex-col items-center gap-3 p-5 text-center"
            >
              <div className={cn("relative flex h-14 w-14 items-center justify-center rounded-xl", color)}>
                <Icon className="h-7 w-7 text-white" aria-hidden />
                <span className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-white/90">
                  <ArrowRight className="h-3 w-3 text-primary" aria-hidden />
                </span>
              </div>
              <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                {label}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="section bg-muted/40">
        <div className="container">
          <div className="mx-auto max-w-3xl text-center mb-12">
            <h2 className="heading-2">How it works</h2>
            <p className="mt-3 text-lead">Three simple steps to make your neighborhood better.</p>
          </div>
          <div className="grid gap-8 md:grid-cols-3">
            {FEATURES.map((feature, index) => (
              <Card key={feature.title} variant="elevated" className="relative overflow-hidden animate-slide-up" style={{ animationDelay: `${index * 100}ms` }}>
                <CardHeader className="text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <feature.icon className="h-7 w-7" aria-hidden />
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Live Stats / Social Proof */}
      <section className="section border-y border-border">
        <div className="container">
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            <div className="text-center p-4">
              <div className="text-4xl md:text-5xl font-bold text-primary">50K+</div>
              <div className="mt-1 text-sm text-muted-foreground">Issues Reported</div>
            </div>
            <div className="text-center p-4 border-l border-border">
              <div className="text-4xl md:text-5xl font-bold text-success">92%</div>
              <div className="mt-1 text-sm text-muted-foreground">Resolution Rate</div>
            </div>
            <div className="text-center p-4 border-l border-border">
              <div className="text-4xl md:text-5xl font-bold text-warning">24h</div>
              <div className="mt-1 text-sm text-muted-foreground">Avg. Response</div>
            </div>
            <div className="text-center p-4 border-l border-border">
              <div className="text-4xl md:text-5xl font-bold text-primary">500+</div>
              <div className="mt-1 text-sm text-muted-foreground">Active Cities</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="section-lg">
        <div className="container">
          <Card variant="brand" className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-primary/20 via-transparent to-primary/10" />
            <CardContent className="relative flex flex-col items-center justify-center gap-6 py-12 md:py-16 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/20">
                <ShieldCheck className="h-8 w-8 text-primary" aria-hidden />
              </div>
              <div className="max-w-2xl">
                <h2 className="heading-3">Ready to make a difference?</h2>
                <p className="mt-3 text-lead">
                  Join thousands of citizens improving their neighborhoods. Report your first issue in under 2 minutes.
                </p>
              </div>
              <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                <Link to="/report">
                  <Button size="lg" className="btn-brand w-full sm:w-auto gap-2" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    Report Your First Issue
                  </Button>
                </Link>
                <Link to="/map">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto bg-background/50 border-border/50 hover:bg-background" leftIcon={<Map className="h-4 w-4" />}>
                    Browse Live Map
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Emergency Notice */}
      <section className="section container">
        <Card variant="outlined" className="border-danger/30 bg-danger/5">
          <CardContent className="flex items-start gap-4 p-6">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-danger/10">
              <AlertTriangle className="h-5 w-5 text-danger" aria-hidden />
            </div>
            <div>
              <CardTitle className="text-danger">Life-threatening emergency?</CardTitle>
              <CardDescription className="mt-2">
                SafeCity is an incident coordination tool, not an emergency service. For fires,
                medical emergencies or crimes in progress, always call your local emergency
                number first (India: 112).
              </CardDescription>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  );
}