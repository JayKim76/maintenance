import { useState, useRef, useEffect } from 'react';
import { Activity, Loader, AlertTriangle, CheckCircle2, Database, HardDrive, Cpu, Lock, Thermometer, Layers, Server, BarChart3, RefreshCw, FileWarning, Radio, StopCircle, Clock, Download, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { getApiUrl } from '../utils/api';
import { useConnection } from '../context/ConnectionContext';
import * as XLSX from 'xlsx';

const SECTION_ICONS = {
    instance: <Server className="w-5 h-5" />,
    capacity: <Cpu className="w-5 h-5" />,
    waits: <Activity className="w-5 h-5" />,
    topsql: <BarChart3 className="w-5 h-5" />,
    locks: <Lock className="w-5 h-5" />,
    tablespace: <Database className="w-5 h-5" />,
    temp: <Thermometer className="w-5 h-5" />,
    datafiles: <HardDrive className="w-5 h-5" />,
    hotfiles: <Layers className="w-5 h-5" />,
    asm: <HardDrive className="w-5 h-5" />,
    alertlog: <FileWarning className="w-5 h-5" />,
    listener: <Radio className="w-5 h-5" />,
};

function DataTable({ data }) {
    if (!data || data.error) {
        const isTimeout = data?.error?.includes('timed out');
        const isCancelled = data?.error?.includes('Cancelled');
        return (
            <div className={`text-sm italic py-2 flex items-center gap-2 ${isTimeout ? 'text-yellow-500' : isCancelled ? 'text-slate-500' : 'text-slate-500'}`}>
                {isTimeout && <Clock className="w-4 h-4" />}
                {data?.error || 'No data'}
            </div>
        );
    }
    if (!data.rows || data.rows.length === 0) {
        return <div className="text-sm text-slate-500 italic py-2">No rows returned</div>;
    }

    return (
        <div className="overflow-x-auto rounded-lg border border-slate-700/50">
            <table className="w-full text-sm">
                <thead>
                    <tr className="bg-slate-800/80">
                        {data.columns.map((col, i) => (
                            <th key={i} className="px-3 py-2 text-left text-xs font-semibold text-slate-300 whitespace-nowrap border-b border-slate-700/50">
                                {col}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.rows.map((row, ri) => {
                        const maxUsedPctIdx = data.columns.findIndex(c => c.toUpperCase() === 'MAX_USED_PCT');
                        const maxUsedPctVal = maxUsedPctIdx >= 0 ? row[maxUsedPctIdx] : null;

                        return (
                            <tr key={ri} className={`border-b border-slate-700/30 ${ri % 2 === 0 ? 'bg-slate-900/30' : 'bg-slate-800/20'} hover:bg-slate-700/30 transition-colors`}>
                                {row.map((cell, ci) => {
                                    const col = data.columns[ci]?.toUpperCase() || '';
                                    const isNumeric = typeof cell === 'number';
                                    const isUsedPct = col.includes('USED_PCT') || col.includes('PCT');
                                    let cellClass = 'px-3 py-1.5 text-slate-300 whitespace-nowrap';
                                    if (isNumeric) cellClass += ' text-right font-mono';

                                    let badge = null;
                                    if (isUsedPct && typeof cell === 'number') {
                                        if (col === 'MAX_USED_PCT') {
                                            if (cell >= 95) badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 font-bold">CRITICAL</span>;
                                            else if (cell >= 85) badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-yellow-500/20 text-yellow-400 font-bold">WARNING</span>;
                                            else badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-emerald-500/20 text-emerald-400 font-bold">AUTO-EXTEND OK</span>;
                                        } else if (col === 'USED_PCT') {
                                            if (maxUsedPctVal !== null && typeof maxUsedPctVal === 'number' && maxUsedPctVal < 85) {
                                                badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-blue-500/20 text-blue-400 font-bold">AUTO-EXTEND</span>;
                                            } else {
                                                if (cell >= 90) badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 font-bold">CRITICAL</span>;
                                                else if (cell >= 80) badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-yellow-500/20 text-yellow-400 font-bold">WARNING</span>;
                                            }
                                        } else {
                                            if (cell >= 90) badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 font-bold">CRITICAL</span>;
                                            else if (cell >= 80) badge = <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-yellow-500/20 text-yellow-400 font-bold">WARNING</span>;
                                        }
                                    }

                                    return (
                                        <td key={ci} className={cellClass}>
                                            {cell === null ? <span className="text-slate-600">NULL</span> : String(cell)}
                                            {badge}
                                        </td>
                                    );
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

function Section({ section, index }) {
    const icon = SECTION_ICONS[section.id] || <Activity className="w-5 h-5" />;
    const hasError = section.data?.some(d => d?.error);
    const hasTimeout = section.data?.some(d => d?.error?.includes('timed out'));
    const hasCancelled = section.data?.some(d => d?.error?.includes('Cancelled'));

    return (
        <div className="bg-surface rounded-xl border border-slate-700/50 shadow-lg overflow-hidden">
            <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-700/50 bg-gradient-to-r from-slate-800/50 to-transparent">
                <div className={`p-2 rounded-lg ${hasCancelled ? 'bg-slate-700/50 text-slate-400' : hasTimeout ? 'bg-yellow-500/10 text-yellow-500' : hasError ? 'bg-danger/10 text-danger' : 'bg-primary/10 text-primary'}`}>
                    {icon}
                </div>
                <div className="flex-1">
                    <span className="text-xs text-slate-500 font-mono">#{index + 1}</span>
                    <h3 className="text-base font-semibold text-gray-200">{section.title}</h3>
                </div>
                {hasTimeout && <span className="text-[10px] px-2 py-0.5 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 rounded-full">TIMEOUT</span>}
                {hasCancelled && <span className="text-[10px] px-2 py-0.5 bg-slate-700 text-slate-400 border border-slate-600 rounded-full">CANCELLED</span>}
            </div>
            <div className="p-4 space-y-4">
                {section.data.map((table, ti) => (
                    <DataTable key={ti} data={table} />
                ))}
            </div>
        </div>
    );
}

function SummaryTable({ lines }) {
    if (!lines || lines.length === 0) return null;

    const parsedRows = lines
        .map(l => l.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim()))
        .filter(row => !row.every(c => /^[:\- ]+$/.test(c)));

    if (parsedRows.length === 0) return null;
    const [headers, ...dataRows] = parsedRows;

    return (
        <div className="my-3 overflow-x-auto rounded-lg border border-slate-700/60 shadow-md bg-slate-900/60">
            <table className="w-full text-xs text-left">
                <thead className="bg-slate-800/90 text-slate-200 border-b border-slate-700/60 font-semibold">
                    <tr>
                        {headers.map((h, i) => (
                            <th key={i} className="px-3 py-2 whitespace-nowrap">
                                {h}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40 font-mono">
                    {dataRows.map((row, ri) => (
                        <tr key={ri} className={`hover:bg-slate-700/30 transition-colors ${ri % 2 === 0 ? 'bg-slate-900/40' : 'bg-slate-800/20'}`}>
                            {row.map((cell, ci) => {
                                const isDanger = cell.includes('위험') || cell.includes('🔴');
                                const isWarn = cell.includes('주의') || cell.includes('🟡');
                                const isGood = cell.includes('여유') || cell.includes('정상') || cell.includes('양호') || cell.includes('🟢');
                                const isPct = cell.includes('%');
                                const isMb = cell.includes('MB');

                                let cellClass = 'px-3 py-2 whitespace-nowrap text-slate-300';
                                if (isDanger) cellClass += ' text-red-400 font-bold';
                                else if (isWarn) cellClass += ' text-yellow-400 font-bold';
                                else if (isGood) cellClass += ' text-emerald-400 font-medium';

                                if ((isPct || isMb) && !isDanger && !isWarn && !isGood) {
                                    cellClass += ' text-right';
                                }

                                return (
                                    <td key={ci} className={cellClass}>
                                        {cell}
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function SummaryView({ content }) {
    if (!content) return null;

    const lines = content.split('\n');
    const elements = [];
    let currentTableLines = [];
    let currentTextLines = [];

    const flushText = () => {
        if (currentTextLines.length > 0) {
            elements.push({
                type: 'text',
                content: currentTextLines.join('\n')
            });
            currentTextLines = [];
        }
    };

    const flushTable = () => {
        if (currentTableLines.length > 0) {
            elements.push({
                type: 'table',
                lines: [...currentTableLines]
            });
            currentTableLines = [];
        }
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        const isTable = trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|');

        if (isTable) {
            flushText();
            currentTableLines.push(trimmed);
        } else {
            flushTable();
            currentTextLines.push(line);
        }
    }
    flushTable();
    flushText();

    return (
        <div className="space-y-3 font-sans text-slate-300">
            {elements.map((el, idx) => {
                if (el.type === 'text') {
                    return (
                        <div key={idx} className="whitespace-pre-wrap leading-relaxed text-sm">
                            {el.content}
                        </div>
                    );
                } else if (el.type === 'table') {
                    return <SummaryTable key={idx} lines={el.lines} />;
                }
                return null;
            })}
        </div>
    );
}

export default function HealthCheck() {
    const { connected } = useConnection();
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [elapsed, setElapsed] = useState(0);
    const [summary, setSummary] = useState('');
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);
    const abortRef = useRef(null);
    const timerRef = useRef(null);

    useEffect(() => {
        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, []);

    const runCheck = async () => {
        setLoading(true);
        setError('');
        setReport(null);
        setSummary('');
        setElapsed(0);
        setIsSummaryExpanded(true);
        const startTime = Date.now();
        timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000);
        abortRef.current = new AbortController();

        try {
            const res = await fetch(`${getApiUrl()}/api/healthcheck/run`, { signal: abortRef.current.signal });
            const data = await res.json();
            if (data.status === 'error') {
                setError(data.message);
            } else {
                setReport(data);
                // Fetch summary in background
                fetchSummary(data);
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                setError('점검이 중단되었습니다.');
            } else {
                setError('Network Error: Could not reach backend server.');
            }
        } finally {
            setLoading(false);
            if (timerRef.current) clearInterval(timerRef.current);
        }
    };

    const fetchSummary = async (reportData) => {
        setSummaryLoading(true);
        try {
            const res = await fetch(`${getApiUrl()}/api/healthcheck/summary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ report: reportData })
            });
            const data = await res.json();
            if (data.status === 'success') {
                setSummary(data.summary);
            }
        } catch (err) {
            console.error('Failed to fetch summary:', err);
        } finally {
            setSummaryLoading(false);
        }
    };

    const cancelCheck = async () => {
        try { await fetch(`${getApiUrl()}/api/healthcheck/cancel`, { method: 'POST' }); } catch { }
        if (abortRef.current) abortRef.current.abort();
    };

    const getReportSid = (rpt) => {
        if (rpt?.sid) return String(rpt.sid).trim();

        const instSec = rpt?.sections?.find(s => s.id === 'instance');
        if (instSec?.data) {
            for (const tbl of instSec.data) {
                if (tbl?.columns && tbl?.rows?.length > 0) {
                    const idx = tbl.columns.findIndex(c => c.toUpperCase() === 'INSTANCE_NAME');
                    if (idx >= 0 && tbl.rows[0][idx]) {
                        return String(tbl.rows[0][idx]).trim();
                    }
                }
            }
        }

        const dsn = rpt?.dsn || '';
        const sidMatch = dsn.match(/\(\s*SID\s*=\s*([^)\s]+)\s*\)/i);
        if (sidMatch) return sidMatch[1].toUpperCase();
        const svcMatch = dsn.match(/\(\s*SERVICE_NAME\s*=\s*([^)\s]+)\s*\)/i);
        if (svcMatch) return svcMatch[1].split('.')[0].toUpperCase();
        if (dsn.includes('/')) return dsn.split('/')[1].split('.')[0].toUpperCase();
        const parts = dsn.split(':');
        if (parts.length >= 3) return parts[2].toUpperCase();
        return '';
    };

    const getFileName = (rpt, ext) => {
        const dsn = (rpt.dsn || 'unknown').replace(/[^a-zA-Z0-9_.-]/g, '_');
        const ts = rpt.timestamp.replace(/[: ]/g, '_');
        return `HealthCheck_${dsn}_${ts}.${ext}`;
    };

    const exportToExcel = (rpt) => {
        const wb = XLSX.utils.book_new();
        const allRows = [];

        // === Report Header ===
        allRows.push(['ORACLE DATABASE HEALTH CHECK REPORT']);
        allRows.push([]);
        allRows.push(['접속 정보', `${rpt.user}@${rpt.dsn}`, '', '점검 시각', rpt.timestamp]);
        allRows.push(['상태', rpt.status === 'cancelled' ? '중단됨' : '완료', '', '섹션 수', rpt.sections.length]);
        allRows.push([]);

        // === Each Section ===
        rpt.sections.forEach((sec, idx) => {
            // Section header row
            allRows.push([`■ ${idx + 1}. ${sec.title}`]);

            sec.data.forEach((table, ti) => {
                if (table.error) {
                    allRows.push(['  ⚠ ' + table.error]);
                    return;
                }
                if (!table.columns || table.columns.length === 0 || !table.rows || table.rows.length === 0) {
                    allRows.push(['  (데이터 없음)']);
                    return;
                }

                // Column headers
                allRows.push(table.columns);
                // Data
                table.rows.forEach(row => {
                    allRows.push(row.map(cell => cell === null ? '' : cell));
                });

                if (ti < sec.data.length - 1) allRows.push([]); // gap between sub-tables
            });

            allRows.push([]); // gap after section
        });

        const ws = XLSX.utils.aoa_to_sheet(allRows);

        // Auto-fit columns
        const maxCols = Math.max(...allRows.map(r => r.length), 1);
        ws['!cols'] = Array.from({ length: maxCols }, (_, ci) => {
            const maxLen = allRows.reduce((max, row) => {
                const val = row[ci] != null ? String(row[ci]) : '';
                return Math.max(max, val.length);
            }, 5);
            return { wch: Math.min(maxLen + 2, 50) };
        });

        // Merge title row across columns
        ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: Math.min(maxCols - 1, 7) } }];

        XLSX.utils.book_append_sheet(wb, ws, 'Health Check Report');
        XLSX.writeFile(wb, getFileName(rpt, 'xlsx'));
    };

    const formatSummaryForPdf = (rawSummary) => {
        if (!rawSummary) return '';
        const lines = rawSummary.split('\n');
        let htmlResult = '';
        let tableBuffer = [];

        const flushTableBuffer = () => {
            if (tableBuffer.length === 0) return;
            const parsed = tableBuffer
                .map(l => l.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim()))
                .filter(row => !row.every(c => /^[:\- ]+$/.test(c)));

            if (parsed.length > 0) {
                const [hdr, ...dataRows] = parsed;
                htmlResult += '<table class="summary-table"><thead><tr>';
                hdr.forEach(c => { htmlResult += `<th>${c}</th>`; });
                htmlResult += '</tr></thead><tbody>';
                dataRows.forEach(r => {
                    htmlResult += '<tr>';
                    r.forEach(c => {
                        let style = '';
                        if (c.includes('위험') || c.includes('🔴')) style = 'color:#dc2626;font-weight:bold;';
                        else if (c.includes('주의') || c.includes('🟡')) style = 'color:#d97706;font-weight:bold;';
                        else if (c.includes('여유') || c.includes('정상') || c.includes('양호') || c.includes('🟢')) style = 'color:#16a34a;font-weight:bold;';
                        else if (c.includes('%') || c.includes('MB')) style = 'text-align:right;font-family:monospace;';
                        htmlResult += `<td style="${style}">${c}</td>`;
                    });
                    htmlResult += '</tr>';
                });
                htmlResult += '</tbody></table>';
            }
            tableBuffer = [];
        };

        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
                tableBuffer.push(trimmed);
            } else {
                flushTableBuffer();
                if (line) {
                    htmlResult += `<div>${line}</div>`;
                } else {
                    htmlResult += '<div style="height:6px;"></div>';
                }
            }
        }
        flushTableBuffer();
        return htmlResult;
    };

    const exportToPdf = (rpt) => {
        const summaryHtml = summary ? `
            <div class="summary-section">
                <div class="section-title">✨ AI 종합 분석 결과</div>
                <div class="summary-content">${formatSummaryForPdf(summary)}</div>
            </div>` : '';

        const sectionHtml = rpt.sections.map((sec, idx) => {
            const tablesHtml = sec.data.map(table => {
                if (table.error) return `<p style="color:#b45309;font-style:italic;">⚠ ${table.error}</p>`;
                if (!table.columns?.length || !table.rows?.length) return '<p style="color:#888;">데이터 없음</p>';
                const ths = table.columns.map(c => `<th>${c}</th>`).join('');
                const trs = table.rows.map(row =>
                    '<tr>' + row.map(cell => {
                        const v = cell === null ? '' : String(cell);
                        const isNum = typeof cell === 'number';
                        return `<td style="${isNum ? 'text-align:right;font-family:monospace;' : ''}">${v}</td>`;
                    }).join('') + '</tr>'
                ).join('');
                return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
            }).join('');

            return `
                <div class="section">
                    <div class="section-title">${idx + 1}. ${sec.title}</div>
                    ${tablesHtml}
                </div>`;
        }).join('');

        const sid = getReportSid(rpt).replace(/[\\/:*?"<>|]/g, '_');
        const dateOnly = (rpt.timestamp || '').split(' ')[0] || new Date().toISOString().slice(0, 10);
        const pdfTitle = sid
            ? `Oracle ${sid} DB Health Check - ${dateOnly}`
            : `Oracle DB Health Check - ${dateOnly}`;

        const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>${pdfTitle}</title>
<style>
  @page { size: A4 landscape; margin: 12mm; }
  * { box-sizing: border-box; }
  body { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; font-size: 10px; color: #1e293b; margin: 0; padding: 0; }
  .header { background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); color: white; padding: 20px 28px; margin-bottom: 16px; border-radius: 4px; }
  .header h1 { margin: 0 0 8px 0; font-size: 18px; font-weight: 700; letter-spacing: 0.5px; }
  .header-info { display: flex; gap: 32px; font-size: 11px; opacity: 0.9; }
  .header-info span { background: rgba(255,255,255,0.15); padding: 3px 10px; border-radius: 3px; }
  .section { page-break-inside: avoid; margin-bottom: 14px; border: 1px solid #e2e8f0; border-radius: 4px; overflow: hidden; }
  .section-title { background: #f1f5f9; padding: 8px 14px; font-size: 12px; font-weight: 700; color: #0f172a; border-bottom: 2px solid #3b82f6; }
  .summary-section { margin-bottom: 16px; border: 1px solid #3b82f6; border-radius: 4px; overflow: hidden; background: #f8fafc; }
  .summary-content { padding: 12px 14px; font-size: 10px; line-height: 1.6; color: #334155; }
  .summary-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9px; }
  .summary-table th { background: #e2e8f0; padding: 5px 8px; text-align: left; font-weight: 700; color: #1e293b; border: 1px solid #cbd5e1; white-space: nowrap; }
  .summary-table td { padding: 4px 8px; border: 1px solid #e2e8f0; white-space: nowrap; font-size: 9px; }
  .summary-table tr:nth-child(even) { background: #f1f5f9; }
  table { width: 100%; border-collapse: collapse; font-size: 9px; }
  th { background: #f8fafc; padding: 5px 8px; text-align: left; font-weight: 600; color: #475569; border-bottom: 1px solid #cbd5e1; white-space: nowrap; }
  td { padding: 4px 8px; border-bottom: 1px solid #f1f5f9; white-space: nowrap; }
  tr:nth-child(even) { background: #fafbfc; }
  tr:hover { background: #f0f4ff; }
  .footer { text-align: center; font-size: 9px; color: #94a3b8; margin-top: 16px; padding: 8px; border-top: 1px solid #e2e8f0; }
</style>
</head><body>
  <div class="header">
    <h1>Oracle Database Health Check Report</h1>
    <div class="header-info">
      <span>🔌 ${rpt.user}@${rpt.dsn}</span>
      <span>📅 ${rpt.timestamp}</span>
      <span>📋 ${rpt.sections.length} sections</span>
      <span>${rpt.status === 'cancelled' ? '⚠ 중단됨' : '✅ 완료'}</span>
    </div>
  </div>
  ${summaryHtml}
  ${sectionHtml}
  <div class="footer">Generated by Oracle Monitoring Tool — ${rpt.timestamp}</div>
</body></html>`;

        const printWin = window.open('', '_blank', 'width=1200,height=800');
        printWin.document.write(html);
        printWin.document.close();
        printWin.document.title = pdfTitle;
        setTimeout(() => { printWin.print(); }, 500);
    };

    return (
        <div className="space-y-6 max-w-6xl mx-auto pb-10">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                    <Activity className="text-accent w-6 h-6" /> DB 점검 리포트
                </h2>
                <div className="flex items-center gap-3">
                    {loading && (
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                            <Clock className="w-4 h-4" />
                            <span className="font-mono">{elapsed}s</span>
                        </div>
                    )}
                    {report && !loading && (
                        <>
                            <button
                                onClick={() => exportToPdf(report)}
                                className="flex items-center gap-2 px-4 py-2.5 bg-accent/20 hover:bg-accent/30 text-accent font-semibold rounded-lg transition-colors border border-accent/30"
                            >
                                <FileText className="w-4 h-4" /> PDF 저장
                            </button>
                            <button
                                onClick={() => exportToExcel(report)}
                                className="flex items-center gap-2 px-4 py-2.5 bg-secondary/20 hover:bg-secondary/30 text-secondary font-semibold rounded-lg transition-colors border border-secondary/30"
                            >
                                <Download className="w-4 h-4" /> Excel 저장
                            </button>
                        </>
                    )}
                    {loading ? (
                        <button
                            onClick={cancelCheck}
                            className="flex items-center gap-2 px-5 py-2.5 bg-danger hover:bg-danger/90 text-white font-bold rounded-lg transition-colors shadow-lg shadow-danger/25"
                        >
                            <StopCircle className="w-4 h-4" /> 중단
                        </button>
                    ) : (
                        <button
                            onClick={runCheck}
                            disabled={!connected}
                            className="flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 text-background font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary/25"
                        >
                            <RefreshCw className="w-4 h-4" /> 점검 실행
                        </button>
                    )}
                </div>
            </div>

            {loading && (
                <div className="bg-surface rounded-xl border border-slate-700/50 p-6 flex items-center gap-4 shadow-lg">
                    <Loader className="w-6 h-6 text-primary animate-spin" />
                    <div>
                        <div className="text-sm font-semibold text-gray-200">점검 진행 중...</div>
                        <div className="text-xs text-slate-400">12개 섹션을 순차적으로 수집합니다. 각 쿼리는 5초 타임아웃이 적용됩니다.</div>
                    </div>
                </div>
            )}

            {!connected && (
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center">
                    <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-3" />
                    <p className="text-slate-300 text-lg font-medium">데이터베이스에 연결되지 않았습니다</p>
                    <p className="text-slate-500 text-sm mt-1">Connections 페이지에서 먼저 접속하세요.</p>
                </div>
            )}

            {error && (
                <div className="bg-danger/10 border border-danger/20 rounded-xl p-4 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-danger mt-0.5 shrink-0" />
                    <span className="text-danger text-sm">{error}</span>
                </div>
            )}

            {report && (
                <>
                    <div className="bg-surface rounded-xl border border-slate-700/50 p-4 flex items-center justify-between shadow-lg">
                        <div className="flex items-center gap-3">
                            <CheckCircle2 className={`w-6 h-6 ${report.status === 'cancelled' ? 'text-yellow-500' : 'text-secondary'}`} />
                            <div>
                                <div className="text-sm font-semibold text-gray-200">
                                    {report.status === 'cancelled' ? '점검 중단됨 (일부 결과)' : '점검 완료'}
                                </div>
                                <div className="text-xs text-slate-400">
                                    {report.user}@{report.dsn} — {report.timestamp} — {elapsed}초 소요
                                </div>
                            </div>
                        </div>
                        <div className="text-xs text-slate-500">
                            {report.sections.length} sections
                        </div>
                    </div>

                    {/* Summary Panel */}
                    <div className="bg-slate-800/40 rounded-xl border border-slate-600/50 shadow-lg overflow-hidden">
                        <div
                            className="px-5 py-3 border-b border-slate-700/50 flex items-center justify-between cursor-pointer hover:bg-slate-700/30 transition-colors"
                            onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
                        >
                            <div className="flex items-center gap-2">
                                <Activity className="w-5 h-5 text-accent" />
                                <h3 className="text-base font-bold text-gray-200">AI 종합 분석 결과</h3>
                            </div>
                            <button className="text-slate-400 hover:text-slate-200">
                                {isSummaryExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                            </button>
                        </div>

                        {isSummaryExpanded && (
                            <div className="p-5 font-mono text-sm leading-relaxed overflow-x-auto">
                                {summaryLoading ? (
                                    <div className="flex items-center gap-3 text-slate-400 py-4 justify-center">
                                        <Loader className="w-5 h-5 animate-spin text-accent" />
                                        <span>분석 중...</span>
                                    </div>
                                ) : summary ? (
                                    <SummaryView content={summary} />
                                ) : (
                                    <div className="text-slate-500 italic">분석 결과가 없습니다.</div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {report.sections.map((sec, i) => (
                            <a key={i} href={`#hc-${sec.id}`} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-700/50 transition-colors">
                                #{i + 1} {sec.title}
                            </a>
                        ))}
                    </div>

                    <div className="space-y-4">
                        {report.sections.map((sec, i) => (
                            <div key={i} id={`hc-${sec.id}`}>
                                <Section section={sec} index={i} />
                            </div>
                        ))}
                    </div>
                </>
            )}

            {!report && !error && connected && !loading && (
                <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-12 text-center">
                    <Activity className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400 text-lg">위의 <strong className="text-primary">"점검 실행"</strong> 버튼을 눌러 점검을 시작하세요</p>
                    <p className="text-slate-500 text-sm mt-2">Instance, Capacity, Wait Events, Top SQL, Locks, Tablespace, Temp, Datafile, Hot Files, ASM, Alert Log, Listener 정보를 수집합니다.</p>
                </div>
            )}
        </div>
    );
}
