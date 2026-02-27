"use client";

import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Minus,
  FileEdit,
  FileText,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PatchChange {
  content_before: string;
  content_after: string;
}

interface PatchResult {
  file_path: string;
  status: "success" | "error" | "warning";
  message: string;
  additions: number;
  deletions: number;
  old_content?: string;
  new_content?: string;
  timestamp: string;
}

interface PatchFileViewerProps {
  onPatch?: (
    filePath: string,
    contentBefore: string,
    contentAfter: string
  ) => Promise<PatchResult>;
}

export function PatchFileViewer({ onPatch }: PatchFileViewerProps) {
  const [filePath, setFilePath] = useState("");
  const [contentBefore, setContentBefore] = useState("");
  const [contentAfter, setContentAfter] = useState("");
  const [results, setResults] = useState<PatchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(
    new Set()
  );

  const handlePatch = async () => {
    if (!filePath.trim() || !contentBefore.trim() || !contentAfter.trim()) {
      alert("Please fill in all fields");
      return;
    }

    setIsLoading(true);
    try {
      const result = onPatch
        ? await onPatch(filePath, contentBefore, contentAfter)
        : {
            file_path: filePath,
            status: "success" as const,
            message: "Patch applied successfully",
            additions: contentAfter.split("\n").length,
            deletions: contentBefore.split("\n").length,
            old_content: contentBefore,
            new_content: contentAfter,
            timestamp: new Date().toISOString(),
          };

      setResults([result, ...results]);

      // Reset form on success
      if (result.status === "success") {
        setFilePath("");
        setContentBefore("");
        setContentAfter("");
      }
    } catch (error) {
      setResults([
        {
          file_path: filePath,
          status: "error",
          message: error instanceof Error ? error.message : "Unknown error",
          additions: 0,
          deletions: 0,
          timestamp: new Date().toISOString(),
        },
        ...results,
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleResult = (id: string) => {
    const next = new Set(expandedResults);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedResults(next);
  };

  const expandAll = () => {
    setExpandedResults(new Set(results.map((_, i) => String(i))));
  };

  const collapseAll = () => {
    setExpandedResults(new Set());
  };

  const clearResults = () => {
    setResults([]);
  };

  return (
    <div className="space-y-6">
      {/* Input Section */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-2">
                File Path
              </label>
              <Input
                placeholder="e.g., src/components/Button.tsx"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="text-sm font-medium block mb-2">
                Content Before (EXACT match required)
              </label>
              <Textarea
                placeholder="The exact block of code to replace..."
                value={contentBefore}
                onChange={(e) => setContentBefore(e.target.value)}
                disabled={isLoading}
                className="font-mono text-xs h-32"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Must match exactly including whitespace and indentation
              </p>
            </div>

            <div>
              <label className="text-sm font-medium block mb-2">
                Content After
              </label>
              <Textarea
                placeholder="The new block of code..."
                value={contentAfter}
                onChange={(e) => setContentAfter(e.target.value)}
                disabled={isLoading}
                className="font-mono text-xs h-32"
              />
            </div>

            <Button
              onClick={handlePatch}
              disabled={isLoading}
              size="lg"
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Patching...
                </>
              ) : (
                <>
                  <FileEdit className="mr-2 h-4 w-4" />
                  Apply Patch
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Section */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-primary/10">
                <FileEdit className="size-4 text-primary" />
              </div>
              <div>
                <span className="text-base font-medium tabular-nums">
                  {results.length}
                </span>
                <span className="text-sm text-muted-foreground ml-1.5">
                  {results.length === 1 ? "patch" : "patches"} applied
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={expandAll}>
                Expand all
              </Button>
              <Button variant="ghost" size="sm" onClick={collapseAll}>
                Collapse all
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearResults}
                className="text-muted-foreground hover:text-foreground"
              >
                Clear
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            {results.map((result, index) => (
              <PatchResultCard
                key={index}
                result={result}
                index={String(index)}
                expanded={expandedResults.has(String(index))}
                onToggle={() => toggleResult(String(index))}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PatchResultCard({
  result,
  index,
  expanded,
  onToggle,
}: {
  result: PatchResult;
  index: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const statusConfig = getStatusConfig(result.status);
  const additions = result.additions || 0;
  const deletions = result.deletions || 0;

  const copyPath = () => {
    navigator.clipboard.writeText(result.file_path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const pathParts = result.file_path.split("/");
  const fileName = pathParts.pop();
  const directory = pathParts.join("/");

  const StatusIcon =
    result.status === "success"
      ? CheckCircle2
      : result.status === "error"
        ? XCircle
        : AlertCircle;

  return (
    <Card className="overflow-hidden">
      <button
        onClick={onToggle}
        className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-muted/50 transition-colors"
      >
        <div className="shrink-0">
          {expanded ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </div>

        <div className={cn("p-1.5 rounded-md shrink-0", statusConfig.bg)}>
          <StatusIcon className={cn("size-4", statusConfig.color)} />
        </div>

        <div className="flex-1 min-w-0 flex items-center gap-2">
          {directory && (
            <span className="text-sm text-muted-foreground font-mono truncate">
              {directory}/
            </span>
          )}
          <span className="text-sm font-medium font-mono truncate">
            {fileName}
          </span>
          {result.status === "warning" && (
            <Badge
              variant="outline"
              className="text-[10px] shrink-0 gap-1 bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
            >
              <AlertCircle className="size-3" />
              Warning
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Change bar visualization */}
          <div className="hidden sm:flex items-center gap-0.5">
            {Array.from({ length: Math.min(5, additions) }).map((_, i) => (
              <div
                key={`add-${i}`}
                className="w-1.5 h-3 rounded-sm bg-emerald-500"
              />
            ))}
            {Array.from({ length: Math.min(5, deletions) }).map((_, i) => (
              <div
                key={`del-${i}`}
                className="w-1.5 h-3 rounded-sm bg-red-500"
              />
            ))}
            {additions + deletions === 0 && (
              <div className="w-1.5 h-3 rounded-sm bg-muted-foreground" />
            )}
          </div>

          <div className="flex items-center gap-2 text-xs tabular-nums">
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              +{additions}
            </span>
            <span className="text-red-600 dark:text-red-400 font-medium">
              -{deletions}
            </span>
          </div>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <CardContent className="p-0 border-t border-border/60">
          <div className="space-y-4 p-4">
            {/* Message */}
            <div>
              <p className="text-sm font-medium mb-1">Status</p>
              <p className={cn("text-sm", statusConfig.textClass)}>
                {result.message}
              </p>
            </div>

            {/* Timestamp */}
            <div>
              <p className="text-xs text-muted-foreground">
                {new Date(result.timestamp).toLocaleString()}
              </p>
            </div>

            {/* Diff view */}
            {result.old_content && result.new_content && (
              <div className="relative">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="absolute top-2 right-2 z-10 opacity-10 hover:opacity-100 focus:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    copyPath();
                  }}
                >
                  {copied ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>

                <DiffView
                  before={result.old_content}
                  after={result.new_content}
                />
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function DiffView({
  before,
  after,
}: {
  before: string;
  after: string;
}) {
  const beforeLines = before.split("\n");
  const afterLines = after.split("\n");

  return (
    <div className="overflow-x-auto border rounded-md">
      <table className="w-full text-xs font-mono">
        <tbody>
          {/* Deletions */}
          {beforeLines.map((line, idx) => (
            <tr
              key={`before-${idx}`}
              className="bg-red-500/10 hover:bg-red-500/20 transition-colors"
            >
              <td className="w-12 px-2 py-0.5 text-right select-none border-r border-border/30 bg-red-500/5 text-red-600/70 dark:text-red-400/70">
                {idx + 1}
              </td>
              <td className="w-12 px-2 py-0.5 text-right select-none border-r border-border/30 text-muted-foreground/50"></td>
              <td className="px-4 py-0.5 whitespace-pre text-red-700 dark:text-red-300">
                -{line || " "}
              </td>
            </tr>
          ))}

          {/* Additions */}
          {afterLines.map((line, idx) => (
            <tr
              key={`after-${idx}`}
              className="bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors"
            >
              <td className="w-12 px-2 py-0.5 text-right select-none border-r border-border/30 text-muted-foreground/50"></td>
              <td className="w-12 px-2 py-0.5 text-right select-none border-r border-border/30 bg-emerald-500/5 text-emerald-600/70 dark:text-emerald-400/70">
                {idx + 1}
              </td>
              <td className="px-4 py-0.5 whitespace-pre text-emerald-700 dark:text-emerald-300">
                +{line || " "}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function getStatusConfig(status: string) {
  switch (status) {
    case "success":
      return {
        color: "text-emerald-600 dark:text-emerald-400",
        bg: "bg-emerald-500/10",
        textClass: "text-emerald-700 dark:text-emerald-300",
      };
    case "error":
      return {
        color: "text-red-600 dark:text-red-400",
        bg: "bg-red-500/10",
        textClass: "text-red-700 dark:text-red-300",
      };
    case "warning":
      return {
        color: "text-amber-600 dark:text-amber-400",
        bg: "bg-amber-500/10",
        textClass: "text-amber-700 dark:text-amber-300",
      };
    default:
      return {
        color: "text-muted-foreground",
        bg: "bg-muted",
        textClass: "text-muted-foreground",
      };
  }
}