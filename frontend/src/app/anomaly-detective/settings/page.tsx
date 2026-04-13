'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings,
  Save,
  RotateCcw,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Shield,
  Zap,
  Scale,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { listDetectionRules, updateDetectionRule } from '@/lib/api';
import type { DetectionRule, RuleType } from '@/lib/types';

const RULE_TYPE_INFO: Record<RuleType, { label: string; color: string }> = {
  STATISTICAL: { label: 'Statistical', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  RULE_BASED: { label: 'Rule-Based', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' },
  ML: { label: 'Machine Learning', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
  PATTERN: { label: 'Pattern', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
};

interface EditableRule {
  id: string;
  enabled: boolean;
  severity: string;
  parameters: Record<string, unknown>;
}

type PresetType = 'conservative' | 'balanced' | 'aggressive';

const PRESETS: Record<PresetType, { label: string; icon: React.ReactNode; desc: string }> = {
  conservative: { label: 'Conservative', icon: <Shield className="h-4 w-4" />, desc: 'High thresholds, fewer alerts' },
  balanced: { label: 'Balanced', icon: <Scale className="h-4 w-4" />, desc: 'Default recommended settings' },
  aggressive: { label: 'Aggressive', icon: <Zap className="h-4 w-4" />, desc: 'Low thresholds, more alerts' },
};

function getPresetMultiplier(preset: PresetType): number {
  if (preset === 'conservative') return 1.5;
  if (preset === 'aggressive') return 0.6;
  return 1.0;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [edits, setEdits] = useState<Record<string, EditableRule>>({});
  const [saveStatus, setSaveStatus] = useState<Record<string, 'saving' | 'saved' | 'error'>>({});

  const { data: rules, isLoading, error } = useQuery({
    queryKey: ['detection-rules'],
    queryFn: listDetectionRules,
  });

  // Initialize edits from fetched rules
  useEffect(() => {
    if (rules && Object.keys(edits).length === 0) {
      const initial: Record<string, EditableRule> = {};
      rules.forEach((r) => {
        initial[r.id] = {
          id: r.id,
          enabled: r.enabled,
          severity: r.severity,
          parameters: { ...r.parameters },
        };
      });
      setEdits(initial);
    }
  }, [rules, edits]);

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<DetectionRule> }) =>
      updateDetectionRule(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
    },
  });

  const handleToggle = useCallback((ruleId: string) => {
    setEdits((prev) => ({
      ...prev,
      [ruleId]: { ...prev[ruleId], enabled: !prev[ruleId]?.enabled },
    }));
  }, []);

  const handleParamChange = useCallback((ruleId: string, key: string, value: unknown) => {
    setEdits((prev) => ({
      ...prev,
      [ruleId]: {
        ...prev[ruleId],
        parameters: { ...prev[ruleId]?.parameters, [key]: value },
      },
    }));
  }, []);

  const saveRule = useCallback(async (ruleId: string) => {
    const edit = edits[ruleId];
    if (!edit) return;
    setSaveStatus((prev) => ({ ...prev, [ruleId]: 'saving' }));
    try {
      await updateMutation.mutateAsync({
        id: ruleId,
        payload: { enabled: edit.enabled, severity: edit.severity as DetectionRule['severity'], parameters: edit.parameters },
      });
      setSaveStatus((prev) => ({ ...prev, [ruleId]: 'saved' }));
      setTimeout(() => setSaveStatus((prev) => ({ ...prev, [ruleId]: undefined as unknown as 'saving' })), 2000);
    } catch {
      setSaveStatus((prev) => ({ ...prev, [ruleId]: 'error' }));
    }
  }, [edits, updateMutation]);

  const saveAll = useCallback(async () => {
    const ruleIds = Object.keys(edits);
    await Promise.allSettled(ruleIds.map((id) => saveRule(id)));
  }, [edits, saveRule]);

  const applyPreset = useCallback((preset: PresetType) => {
    if (!rules) return;
    const multiplier = getPresetMultiplier(preset);
    setEdits((prev) => {
      const updated = { ...prev };
      rules.forEach((r) => {
        const params = { ...r.parameters };
        // Scale numeric parameters
        Object.entries(params).forEach(([key, val]) => {
          if (typeof val === 'number' && key !== 'min_entries') {
            params[key] = Math.round(val * multiplier * 100) / 100;
          }
        });
        updated[r.id] = {
          ...updated[r.id],
          enabled: preset === 'aggressive' ? true : updated[r.id]?.enabled ?? r.enabled,
          parameters: params,
        };
      });
      return updated;
    });
  }, [rules]);

  const resetToDefaults = useCallback(() => {
    if (!rules) return;
    const initial: Record<string, EditableRule> = {};
    rules.forEach((r) => {
      initial[r.id] = {
        id: r.id,
        enabled: r.enabled,
        severity: r.severity,
        parameters: { ...r.parameters },
      };
    });
    setEdits(initial);
  }, [rules]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="text-sm text-slate-500">Failed to load detection rules</p>
        <p className="text-xs text-slate-400">{String(error)}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-200">Detection Rules</h1>
          <p className="text-sm text-slate-500 mt-1">Configure anomaly detection parameters and thresholds</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={resetToDefaults}>
            <RotateCcw className="h-4 w-4 mr-1" /> Reset
          </Button>
          <Button size="sm" onClick={saveAll}>
            <Save className="h-4 w-4 mr-1" /> Save All
          </Button>
        </div>
      </div>

      {/* Presets */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Quick Presets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            {(Object.entries(PRESETS) as [PresetType, typeof PRESETS[PresetType]][]).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                className="flex-1 flex items-center gap-3 p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
                  {preset.icon}
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{preset.label}</p>
                  <p className="text-xs text-slate-500">{preset.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Rules */}
      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}><CardContent className="pt-6"><Skeleton className="h-24 w-full" /></CardContent></Card>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {rules?.map((rule) => {
            const edit = edits[rule.id];
            const status = saveStatus[rule.id];
            const typeInfo = RULE_TYPE_INFO[rule.rule_type] ?? { label: rule.rule_type, color: 'bg-slate-100 text-slate-700' };

            return (
              <Card key={rule.id} className={`transition-all ${edit?.enabled === false ? 'opacity-60' : ''}`}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {/* Toggle */}
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={edit?.enabled ?? rule.enabled}
                          onChange={() => handleToggle(rule.id)}
                        />
                        <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600" />
                      </label>
                      <div>
                        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{rule.name}</h3>
                        <p className="text-xs text-slate-500 mt-0.5">{rule.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={`text-xs ${typeInfo.color}`}>{typeInfo.label}</Badge>
                      {status === 'saving' && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
                      {status === 'saved' && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                      {status === 'error' && <AlertTriangle className="h-4 w-4 text-red-500" />}
                      <Button variant="outline" size="sm" onClick={() => saveRule(rule.id)}>
                        <Save className="h-3 w-3 mr-1" /> Save
                      </Button>
                    </div>
                  </div>

                  {/* Parameters */}
                  {edit && Object.keys(edit.parameters).length > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                      {Object.entries(edit.parameters).map(([key, value]) => (
                        <div key={key}>
                          <label className="text-xs font-medium text-slate-500 block mb-1.5">
                            {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                          </label>
                          {typeof value === 'boolean' ? (
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input
                                type="checkbox"
                                className="sr-only peer"
                                checked={value}
                                onChange={(e) => handleParamChange(rule.id, key, e.target.checked)}
                              />
                              <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600" />
                            </label>
                          ) : typeof value === 'number' ? (
                            <div className="space-y-1">
                              <input
                                type="range"
                                min={0}
                                max={value > 10 ? value * 2 : 10}
                                step={value < 1 ? 0.01 : value < 10 ? 0.1 : 1}
                                value={value}
                                onChange={(e) => handleParamChange(rule.id, key, parseFloat(e.target.value))}
                                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-slate-700 accent-blue-600"
                              />
                              <Input
                                type="number"
                                value={value}
                                onChange={(e) => handleParamChange(rule.id, key, parseFloat(e.target.value) || 0)}
                                className="h-7 text-xs"
                              />
                            </div>
                          ) : (
                            <Input
                              value={String(value ?? '')}
                              onChange={(e) => handleParamChange(rule.id, key, e.target.value)}
                              className="h-7 text-xs"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
