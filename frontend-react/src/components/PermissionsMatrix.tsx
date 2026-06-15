import React from 'react';

const PermissionsMatrix: React.FC = () => {
  const matrix = {
    engineering: { deploy_prod: "APPROVE", access_finance: "NONE" },
    product: { edit_roadmap: "APPROVE", access_security: "NONE" }
    // Add 5 more departments (r55)
  };

  return (
    <div className="permissions-matrix">
      <h2>Permissions Matrix (r55)</h2>
      <table className="min-w-full bg-white">
        <thead>
          <tr>
            <th>Department</th>
            <th>Action</th>
            <th>Permission</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(matrix).map(([dept, actions]) => (
            Object.entries(actions).map(([action, permission]) => (
              <tr key={`${dept}-${action}`}>
                <td>{dept}</td>
                <td>{action}</td>
                <td>{permission}</td>
              </tr>
            ))
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PermissionsMatrix;
