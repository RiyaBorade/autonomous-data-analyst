import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

// Upload a CSV file — returns real table name and row count from PostgreSQL
export async function uploadCSV(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_BASE}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

// Fetch real datasets from PostgreSQL — replaces the hardcoded list
export async function getDatasets() {
  const response = await axios.get(`${API_BASE}/datasets`);
  return response.data.datasets;
}

// Send question to LangGraph agents — returns sql, insight, stats, chart
export async function investigate(question: string, datasetName: string) {
  const response = await axios.post(`${API_BASE}/investigate`, {
    question,
    dataset_name: datasetName
  });
  return response.data;
}