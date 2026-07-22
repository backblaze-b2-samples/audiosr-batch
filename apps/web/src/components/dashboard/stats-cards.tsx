"use client";

import { AudioLines, TrendingUp, Gauge, ListChecks } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useEnhancementStats } from "@/lib/queries";

function kHz(rate: number) {
  return `${Math.round(rate / 1000)} kHz`;
}

export function StatsCards() {
  const { data: stats, isLoading, error, refetch } = useEnhancementStats();

  // Surface fetch failures inline rather than rendering zeros — that would lie
  // about the pipeline state when really the API is just unreachable.
  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const amp =
    stats && stats.amplification_ratio > 0
      ? `${stats.amplification_ratio.toFixed(1)}×`
      : "—";
  const bandwidth =
    stats && stats.avg_input_sample_rate > 0
      ? `${kHz(stats.avg_input_sample_rate)} → ${kHz(stats.avg_output_sample_rate)}`
      : "—";
  const byStatus = stats?.jobs_by_status ?? {};

  const cards = [
    {
      title: "Files enhanced",
      value: stats?.files_enhanced ?? 0,
      icon: AudioLines,
      hint: `${stats?.jobs_total ?? 0} jobs total`,
    },
    {
      title: "Storage amplification",
      value: amp,
      icon: TrendingUp,
      hint: `${stats?.total_original_human ?? "0 B"} → ${stats?.total_enhanced_human ?? "0 B"}`,
    },
    {
      title: "Avg bandwidth gain",
      value: bandwidth,
      icon: Gauge,
      hint: "input → output sample rate",
    },
    {
      title: "Jobs by status",
      value: stats?.jobs_total ?? 0,
      icon: ListChecks,
      hint: `${byStatus.completed ?? 0} done · ${byStatus.processing ?? 0} running · ${byStatus.failed ?? 0} failed`,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="stat-value">{card.value}</div>
                <p className="mt-1 text-xs text-muted-foreground">{card.hint}</p>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
