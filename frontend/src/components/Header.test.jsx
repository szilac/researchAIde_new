import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '../context/ThemeContext'; // Adjust path as necessary
import Header from './Header';

describe('Header Component', () => {
  test('renders ResearchAIde logo text and navigation links', () => {
    render(
      <BrowserRouter>
        <ThemeProvider>
          <Header />
        </ThemeProvider>
      </BrowserRouter>
    );

    // Check for logo text
    expect(screen.getByText('ResearchAIde')).toBeInTheDocument();

    // Check for navigation links
    expect(screen.getByRole('link', { name: /home/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /about/i })).toBeInTheDocument();

    // Check for theme toggle button text (initial state is light theme)
    expect(screen.getByRole('button', { name: /switch to dark mode/i })).toBeInTheDocument();
  });

  // Add more tests here, e.g., for theme toggle functionality
  // test('theme toggle button works', async () => {
  //   const user = userEvent.setup();
  //   render(
  //     <BrowserRouter>
  //       <ThemeProvider>
  //         <Header />
  //       </ThemeProvider>
  //     </BrowserRouter>
  //   );
  //   const toggleButton = screen.getByRole('button', { name: /switch to dark mode/i });
  //   await user.click(toggleButton);
  //   expect(screen.getByRole('button', { name: /switch to light mode/i })).toBeInTheDocument();
  // });
}); 