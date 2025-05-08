import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import ResearchSetupPage from './pages/ResearchSetupPage';
import { useTheme } from './hooks/useTheme';
import './App.css';

function App() {
  const { theme } = useTheme();

  return (
    <div className={`app-container ${theme}`}>
      <Header />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/setup" element={<ResearchSetupPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
