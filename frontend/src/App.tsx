import React, { useCallback, useEffect, useState } from 'react';
import { getDatasets, investigate, uploadCSV } from './api';
import ChartPanel from './components/ChartPanel';

interface Dataset {
  table_name: string;
  row_count: number;
}

interface InvestigateResult {
  sql: string;
  insight: string;
  stats: string;
  chart_json: string;
}

function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [result, setResult] = useState<InvestigateResult | null>(null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [sqlOpen, setSqlOpen] = useState(true);

  const loadDatasets = useCallback(async () => {
    try {
      const data = await getDatasets();
      setDatasets(data);
      setSelectedDataset((current) => {
        if (!current) return current;
        return data.find((d: Dataset) => d.table_name === current.table_name) ?? null;
      });
    } catch (err) {
      console.error('Failed to load datasets:', err);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Please upload a .csv file.');
      return;
    }
    setUploading(true);
    try {
      await uploadCSV(file);
      await loadDatasets();
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed. Check the console for details.');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) await handleFileUpload(file);
  };

  const handleSend = async () => {
    if (!selectedDataset) {
      alert('Please select a dataset first');
      return;
    }
    if (!question.trim()) return;

    setLoading(true);
    setResult(null);
    try {
      const data = await investigate(question.trim(), selectedDataset.table_name);
      setResult({
        sql: data.sql || '',
        insight: data.insight || '',
        stats: data.stats || '',
        chart_json: data.chart_json || '',
      });
    } catch (err: unknown) {
      console.error('Investigation failed:', err);
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
      const detail = axiosErr.response?.data?.detail;
      if (axiosErr.response?.status === 429) {
        alert(detail || 'Gemini API rate limit reached. Wait a minute and try again.');
      } else {
        alert(detail || 'Investigation failed. Check the console for details.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !loading) handleSend();
  };

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      {/* Left sidebar */}
      <aside
        className="w-[280px] shrink-0 flex flex-col border-r border-gray-200"
        style={{ backgroundColor: '#F8FAFC' }}
      >
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-lg font-semibold text-gray-900">Data Analyst AI</h1>
        </div>

        {/* Drag-and-drop upload */}
        <div className="p-4">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
              dragActive
                ? 'border-[#1A56DB] bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onClick={() => document.getElementById('csv-input')?.click()}
          >
            <input
              id="csv-input"
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
                e.target.value = '';
              }}
            />
            {uploading ? (
              <p className="text-sm text-gray-500">Uploading…</p>
            ) : (
              <>
                <p className="text-sm font-medium text-gray-700">Drop CSV here</p>
                <p className="text-xs text-gray-500 mt-1">or click to browse</p>
              </>
            )}
          </div>
        </div>

        {/* Dataset list */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Datasets
          </p>
          {datasets.length === 0 ? (
            <p className="text-sm text-gray-400">No datasets yet. Upload a CSV.</p>
          ) : (
            <div className="space-y-2">
              {datasets.map((dataset) => {
                const isSelected = selectedDataset?.table_name === dataset.table_name;
                return (
                  <button
                    key={dataset.table_name}
                    type="button"
                    onClick={() => {
                      setSelectedDataset(dataset);
                      setResult(null);
                    }}
                    className={`w-full text-left rounded-lg p-3 transition-colors ${
                      isSelected
                        ? 'text-white'
                        : 'bg-white border border-gray-200 hover:border-gray-300 text-gray-900'
                    }`}
                    style={isSelected ? { backgroundColor: '#1A56DB' } : undefined}
                  >
                    <p className="text-sm font-medium truncate">{dataset.table_name}</p>
                    <p
                      className={`text-xs mt-0.5 ${
                        isSelected ? 'text-blue-100' : 'text-gray-500'
                      }`}
                    >
                      {dataset.row_count.toLocaleString()} rows
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto p-6 pb-24">
          {!selectedDataset && !result && !loading && (
            <div className="h-full flex items-center justify-center">
              <p className="text-gray-400 text-lg">Select a dataset and ask a question</p>
            </div>
          )}

          {loading && (
            <div className="h-full flex items-center justify-center">
              <div className="flex items-center gap-3 text-gray-500">
                <span className="inline-block w-5 h-5 border-2 border-gray-300 border-t-[#1A56DB] rounded-full animate-spin" />
                <span>Analyzing…</span>
              </div>
            </div>
          )}

          {result && !loading && (
            <div className="max-w-4xl mx-auto space-y-4">
              {/* 1. SQL panel */}
              <div className="rounded-lg overflow-hidden bg-gray-900 text-gray-100">
                <button
                  type="button"
                  onClick={() => setSqlOpen((o) => !o)}
                  className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-gray-800 transition-colors"
                >
                  <span>Generated SQL</span>
                  <span className="text-gray-400">{sqlOpen ? '▼' : '▶'}</span>
                </button>
                {sqlOpen && (
                  <pre className="px-4 pb-4 text-sm font-mono whitespace-pre-wrap break-words text-green-300 overflow-x-auto">
                    {result.sql || 'No SQL generated.'}
                  </pre>
                )}
              </div>

              {/* 2. Insight card */}
              <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Insight
                </h2>
                <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                  {result.insight || 'No insight available.'}
                </p>
              </div>

              {/* 3. Stats card */}
              <div className="bg-gray-100 border border-gray-200 rounded-lg p-5">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Statistics
                </h2>
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                  {result.stats || 'No statistics available.'}
                </pre>
              </div>

              {/* 4. Chart */}
              <ChartPanel chartJson={result.chart_json} />
            </div>
          )}
        </div>

        {/* Fixed bottom input bar */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          <div className="max-w-4xl mx-auto flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your data…"
              disabled={loading}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A56DB] focus:border-transparent disabled:bg-gray-50"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={loading}
              className="px-5 py-2.5 rounded-lg text-white text-sm font-medium disabled:opacity-60 flex items-center gap-2 min-w-[88px] justify-center"
              style={{ backgroundColor: '#1A56DB' }}
            >
              {loading ? (
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Send'
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
