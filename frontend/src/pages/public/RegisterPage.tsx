import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { authApi } from "@/api/auth";
import { normalizeError } from "@/api/client";

const schema = z
  .object({
    first_name: z.string().min(1, "First name is required"),
    last_name: z.string().min(1, "Last name is required"),
    email: z.string().email("Enter a valid email"),
    phone: z.string().optional(),
    password: z.string().min(10, "At least 10 characters"),
    confirm: z.string(),
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
  const { toast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

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
      });
      toast({
        title: "Account created",
        description: "You can now log in with your credentials.",
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
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div className="grid grid-cols-2 gap-3">
              {field("first_name", "First name", "text", "given-name")}
              {field("last_name", "Last name", "text", "family-name")}
            </div>
            {field("email", "Email", "email", "email")}
            {field("phone", "Phone (optional)", "tel", "tel")}
            {field("password", "Password (min 10 chars)", "password", "new-password")}
            {field("confirm", "Confirm password", "password", "new-password")}
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
