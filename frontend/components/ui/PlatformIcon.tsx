import { GitBranch, Globe, LayoutGrid, Share2, Link2 } from "lucide-react";

interface Props {
  platform: string;
  className?: string;
}

export function PlatformIcon({ platform, className = "size-3.5" }: Props) {
  if (platform === "wordpress" || platform === "wordpress-com")
    return <Globe className={className} aria-hidden="true" />;
  if (platform === "webflow")
    return <LayoutGrid className={className} aria-hidden="true" />;
  if (platform === "x")
    return <Share2 className={className} aria-hidden="true" />;
  if (platform === "github_pages")
    return <GitBranch className={className} aria-hidden="true" />;
  return <Link2 className={className} aria-hidden="true" />;
}
