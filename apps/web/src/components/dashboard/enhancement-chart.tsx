"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useEnhancementActivity } from "@/lib/queries";
import { humanizeBytes } from "@/lib/utils";

const chartConfig = {
  bytes: {
    label: "Enhanced output",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

const skeletonBarHeights = ["h-24", "h-32", "h-20", "h-36", "h-28", "h-40", "h-24"];

function ChartSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="h-[240px] w-full rounded-md border border-border bg-muted/20 px-4 py-4"
    >
      <span className="sr-only">Loading enhanced-output activity</span>
      <div aria-hidden className="flex h-full items-end gap-3">
        {skeletonBarHeights.map((height, i) => (
          <Skeleton
            key={i}
            className={`${height} min-w-0 flex-1 motion-reduce:animate-none`}
          />
        ))}
      </div>
    </div>
  );
}

export function EnhancementChart() {
  const { data: activity, isLoading, error, refetch } = useEnhancementActivity(7);

  const data = useMemo(
    () =>
      (activity ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        bytes: d.bytes,
      })),
    [activity],
  );

  const total = data.reduce((sum, d) => sum + d.bytes, 0);
  const hasKnownActivity = activity !== undefined;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Enhanced Output Volume</CardTitle>
        <CardDescription className="text-xs">
          48 kHz WAV bytes written to B2, last 7 days
        </CardDescription>
        <CardAction className="text-right self-center">
          {isLoading ? (
            <div aria-hidden className="space-y-1">
              <Skeleton className="ml-auto h-2.5 w-10 motion-reduce:animate-none" />
              <Skeleton className="ml-auto h-6 w-12 motion-reduce:animate-none" />
            </div>
          ) : (
            <>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Total
              </div>
              <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
                {hasKnownActivity ? humanizeBytes(total) : "-"}
              </div>
            </>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <ChartSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No enhancements yet"
            description="Run an enhancement to see output volume grow here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
              <defs>
                <linearGradient id="bytes-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-bytes)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-bytes)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="var(--border)"
              />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={10}
                fontSize={11}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={6}
                fontSize={11}
                width={52}
                tickFormatter={(v) => humanizeBytes(Number(v))}
              />
              <ChartTooltip
                cursor={{ fill: "var(--accent-subtle)" }}
                content={
                  <ChartTooltipContent
                    formatter={(value) => humanizeBytes(Number(value))}
                  />
                }
              />
              <Bar
                dataKey="bytes"
                fill="url(#bytes-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
