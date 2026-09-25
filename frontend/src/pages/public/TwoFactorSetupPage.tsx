import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ShieldCheck, QrCode, Key, Download, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { authApi } from "@/api/auth";
import { normalizeError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { Separator } from "@/components/ui/input";

const schema = z.object({
  token: z.string().length(6, "Enter the 6-digit code from your authenticator app"),
});

type FormData = z.infer<typeof schema>;

export function TwoFactorSetupPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const { toast } = useToast();
  const [step, setStep] = useState<"setup" | "verify" | "complete">("setup");
  const [secret, setSecret] = useState("");
  const [otpauthUri, setOtpauthUri] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const loadSetup = async () => {
    try {
      const data = await authApi.setup2fa();
      setSecret(data.secret);
      setOtpauthUri(data.otpauth_uri);
      setRecoveryCodes(data.recovery_codes);
    } catch (error) {
      toast({ title: "Failed to load 2FA setup", description: normalizeError(error).detail, variant: "error" });
    }
  };

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      const result = await authApi.disable2fa(data);
      toast({ title: "2FA enabled", description: result.detail, variant: "success" });
      setStep("complete");
    } catch (error) {
      toast({ title: "Verification failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setSubmitting(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: `${label} copied`, variant: "success" });
  };

  return (
    <div className="container flex min-h-[70vh] items-center justify-center py-10">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <ShieldCheck className="mx-auto mb-2 h-10 w-10 text-primary" aria-hidden />
          <CardTitle className="text-2xl">
            {step === "setup" ? "Set up two-factor authentication" : step === "verify" ? "Verify authenticator app" : "2FA enabled"}
          </CardTitle>
          <CardDescription>
            {step === "setup" && "Add an extra layer of security to your account."}
            {step === "verify" && "Enter the 6-digit code from your authenticator app."}
            {step === "complete" && "Your account is now protected with two-factor authentication."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {step === "setup" && (
            <div className="space-y-6">
              <div className="rounded-lg border bg-muted p-4 text-center">
                <QrCode className="mx-auto mb-2 h-10 w-10 text-primary" aria-hidden />
                <p className="font-medium">Scan with authenticator app</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Google Authenticator, Authy, 1Password, Microsoft Authenticator, etc.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="secret">Manual entry key</Label>
                <div className="flex gap-2">
                  <Input
                    id="secret"
                    value={secret}
                    readOnly
                    className="font-mono text-sm flex-1"
                  />
                  <Button variant="outline" onClick={() => copyToClipboard(secret, "Secret key")}>
                    Copy
                  </Button>
                </div>
              </div>

              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Recovery codes</Label>
                  <Button variant="ghost" size="sm" onClick={() => copyToClipboard(recoveryCodes.join("\n"), "Recovery codes")}>
                    <Download className="h-4 w-4" /> Copy all
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm font-mono">
                  {recoveryCodes.map((code, i) => (
                    <div key={i} className="rounded border bg-card p-2 text-center">
                      {code}
                    </div>
                  ))}
                </div>
                <p className="text-xs text-warning flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Save these codes in a secure place. They are shown only once and can be used to
                  access your account if you lose your authenticator device.
                </p>
              </div>

              <Button className="w-full" onClick={() => setStep("verify")} disabled={!secret}>
                I've scanned the code — verify
              </Button>
            </div>
          )}

          {step === "verify" && (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-2">
                <Label htmlFor="token">6-digit code</Label>
                <Input
                  id="token"
                  type="text"
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  aria-invalid={!!errors.token}
                  {...register("token")}
                />
                {errors.token && <p className="text-sm text-danger" role="alert">{errors.token.message}</p>}
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Verifying…" : "Verify & enable 2FA"}
              </Button>
            </form>
          )}

          {step === "complete" && (
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
                <ShieldCheck className="h-8 w-8 text-success" aria-hidden />
              </div>
              <p className="text-sm text-muted-foreground">
                You'll need to enter a code from your authenticator app each time you log in.
              </p>
              <Button className="w-full" onClick={() => navigate("/dashboard")}>
                Continue to dashboard
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}