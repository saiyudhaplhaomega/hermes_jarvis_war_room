import React, { useEffect, useState } from 'react';
import { fetchKPIs } from '../api';

const KPIDashboard: React.FC = () => {
  const [kpis, setKpis] = useState<Record<string, number>>({});

  useEffect(() => {
    fetchKPIs().then(setKpis);
  }, []);

  return (
    <div className="kpi-dashboard">
      <h2>Company KPIs (r53)</h2>
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(kpis).map(([kpi, value]) => (
          <div key={kpi} className="bg-gray-100 p-4 rounded">
            <h3 className="font-bold">{kpi.replace('_', ' ')}</h3>
            <p>{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default KPIDashboard;
