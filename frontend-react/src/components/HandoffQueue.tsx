import React, { useEffect, useState } from 'react';
import { fetchHandoffs } from '../api';

const HandoffQueue: React.FC = () => {
  const [handoffs, setHandoffs] = useState<any[]>([]);

  useEffect(() => {
    fetchHandoffs().then(setHandoffs);
  }, []);

  return (
    <div className="handoff-queue">
      <h2>Handoff Queue (r54)</h2>
      <table className="min-w-full bg-white">
        <thead>
          <tr>
            <th>Ticket ID</th>
            <th>From</th>
            <th>To</th>
            <th>Status</th>
            <th>SLA Deadline</th>
          </tr>
        </thead>
        <tbody>
          {handoffs.map((handoff) => (
            <tr key={handoff.ticket_id}>
              <td>{handoff.ticket_id}</td>
              <td>{handoff.from_dept}</td>
              <td>{handoff.to_dept}</td>
              <td>{handoff.status}</td>
              <td>{handoff.sla_deadline}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default HandoffQueue;
