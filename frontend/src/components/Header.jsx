import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import './Header.css'; // We'll create this CSS file next

function Header() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className={`app-header ${theme}`}>
      <div className="logo">
        <Link to="/">ResearchAIde</Link>
      </div>
      <nav>
        <ul>
          <li>
            <Link to="/">Home</Link>
          </li>
          <li>
            <Link to="/exploration/report">Explore Research</Link>
          </li>
          <li>
            <Link to="/about">About</Link>
          </li>
        </ul>
      </nav>
      <div className="theme-toggle">
        <button onClick={toggleTheme}>
          Switch to {theme === 'light' ? 'Dark' : 'Light'} Mode
        </button>
      </div>
    </header>
  );
}

export default Header; 