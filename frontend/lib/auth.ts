import { fetchAPI } from "./api";

export async function logout(router: { push: (path: string) => void }): Promise<void> {
  await fetchAPI("/auth/logout", { method: "POST" });
  router.push("/login");
}
