import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function AboutPage() {
  return (
    <div className="container max-w-3xl py-12">
      <h1 className="text-3xl font-bold">About SafeCity</h1>
      <p className="mt-4 text-muted-foreground">
        SafeCity is a Smart City Incident Management and Civic Response Platform developed as a
        Software Development Project (SDP) at The Bombay Salesian Society. It gives citizens a
        simple way to report civic problems and gives municipal teams the tools to verify,
        prioritize, assign, and resolve them — transparently.
      </p>

      <div className="mt-8 grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>What SafeCity does</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>• Citizens report incidents with photos, location, and description.</p>
            <p>• Authorities verify reports and route them to the right department.</p>
            <p>• Staff work incidents under SLA deadlines with escalation on breach.</p>
            <p>• Everyone sees a transparent, privacy-safe public timeline.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Privacy by design</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>• Anonymous reporting is supported where enabled.</p>
            <p>• Public maps show approximate locations, never exact home coordinates.</p>
            <p>• Personal contact details are never shown publicly.</p>
            <p>• Photos are stripped of EXIF/GPS metadata automatically.</p>
          </CardContent>
        </Card>

        <Card className="border-danger/40">
          <CardHeader>
            <CardTitle className="text-danger">Not an emergency service</CardTitle>
            <CardDescription>
              SafeCity coordinates civic incident follow-up. It is not an official government
              system and does not replace emergency services. For life-threatening situations
              call 112 (India) or your local emergency number.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}
