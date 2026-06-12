/**
 * API Explorer - Interactive documentation for backend APIs.
 * Fetches live API documentation from Flask backend.
 */

import { useState, useEffect } from 'react';
import { checkHealth, optimizeSuppliers } from '../services/api';
import './ApiExplorer.css';

interface ApiEndpoint {
  method: string;
  path: string;
  description: string;
  request_body?: any;
  response?: any;
}

interface ApiDocs {
  service: string;
  version: string;
  environment: string;
  endpoints: ApiEndpoint[];
  example_requests?: any;
}

export default function ApiExplorer() {
  const [apiDocs, setApiDocs] = useState<ApiDocs | null>(null);
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch API documentation from backend
    async function fetchApiDocs() {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';
        const res = await fetch(`${API_BASE_URL}/`);
        const docs = await res.json();
        setApiDocs(docs);
      } catch (err) {
        console.error('Failed to fetch API docs:', err);
      }
    }
    fetchApiDocs();
  }, []);

  const handleTestEndpoint = async (endpoint: ApiEndpoint) => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      if (endpoint.path === '/health') {
        const result = await checkHealth();
        setResponse(result);
      } else if (endpoint.path === '/api/optimize' && apiDocs?.example_requests) {
        const exampleRequest = apiDocs.example_requests.optimize_500_ebikes;
        const result = await optimizeSuppliers(exampleRequest, false);
        setResponse(result);
      } else if (endpoint.path === '/') {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';
        const res = await fetch(`${API_BASE_URL}/`);
        const result = await res.json();
        setResponse(result);
      }
    } catch (err: any) {
      setError(err.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  if (!apiDocs) {
    return (
      <div className="api-explorer">
        <div className="api-explorer-header">
          <h2>API Explorer</h2>
          <p>Loading API documentation...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="api-explorer">
      <div className="api-explorer-header">
        <h2>API Explorer</h2>
        <p>{apiDocs.service} - v{apiDocs.version} ({apiDocs.environment})</p>
      </div>

      <div className="api-explorer-content">
        <div className="endpoints-list">
          <h3>Available Endpoints</h3>
          {apiDocs.endpoints.map((endpoint, index) => (
            <div
              key={index}
              className={`endpoint-card ${selectedEndpoint === endpoint ? 'selected' : ''}`}
              onClick={() => setSelectedEndpoint(endpoint)}
            >
              <div className="endpoint-method-path">
                <span className={`method-badge method-${endpoint.method.toLowerCase()}`}>
                  {endpoint.method}
                </span>
                <code className="endpoint-path">{endpoint.path}</code>
              </div>
              <p className="endpoint-description">{endpoint.description}</p>
            </div>
          ))}
        </div>

        <div className="endpoint-details">
          {selectedEndpoint ? (
            <>
              <div className="detail-header">
                <h3>
                  <span className={`method-badge method-${selectedEndpoint.method.toLowerCase()}`}>
                    {selectedEndpoint.method}
                  </span>
                  <code>{selectedEndpoint.path}</code>
                </h3>
                <button
                  className="test-button"
                  onClick={() => handleTestEndpoint(selectedEndpoint)}
                  disabled={loading}
                >
                  {loading ? 'Testing...' : 'Test Endpoint'}
                </button>
              </div>

              <div className="detail-section">
                <h4>Description</h4>
                <p>{selectedEndpoint.description}</p>
              </div>

              {selectedEndpoint.request_body && (
                <div className="detail-section">
                  <h4>Request Body Schema</h4>
                  <pre className="code-block">
                    {JSON.stringify(selectedEndpoint.request_body, null, 2)}
                  </pre>
                </div>
              )}

              {selectedEndpoint.response && (
                <div className="detail-section">
                  <h4>Response Schema</h4>
                  <pre className="code-block">
                    {JSON.stringify(selectedEndpoint.response, null, 2)}
                  </pre>
                </div>
              )}

              {selectedEndpoint.path === '/api/optimize' && apiDocs.example_requests && (
                <div className="detail-section">
                  <h4>Example Request</h4>
                  <pre className="code-block">
                    {JSON.stringify(apiDocs.example_requests.optimize_500_ebikes, null, 2)}
                  </pre>
                </div>
              )}

              {response && (
                <div className="detail-section">
                  <h4>Live Response</h4>
                  <pre className="code-block response-success">
                    {JSON.stringify(response, null, 2)}
                  </pre>
                </div>
              )}

              {error && (
                <div className="detail-section">
                  <h4>Error</h4>
                  <pre className="code-block response-error">{error}</pre>
                </div>
              )}
            </>
          ) : (
            <div className="no-selection">
              <p>Select an endpoint to view details and test it</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
