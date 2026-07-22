import Link from "next/link";
import { AudioLines } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentEnhancementsTable } from "@/components/dashboard/recent-enhancements-table";
import { EnhancementChart } from "@/components/dashboard/enhancement-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Batch audio super-resolution on Backblaze B2 — every restored file
            expands 5–10× as it upscales to 48 kHz.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/jobs">
            <AudioLines className="h-3.5 w-3.5" />
            New enhancement
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <EnhancementChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentEnhancementsTable />
        </div>
      </div>
    </div>
  );
}
