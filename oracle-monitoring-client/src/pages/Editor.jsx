import { useState, useRef } from 'react';
import { Play, Upload, FileCode, CheckCircle, AlertCircle, Terminal } from 'lucide-react';
import { getApiUrl } from '../utils/api';

export default function Editor() {
    const [sql, setSql] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const fileInputRef = useRef(null);

    const executeSql = async (sqlText) => {
        if (!sqlText.trim()) return;
        setLoading(true);
        setResult(null);
        try {
            const res = await fetch(`${getApiUrl()}/api/editor/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql: sqlText })
            });
            const data = await res.json();
            setResult(data);
        } catch (err) {
            setResult({ status: 'error', message: err.message });
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setLoading(true);
        setResult(null);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`${getApiUrl()}/api/editor/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            setResult(data);
            // Optionally set SQL to "File Execution" or show file content
            // For now, let's keep the textarea as is or update it?
            // The backend executes the file.
        } catch (err) {
            setResult({ status: 'error', message: err.message });
        } finally {
            setLoading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    return (
        <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-100px)] flex flex-col">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                    <Terminal className="text-primary w-6 h-6" /> SQL 에디터
                </h2>
                <div className="flex gap-3">
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleUpload}
                        accept=".sql"
                        className="hidden"
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors border border-slate-700"
                    >
                        <Upload className="w-4 h-4" /> SQL 업로드
                    </button>
                    <button
                        onClick={() => executeSql(sql)}
                        disabled={loading || !sql.trim()}
                        className={`flex items-center gap-2 px-6 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg transition-all shadow-lg shadow-primary/25 font-medium ${loading || !sql.trim() ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        <Play className="w-4 h-4" /> 실행
                    </button>
                </div>
            </div>

            {/* Editor Area */}
            <div className="relative flex-1 min-h-[300px] bg-slate-900 rounded-xl border border-slate-700/50 shadow-inner overflow-hidden flex flex-col">
                <div className="bg-slate-800/50 px-4 py-2 text-xs text-slate-400 border-b border-slate-700/50 flex justify-between">
                    <span>쿼리 입력</span>
                    <span>Ctrl+Enter로 실행</span>
                </div>
                <textarea
                    value={sql}
                    onChange={(e) => setSql(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.ctrlKey && e.key === 'Enter') {
                            executeSql(sql);
                        }
                    }}
                    placeholder="SELECT * FROM ..."
                    className="flex-1 w-full bg-transparent text-gray-200 font-mono text-sm p-4 resize-none focus:outline-none custom-scrollbar"
                    style={{ lineHeight: '1.6' }}
                    spellCheck="false"
                />
            </div>

            {/* Results Area */}
            <div className="flex-1 min-h-[300px] bg-surface rounded-xl border border-slate-700/50 shadow-lg overflow-hidden flex flex-col">
                <div className="bg-slate-800/30 px-4 py-3 border-b border-slate-700/50 flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-secondary" />
                    <span className="font-medium text-sm text-gray-300">실행 결과</span>
                </div>

                <div className="flex-1 overflow-auto custom-scrollbar p-0">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-full text-slate-500">
                            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mb-4"></div>
                            <span>쿼리 실행 중...</span>
                        </div>
                    ) : result ? (
                        result.status === 'success' ? (
                            <div className="h-full flex flex-col">
                                {result.message && (
                                    <div className="bg-emerald-500/10 text-emerald-400 px-4 py-2 text-sm border-b border-emerald-500/20 flex items-center gap-2">
                                        <CheckCircle className="w-4 h-4" /> {result.message}
                                    </div>
                                )}
                                {result.columns && result.columns.length > 0 && (
                                    <div className="flex-1 overflow-auto">
                                        <table className="w-full text-left text-sm text-gray-300 border-collapse">
                                            <thead className="bg-slate-800/80 text-xs uppercase text-slate-400 sticky top-0 backdrop-blur-sm z-10">
                                                <tr>
                                                    {result.columns.map((col, idx) => (
                                                        <th key={idx} className="px-4 py-3 font-medium border-b border-slate-700 whitespace-nowrap">{col}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-700/50">
                                                {result.rows.map((row, rIdx) => (
                                                    <tr key={rIdx} className="hover:bg-slate-800/30 transition-colors">
                                                        {row.map((cell, cIdx) => (
                                                            <td key={cIdx} className="px-4 py-2 border-b border-slate-800/50 whitespace-nowrap">{cell}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="p-6 text-danger bg-danger/5 border-l-4 border-danger">
                                <h4 className="font-bold flex items-center gap-2 mb-2"><AlertCircle className="w-5 h-5" /> 오류</h4>
                                <p className="font-mono text-sm">{result.message}</p>
                            </div>
                        )
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-slate-600">
                            <Terminal className="w-12 h-12 mb-4 opacity-20" />
                            <p>쿼리를 입력하고 실행 버튼을 눌러 결과를 확인하세요.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
