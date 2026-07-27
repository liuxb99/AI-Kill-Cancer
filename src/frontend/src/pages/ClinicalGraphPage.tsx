import React, { useState, useEffect } from 'react';

interface Entity {
  id: string;
  kind: string;
  name: string;
  properties?: Record<string, unknown>;
}

interface Relation {
  id: string;
  kind: string;
  from_id: string;
  to_id: string;
}

interface ThreadResponse {
  patient_id: string;
  entities: Entity[];
  relations: Relation[];
  projection_status: string;
  message?: string;
}

const ClinicalGraphPage: React.FC = () => {
  const [patientId, setPatientId] = useState('');
  const [data, setData] = useState<ThreadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Read patientId from URL query params on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const pid = params.get('patientId');
    if (pid) {
      setPatientId(pid);
    }
  }, []);

  // Auto-search when patientId is provided via URL
  useEffect(() => {
    if (patientId.trim()) {
      handleSearch();
    }
  }, [patientId]);

  const handleSearch = async () => {
    if (!patientId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/clinical-graph/patient/${encodeURIComponent(patientId)}/thread`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        if (res.status === 404) {
          setData(null);
          setError('Patient graph data not found or projection pending');
        } else {
          throw new Error(`HTTP ${res.status}`);
        }
      } else {
        const json: ThreadResponse = await res.json();
        setData(json);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch graph data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Clinical Knowledge Graph</h1>
      <div style={{ marginBottom: '16px' }}>
        <input
          type="text"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          placeholder="Enter Patient ID"
          style={{ padding: '8px', width: '300px', marginRight: '8px' }}
        />
        <button onClick={handleSearch} disabled={loading} style={{ padding: '8px 16px' }}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'red', marginBottom: '16px' }}>{error}</div>
      )}

      {data && (
        <div>
          <h2>Patient Thread: {data.patient_id}</h2>
          <p>Projection Status: {data.projection_status}</p>
          {data.message && <p style={{ color: 'orange' }}>{data.message}</p>}
          
          <h3>Entities ({data.entities.length})</h3>
          <ul>
            {data.entities.map((e) => (
              <li key={e.id}>
                <strong>{e.kind}</strong>: {e.name} ({e.id})
              </li>
            ))}
          </ul>

          <h3>Relations ({data.relations.length})</h3>
          <ul>
            {data.relations.map((r) => (
              <li key={r.id}>
                <strong>{r.kind}</strong>: {r.from_id} → {r.to_id}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ClinicalGraphPage;
