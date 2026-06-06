import React from 'react';
import Plot from 'react-plotly.js';

interface ChartPanelProps {
  chartJson: string; // JSON string from backend
}

const ChartPanel: React.FC<ChartPanelProps> = ({ chartJson }) => {
  // If no chart data — show placeholder
  if (!chartJson) {
    return (
      <div className="flex items-center justify-center h-48 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-400 text-sm">No chart for this question</p>
      </div>
    );
  }

  // Try to parse the chart JSON from the backend
  try {
    const figure = JSON.parse(chartJson);
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <Plot
          data={figure.data}
          layout={{
            ...figure.layout,
            autosize: true,
            margin: { t: 40, r: 20, b: 40, l: 50 },
            font: { family: 'Arial, sans-serif', size: 12 },
          }}
          style={{ width: '100%', height: '350px' }}
          useResizeHandler={true}
          config={{ responsive: true, displayModeBar: false }}
        />
      </div>
    );
  } catch (e) {
    // If JSON parsing fails — show error
    return (
      <div className="flex items-center justify-center h-48 bg-red-50 rounded-lg border border-red-200">
        <p className="text-red-400 text-sm">Could not render chart</p>
      </div>
    );
  }
};

export default ChartPanel;