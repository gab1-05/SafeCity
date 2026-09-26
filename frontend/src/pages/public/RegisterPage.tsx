import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { authApi, departmentsApi } from "@/api/auth";
import { normalizeError, tokenStore } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import type { UserRole } from "@/types";

/** Roles a new user may request. The account is always created as
 * `citizen`; anything else becomes a pending request for admin approval.
 * `city_admin` / `superuser` are never self-requestable. */
const REQUESTABLE_ROLES = [
  { value: "citizen", label: "Citizen — report issues (default, instant access)" },
  { value: "volunteer", label: "Volunteer — help with verified incidents" },
  { value: "department_staff", label: "Department staff — manage department incidents" },
  { value: "emergency_responder", label: "Emergency responder — handle emergencies" },
] as const;

const schema = z
  .object({
    first_name: z.string().min(1, "First name is required"),
    last_name: z.string().min(1, "Last name is required"),
    email: z.string().email("Enter a valid email"),
    phone: z.string().optional(),
    password: z.string().min(10, "At least 10 characters"),
    confirm: z.string(),
    requested_role: z.string().default("citizen"),
    requested_department_id: z.string().optional(),
    role_request_reason: z.string().max(2000).optional(),
    accept_terms: z.literal(true, {
      errorMap: () => ({ message: "You must accept the terms to register" }),
    }),
  })
  .refine((data) => data.password === data.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

type FormData = z.infer<typeof schema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const { toast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [oauthUnconfigured, setOauthUnconfigured] = useState(false);

  const { data: departments } = useQuery({
    queryKey: ["departments-public"],
    queryFn: departmentsApi.list,
    staleTime: 5 * 60 * 1000,
  });

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const requestedRole = watch("requested_role");
  const needsApproval = requestedRole && requestedRole !== "citizen";

  const applyGoogleSignup = (result: {
    access: string;
    refresh: string;
    user: { id: string; email: string; role: string; full_name?: string };
  }) => {
    tokenStore.set(result.access, result.refresh);
    setUser({
      id: result.user.id,
      email: result.user.email,
      role: result.user.role as UserRole,
      full_name: result.user.full_name || result.user.email,
      department: null,
    });
    toast({
      title: "Account created with Google",
      description:
        needsApproval
          ? "Your role request was submitted for admin approval."
          : "You can now use SafeCity.",
      variant: "success",
    });
    navigate("/dashboard");
  };

  const onGoogleCredential = async (idToken: string) => {
    setSubmitting(true);
    try {
      const formValues = watch();
      const result = await authApi.googleLogin(
        idToken,
        needsApproval
          ? {
              requested_role: formValues.requested_role,
              requested_department_id: formValues.requested_department_id || undefined,
              role_request_reason: formValues.role_request_reason || "",
            }
          : undefined,
      );
      applyGoogleSignup(result);
    } catch (error) {
      const normalized = normalizeError(error);
      if (normalized.status === 503) setOauthUnconfigured(true);
      toast({
        title: "Google sign-up failed",
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
      await authApi.register({
        email: data.email,
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone,
        password: data.password,
        accept_terms: true,
        ...(data.requested_role !== "citizen"
          ? {
              requested_role: data.requested_role,
              requested_department_id: data.requested_department_id || undefined,
              role_request_reason: data.role_request_reason || "",
            }
          : {}),
      });
      toast({
        title: "Account created",
        description:
          data.requested_role !== "citizen"
            ? "You can log in now. Your role request is pending admin approval."
            : "You can now log in with your credentials.",
        variant: "success",
      });
      navigate("/login");
    } catch (error) {
      const normalized = normalizeError(error);
      toast({
        title: "Registration failed",
        description:
          Object.values(normalized.fieldErrors)[0]?.[0] ?? normalized.detail,
        variant: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const field = (
    name: keyof FormData,
    label: string,
    type = "text",
    autoComplete?: string,
  ) => (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <Input
        id={name}
        type={type}
        autoComplete={autoComplete}
        aria-invalid={!!errors[name]}
        {...register(name)}
      />
      {errors[name] && (
        <p className="text-sm text-danger" role="alert">
          {errors[name]?.message as string}
        </p>
      )}
    </div>
  );

  return (
    <div className="container flex min-h-[70vh] items-center justify-center py-10">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Create your SafeCity account</CardTitle>
          <CardDescription>Report issues and follow their resolution</CardDescription>
        </CardHeader>
        <CardContent>
          <GoogleSignInButton
            onCredential={onGoogleCredential}
            onUnavailable={() => setOauthUnconfigured(true)}
            onError={(msg) => toast({ title: "Google sign-up failed", description: msg, variant: "error" })}
          />
          {!oauthUnconfigured && (
            <div className="my-4 flex items-center gap-3" aria-hidden>
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs uppercase tracking-wide text-muted-foreground">or</span>
              <div className="h-px flex-1 bg-border" />
            </div>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div className="grid grid-cols-2 gap-3">
              {field("first_name", "First name", "text", "given-name")}
              {field("last_name", "Last name", "text", "family-name")}
            </div>
            {field("email", "Email", "email", "email")}
            {field("phone", "Phone (optional)", "tel", "tel")}
            {field("password", "Password (min 10 chars)", "password", "new-password")}
            {field("confirm", "Confirm password", "password", "new-password")}
            <div className="space-y-2">
              <Label htmlFor="requested_role">I want to join as</Label>
              <Select
                id="requested_role"
                {...register("requested_role")}
              >
                {REQUESTABLE_ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
              {needsApproval ? (
                <p className="text-xs text-muted-foreground">
                  Your account is created as citizen immediately. The selected role
                  needs an administrator's approval.
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Citizen accounts get instant access. Admins and superusers can only
                  be assigned by an existing administrator.
                </p>
              )}
              {errors.requested_role && (
                <p className="text-sm text-danger" role="alert">
                  {errors.requested_role.message}
                </p>
              )}
            </div>
            {needsApproval && (
              <>
                {requestedRole === "department_staff" && (
                  <div className="space-y-2">
                    <Label htmlFor="requested_department_id">Department</Label>
                    <Select
                      id="requested_department_id"
                      {...register("requested_department_id")}
                    >
                      <option value="">Select a department…</option>
                      {(departments ?? []).map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="role_request_reason">
                    Why do you need this role? (optional)
                  </Label>
                  <Input
                    id="role_request_reason"
                    placeholder="e.g. Volunteer with the local response team"
                    {...register("role_request_reason")}
                  />
                </div>
              </>
            )}
            <div className="flex items-start gap-2">
              <input
                id="accept_terms"
                type="checkbox"
                className="mt-1"
                aria-invalid={!!errors.accept_terms}
                {...register("accept_terms")}
              />
              <Label htmlFor="accept_terms" className="font-normal">
                I accept the terms of service and privacy policy
              </Label>
            </div>
            {errors.accept_terms && (
              <p className="text-sm text-danger" role="alert">
                {errors.accept_terms.message}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Creating account…" : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already registered?{" "}
            <Link to="/login" className="text-primary hover:underline">
              Log in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
