import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { authApi } from "@/api/auth";
import { normalizeError, tokenStore } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import type { UserRole } from "@/types";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setUser = useAuthStore((s) => s.setUser);
  const { toast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [oauthUnconfigured, setOauthUnconfigured] = useState(false);
  const [requires2fa, setRequires2fa] = useState(false);
  const [pendingUser, setPendingUser] = useState<{
    id: string;
    email: string;
    role: UserRole;
    full_name?: string;
    department?: { name?: string } | null;
  } | null>(null);

  const applyLogin = (result: {
    access: string;
    refresh: string;
    user: {
      id: string;
      email: string;
      role: UserRole;
      first_name?: string;
      last_name?: string;
      full_name?: string;
      department?: { name?: string } | null;
    };
  }) => {
    tokenStore.set(result.access, result.refresh);
    setUser({
      id: result.user.id,
      email: result.user.email,
      role: result.user.role,
      full_name:
        result.user.full_name ||
        `${result.user.first_name ?? ""} ${result.user.last_name ?? ""}`.trim() ||
        result.user.email,
      department: result.user.department?.name ?? null,
    });
    toast({ title: "Welcome back", variant: "success" });
    const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;
    navigate(from ?? "/dashboard");
  };

  const onGoogleCredential = async (idToken: string) => {
    setSubmitting(true);
    try {
      const result = await authApi.googleLogin(idToken);
      applyLogin(result);
    } catch (error) {
      const normalized = normalizeError(error);
      if (normalized.status === 503) {
        setOauthUnconfigured(true);
      }
      toast({
        title: "Google sign-in failed",
        description: normalized.detail,
        variant: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      const result = await authApi.login(data);
      if (result.requires_2fa) {
        setPendingUser({
          id: result.user.id,
          email: result.user.email,
          role: result.user.role,
          full_name: result.user.full_name,
        });
        setRequires2fa(true);
        return;
      }
      applyLogin(result);
    } catch (error) {
      const normalized = normalizeError(error);
      toast({
        title: normalized.status === 423 ? "Account locked" : "Login failed",
        description: normalized.detail,
        variant: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  if (requires2fa && pendingUser) {
    return (
      <div className="container flex min-h-[70vh] items-center justify-center py-10">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <ShieldCheck className="mx-auto mb-2 h-10 w-10 text-primary" aria-hidden />
            <CardTitle className="text-2xl">Two-factor authentication</CardTitle>
            <CardDescription>Enter the 6-digit code from your authenticator app</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const token = formData.get("token") as string;
                setSubmitting(true);
                try {
                  const result = await authApi.verify2fa({ token });
                  applyLogin({
                    access: result.access,
                    refresh: result.refresh,
                    user: result.user,
                  });
                } catch (error) {
                  toast({ title: "Verification failed", description: normalizeError(error).detail, variant: "error" });
                } finally {
                  setSubmitting(false);
                }
              }}
              className="space-y-4"
            >
              <Input
                name="token"
                type="text"
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                autoFocus
                required
              />
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Verifying…" : "Verify"}
              </Button>
              <p className="text-sm text-muted-foreground text-center">
                <Link to="/login" className="text-primary hover:underline">
                  Back to login
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container flex min-h-[70vh] items-center justify-center py-10">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <ShieldCheck className="mx-auto mb-2 h-10 w-10 text-primary" aria-hidden />
          <CardTitle className="text-2xl">Log in to SafeCity</CardTitle>
          <CardDescription>Track reports and manage incidents</CardDescription>
        </CardHeader>
        <CardContent>
          <GoogleSignInButton
            onCredential={onGoogleCredential}
            onUnavailable={() => setOauthUnconfigured(true)}
            onError={(msg) => toast({ title: "Google sign-in failed", description: msg, variant: "error" })}
          />
          {!oauthUnconfigured && (
            <div className="my-4 flex items-center gap-3" aria-hidden>
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs uppercase tracking-wide text-muted-foreground">or</span>
              <div className="h-px flex-1 bg-border" />
            </div>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                aria-invalid={!!errors.email}
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-danger" role="alert">
                  {errors.email.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={!!errors.password}
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-danger" role="alert">
                  {errors.password.message}
                </p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Logging in…" : "Log in"}
            </Button>
          </form>
          <div className="mt-4 flex flex-col items-center gap-2 text-sm">
            <Link to="/forgot-password" className="text-primary hover:underline">
              Forgot password?
            </Link>
            <span className="text-muted-foreground">
              New citizen?{" "}
              <Link to="/register" className="text-primary hover:underline">
                Create an account
              </Link>
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
