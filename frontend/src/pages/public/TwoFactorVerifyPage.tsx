import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ShieldCheck, RotateCcw, Key } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { authApi } from "@/api/auth";
import { normalizeError, tokenStore } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { Separator } from "@/components/ui/input";

const schema = z.object({
  token: z.string().length(6, "Enter the 6-digit code"),
});

type FormData = z.infer<typeof schema>;

export function TwoFactorVerifyPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const { toast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      const result = await authApi.verify2fa(data);
      setUser({
        id: result.user.id,
        email: result.user.email,
        role: result.user.role,
        full_name: result.user.full_name,
        department: null,
      });
      toast({ title: "Welcome back", variant: "success" });
      navigate("/dashboard");
    } catch (error) {
      toast({ title: "Verification failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container flex min-h-[70vh] items-center justify-center py-10">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <ShieldCheck className="mx-auto mb-2 h-10 w-10 text-primary" aria-hidden />
          <CardTitle className="text-2xl">Two-factor authentication</CardTitle>
          <CardDescription>Enter the 6-digit code from your authenticator app</CardDescription>
        </CardHeader>
        <CardContent>
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
                autoFocus
              />
              {errors.token && <p className="text-sm text-danger" role="alert">{errors.token.message}</p>}
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Verifying…" : "Verify"}
            </Button>

            <Separator />
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                className="flex-1"
                onClick={() => setShowRecovery(true)}
              >
                <Key className="h-4 w-4" /> Use recovery code
              </Button>
              <Button variant="ghost" size="sm" onClick={() => navigate("/login")}>
                <RotateCcw className="h-4 w-4" /> Back to login
              </Button>
            </div>
          </form>

          {showRecovery && (
            <div className="mt-4 space-y-2">
              <p className="text-sm text-muted-foreground">
                Enter one of your recovery codes (8 hex characters).
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const formData = new FormData(e.currentTarget);
                  handleSubmit(onSubmit)({ token: formData.get("recovery") as string } as FormData);
                }}
                className="space-y-2"
              >
                <Input
                  name="recovery"
                  type="text"
                  inputMode="text"
                  maxLength={8}
                  placeholder="ABCD1234"
                  autoComplete="off"
                />
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? "Verifying…" : "Verify recovery code"}
                </Button>
              </form>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}