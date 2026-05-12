import React from 'react';

interface ExportActionsProps {
  reportId: string;
}

export default function ExportActions({ reportId }: ExportActionsProps) {
  const actions = [
    {
      label: 'PDF',
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      ),
      href: `/api/audit/pdf?id=${reportId}`,
    },
    {
      label: 'JSON',
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      ),
      href: `/api/audit?id=${reportId}&format=json`,
    },
    {
      label: 'Copy',
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      ),
      onClick: () => {
        navigator.clipboard.writeText(`${window.location.origin}/report/${reportId}`);
      },
    },
  ];

  return (
    <div className="flex flex-col gap-1.5">
      {actions.map((action) =>
        action.href ? (
          <a
            key={action.label}
            href={action.href}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-border bg-bg-base text-xs font-medium text-text-secondary hover:text-text-primary hover:border-accent-teal/30 hover:bg-bg-subtle/50 transition-colors"
            target={action.href.startsWith('http') ? '_blank' : undefined}
            rel={action.href.startsWith('http') ? 'noopener' : undefined}
          >
            {action.icon}
            {action.label}
          </a>
        ) : (
          <button
            key={action.label}
            onClick={action.onClick}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-border bg-bg-base text-xs font-medium text-text-secondary hover:text-text-primary hover:border-accent-teal/30 hover:bg-bg-subtle/50 transition-colors"
          >
            {action.icon}
            {action.label}
          </button>
        )
      )}
    </div>
  );
}
