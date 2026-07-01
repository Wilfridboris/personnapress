import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ClientListItem } from "@/lib/types";

interface ClientStore {
  clients: ClientListItem[];
  activeClientId: string | null;
  isInitialized: boolean;
  setClients: (clients: ClientListItem[]) => void;
  setActiveClientId: (id: string) => void;
  setInitialized: () => void;
  addClient: (client: ClientListItem) => void;
  updateClientName: (id: string, name: string) => void;
  removeClient: (id: string) => void;
}

export const useClientStore = create<ClientStore>()(
  persist(
    (set) => ({
      clients: [],
      activeClientId: null,
      isInitialized: false,
      setClients: (clients) => set({ clients }),
      setActiveClientId: (id) => set({ activeClientId: id }),
      setInitialized: () => set({ isInitialized: true }),
      addClient: (client) =>
        set((state) => ({ clients: [...state.clients, client] })),
      updateClientName: (id, name) =>
        set((state) => ({
          clients: state.clients.map((c) => (c.id === id ? { ...c, name } : c)),
        })),
      removeClient: (id) =>
        set((state) => {
          const remaining = state.clients.filter((c) => c.id !== id);
          const activeClientId =
            state.activeClientId === id
              ? (remaining[0]?.id ?? null)
              : state.activeClientId;
          return { clients: remaining, activeClientId };
        }),
    }),
    {
      name: "personapress-active-client",
      partialize: (state) => ({ activeClientId: state.activeClientId }),
    }
  )
);
