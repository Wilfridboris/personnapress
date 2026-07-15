import { fetchAPI } from "./api";
import { useClientStore } from "./stores/useClientStore";

export async function logout(router: { push: (path: string) => void }): Promise<void> {
  await fetchAPI("/auth/logout", { method: "POST" });
  useClientStore.getState().setClients([]);
  useClientStore.setState({ activeClientId: null, isInitialized: false });
  router.push("/login");
}
