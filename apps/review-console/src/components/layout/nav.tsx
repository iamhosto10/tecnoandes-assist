"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mountain, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { ShortcutsHelpDialog } from "./shortcuts-help-dialog";

const LINKS = [
  { href: "/", label: "Cola" },
  { href: "/documents", label: "Base de conocimiento" },
  { href: "/gaps", label: "Brechas" },
];

export function Nav() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <header className="flex items-center justify-between border-b bg-background px-4 py-2.5 sm:px-6">
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Mountain className="size-4" />
          </div>
          <span className="text-sm font-semibold">TecnoAndes — Consola</span>
        </Link>
        <nav className="flex items-center gap-1">
          {LINKS.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center gap-1">
        <ShortcutsHelpDialog />
        <Button variant="ghost" size="icon" aria-label="Cerrar sesión" onClick={logout}>
          <LogOut className="size-4" />
        </Button>
      </div>
    </header>
  );
}
