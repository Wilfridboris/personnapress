import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ClientStore {
  activeClientId: string | null;
  setActiveClientId: (id: string) => void;
}

export const useClientStore = create<ClientStore>()(
  persist(
    (set) => ({
      activeClientId: null,
      setActiveClientId: (id) => set({ activeClientId: id }),
    }),
    {
      name: "personapress-active-client",
    }
  )
);
