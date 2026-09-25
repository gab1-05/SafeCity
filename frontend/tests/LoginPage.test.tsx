import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginPage } from "@/pages/public/LoginPage";
import { ToastProvider } from "@/components/ui/toast";
import { authApi } from "@/api/auth";

vi.mock("@/api/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/auth")>();
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      login: vi.fn(),
    },
  };
});

function renderLogin() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
  });

  it("shows validation errors for empty submission", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findAllByRole("alert")).toHaveLength(2);
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it("submits credentials and shows success toast", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockResolvedValueOnce({
      access: "a",
      refresh: "r",
      user: {
        id: "1",
        email: "c@test.local",
        role: "citizen",
        full_name: "Citi Zen",
      },
    });
    renderLogin();
    await user.type(screen.getByLabelText(/email/i), "c@test.local");
    await user.type(screen.getByLabelText(/password/i), "Password123!");
    await user.click(screen.getByRole("button", { name: /log in/i }));
    await waitFor(() => expect(authApi.login).toHaveBeenCalledWith({
      email: "c@test.local",
      password: "Password123!",
    }));
    expect(await screen.findByText(/welcome back/i)).toBeInTheDocument();
  });

  it("shows error toast on failed login", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 401, data: { detail: "Invalid credentials." } },
    });
    renderLogin();
    await user.type(screen.getByLabelText(/email/i), "c@test.local");
    await user.type(screen.getByLabelText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/login failed/i)).toBeInTheDocument();
  });
});
