import type { Metadata } from "next";
import { ClientsRedirectClient } from "@/components/clients/ClientsRedirectClient";

export const metadata: Metadata = {
  title: "Clients - PersonnaPress",
  robots: { index: false },
};

export default function ClientsPage() {
  return <ClientsRedirectClient />;
}
