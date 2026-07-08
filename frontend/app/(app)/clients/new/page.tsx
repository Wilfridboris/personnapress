import type { Metadata } from "next";
import { CreateClientForm } from "@/components/clients/CreateClientForm";

export const metadata: Metadata = {
  title: "New Client | PersonnaPress",
  robots: { index: false },
};

export default function NewClientPage() {
  return (
    <div className="max-w-[720px] px-8">
      <CreateClientForm />
    </div>
  );
}
