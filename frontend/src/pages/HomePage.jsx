import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import Button from '../components/form/Button';

function HomePage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div>
      <h1>Home Page</h1>
      <p>Welcome to the ResearchAIde application!</p>
      
      <div className="mt-8">
        <Link to="/setup">
          <Button variant="primary" size="lg">Start New Research</Button>
        </Link>
      </div>

      <hr className="my-8"/>
      <h2>Theme Demo</h2>
      <p>Current theme: {theme}</p>
      <Button onClick={toggleTheme} variant="secondary" className="mt-2">
        Toggle Theme
      </Button>
    </div>
  );
}

export default HomePage; 