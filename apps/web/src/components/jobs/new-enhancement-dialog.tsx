"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { AudioLines, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { EmptyState } from "@/components/ui/empty-state";
import { ApiError } from "@/lib/api-client";
import { useCreateJob, useLibrary } from "@/lib/queries";
import type { QualityPreset } from "@audiosr-batch/shared";

// Human-facing preset copy. Server maps preset → ddim_steps (25/50/100).
const PRESETS: { value: QualityPreset; label: string; hint: string }[] = [
  { value: "fast", label: "Fast", hint: "25 steps — quickest, good for a first pass" },
  { value: "balanced", label: "Balanced", hint: "50 steps — recommended default" },
  { value: "high", label: "High", hint: "100 steps — best fidelity, slowest" },
];

const schema = z.object({
  inputKey: z.string().min(1, "Select an audio file to enhance"),
  qualityPreset: z.enum(["fast", "balanced", "high"]),
  // Optional integer seed; blank = random (server records the seed it used).
  seed: z
    .string()
    .regex(/^\d*$/, "Digits only")
    .optional(),
});

type FormValues = z.infer<typeof schema>;

export function NewEnhancementDialog() {
  const [open, setOpen] = useState(false);
  const { data: tracks = [], isLoading } = useLibrary();
  const createJob = useCreateJob();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { inputKey: "", qualityPreset: "balanced", seed: "" },
  });

  const onSubmit = (values: FormValues) => {
    createJob.mutate(
      {
        input_key: values.inputKey,
        quality_preset: values.qualityPreset,
        seed: values.seed ? Number(values.seed) : null,
      },
      {
        onSuccess: () => {
          toast.success("Enhancement queued", {
            description: "It will run shortly — watch the status update live.",
          });
          form.reset({ inputKey: "", qualityPreset: "balanced", seed: "" });
          setOpen(false);
        },
        onError: (err) => {
          const detail =
            err instanceof ApiError ? err.message : "Failed to create enhancement";
          toast.error(detail);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Plus className="h-3.5 w-3.5" />
          New enhancement
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New enhancement</DialogTitle>
          <DialogDescription>
            Super-resolve an ingested original to 48 kHz with AudioSR. Tip: pick
            a short clip (a few seconds) for a fast first run.
          </DialogDescription>
        </DialogHeader>

        {!isLoading && tracks.length === 0 ? (
          <EmptyState
            icon={AudioLines}
            title="No audio ingested yet"
            description="Upload an MP3/WAV/OGG on the Upload page first, then enhance it here."
          />
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <FormField
                control={form.control}
                name="inputKey"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Source audio</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select an ingested original" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {tracks.map((t) => (
                          <SelectItem key={t.original_key} value={t.original_key}>
                            {t.collection} / {t.original_filename}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Only files under <code>originals/</code> can be enhanced.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="qualityPreset"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Quality preset</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {PRESETS.map((p) => (
                          <SelectItem key={p.value} value={p.value}>
                            {p.label} — {p.hint}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Higher quality runs more diffusion steps (slower).
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="seed"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Seed (optional)</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="numeric"
                        placeholder="42"
                        className="max-w-[10rem] font-mono tabular-nums"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Leave blank for a random seed. The seed used is recorded on
                      the job for reproducibility.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setOpen(false)}
                  disabled={createJob.isPending}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createJob.isPending}>
                  {createJob.isPending ? "Queuing..." : "Enhance"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
