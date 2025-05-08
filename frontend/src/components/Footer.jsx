import React from 'react';
import { useTheme } from '../hooks/useTheme';
import './Footer.css'; // We'll create this CSS file next

function Footer() {
  const { theme } = useTheme();
  const currentYear = new Date().getFullYear();

  return (
    <footer className={`app-footer ${theme}`}>
      <p>&copy; {currentYear} ResearchAIde. All rights reserved.</p>
      <p>
        <a href="/privacy-policy">Privacy Policy</a> | <a href="/terms-of-service">Terms of Service</a>
      </p>
    </footer>
  );
}

export default Footer; 