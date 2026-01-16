import React, { useEffect } from 'react';

function App() {
  useEffect(() => {
    // Redirect to the FastAPI-served frontend
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    if (backendUrl) {
      window.location.href = backendUrl;
    }
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f0f23',
      color: '#e2e8f0',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif'
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ 
          background: 'linear-gradient(135deg, #6366f1, #a855f7)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          fontSize: '2.5rem',
          marginBottom: '1rem'
        }}>
          ✨ WAN 2.2 Dream Studio
        </h1>
        <p>Redirecting to video generation studio...</p>
      </div>
    </div>
  );
}

export default App;
