"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { LoginForm } from "./login-form";
import { Nav } from "./nav";

export function AuthGate({ children }: { children: ReactNode }) {
  const { token } = useAuth();

  if (!token) return <LoginForm />;

  return (
    <div className="flex h-dvh flex-col">
      <Nav />
      <main className="flex-1 overflow-y-auto bg-muted/20">{children}</main>
    </div>
  );
}
