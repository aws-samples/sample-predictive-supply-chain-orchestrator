/**
 * Backend connection status indicator.
 * Shows whether frontend is connected to real backend or using fallback data.
 */

import { useEffect, useState } from 'react';
import { checkHealth } from '../services/api';
import { useAuth } from '../auth/CognitoAuth';

interface BackendStatusProps {
  className?: string;
  compact?: boolean;
}

export default function BackendStatus({ className = '', compact = false }: BackendStatusProps) {
  const [status, setStatus] = useState<'checking' | 'connected' | 'fallback'>('checking');
  const [backendInfo, setBackendInfo] = useState<{ version: string; environment: string } | null>(null);
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    // Wait for auth to resolve before checking backend
    if (isLoading) return;

    async function checkBackend() {
      try {
        const health = await checkHealth();
        if (health && health.status === 'healthy') {
          setStatus('connected');
          setBackendInfo({
            version: health.version,
            environment: health.environment,
          });
          // console.log('✅ Backend connected:', health);
        } else {
          setStatus('fallback');
          // console.log('📦 Using fallback data');
        }
      } catch (error) {
        setStatus('fallback');
        // console.log('📦 Backend unavailable, using fallback data');
      }
    }

    checkBackend();

    // Check every 30 seconds
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, isLoading]);

  if (compact) {
    const dotColor = status === 'connected' ? '#34d399' : status === 'fallback' ? '#fbbf24' : 'rgba(255,255,255,0.4)'
    return (
      <div className={`backend-status ${className}`} style={{ display: 'flex', justifyContent: 'center' }} title={status === 'connected' ? `Backend Connected v${backendInfo?.version}` : status === 'fallback' ? 'Using Demo Data' : 'Checking...'}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor, display: 'block' }} />
      </div>
    )
  }

  return (
    <div className={`backend-status ${className}`}>
      {status === 'checking' && (
        <div className="status-badge status-checking">
          <span className="status-dot"></span>
          <span>Checking backend...</span>
        </div>
      )}
      
      {status === 'connected' && (
        <div className="status-badge status-connected">
          <span className="status-dot"></span>
          <span>
            Backend Connected
            {backendInfo && (
              <span className="status-details">
                {' '}v{backendInfo.version} ({backendInfo.environment})
              </span>
            )}
          </span>
        </div>
      )}
      
      {status === 'fallback' && (
        <div className="status-badge status-fallback">
          <span className="status-dot"></span>
          <span>Using Demo Data (Backend Offline)</span>
        </div>
      )}
    </div>
  );
}
