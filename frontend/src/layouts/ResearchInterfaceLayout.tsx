import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const ResearchInterfaceLayout: React.FC = () => {
  const getNavLinkClass = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? 'bg-indigo-700 text-white px-3 py-2 rounded-md text-sm font-medium'
      : 'text-indigo-100 hover:bg-indigo-500 hover:text-white px-3 py-2 rounded-md text-sm font-medium';

  return (
    <div className="research-interface-layout min-h-screen flex flex-col">
      <nav className="bg-indigo-600 shadow-md">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <span className="font-semibold text-xl text-white mr-6">Research Exploration</span>
              <div className="flex space-x-4">
                <NavLink to="report" className={getNavLinkClass}>
                  Directions Report
                </NavLink>
                <NavLink to="assessments" className={getNavLinkClass}>
                  Assessments
                </NavLink>
                <NavLink to="export" className={getNavLinkClass}>
                  Export
                </NavLink>
              </div>
            </div>
            {/* Future elements like UserProfile can go here */}
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <main className="flex-grow container mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
};

export default ResearchInterfaceLayout; 