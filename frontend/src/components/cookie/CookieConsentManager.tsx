import React, { useEffect, useState } from 'react';
import {
  hasConsented,
  acceptAll,
  rejectAll,
  saveCustomConsent,
  getConsent,
  loadAnalyticsScript,
} from '../../lib/cookieConsent';
import CookieBanner from './CookieBanner';
import CookiePreferencesModal from './CookiePreferencesModal';
import CookieFloatingButton from './CookieFloatingButton';

type ManagerState = 'hidden' | 'banner' | 'floating';

export default function CookieConsentManager() {
  const [managerState, setManagerState] = useState<ManagerState>('hidden');
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (hasConsented()) {
      setManagerState('floating');
      loadAnalyticsScript();
    } else {
      setManagerState('banner');
    }
  }, []);

  const handleAcceptAll = () => {
    acceptAll();
    setManagerState('floating');
  };

  const handleReject = () => {
    rejectAll();
    setManagerState('floating');
  };

  const handleDismiss = () => {
    // Dismiss equivale a mantenere solo le impostazioni predefinite (necessari)
    const current = getConsent();
    saveCustomConsent({
      preferences: current.preferences || false,
      analytics: false,
      marketing: false,
    });
    setManagerState('floating');
  };

  return (
    <>
      {managerState === 'banner' && (
        <CookieBanner
          onAcceptAll={handleAcceptAll}
          onRejectNonEssential={handleReject}
          onCustomize={() => setShowModal(true)}
          onDismiss={handleDismiss}
        />
      )}

      {managerState === 'floating' && (
        <CookieFloatingButton onClick={() => setShowModal(true)} />
      )}

      <CookiePreferencesModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          if (!hasConsented()) {
            // Se l'utente chiude senza aver mai dato consenso, torna al banner
            setManagerState('banner');
          }
        }}
      />
    </>
  );
}
