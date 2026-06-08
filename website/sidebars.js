// @ts-check
// AETHON handbook — explicit sidebar so the reading order is curated like a book.

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  handbook: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/installation',
        'getting-started/configuration',
        'getting-started/model-backends',
        'getting-started/docker',
      ],
    },
    {
      type: 'category',
      label: 'Usage Guide',
      items: [
        'guides/cli',
        'guides/webchat',
        'guides/dashboard',
        'guides/messaging-bots',
        'guides/webhooks',
        'guides/scheduler',
      ],
    },
    {
      type: 'category',
      label: 'Core Concepts',
      items: [
        'concepts/workspace',
        'concepts/memory',
        'concepts/multi-agent',
        'concepts/sops',
        'concepts/tools',
        'concepts/capabilities',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/cli',
        'reference/configuration',
        'reference/api',
        'reference/architecture',
      ],
    },
    {
      type: 'category',
      label: 'Operations',
      items: [
        'operations/security',
        'operations/troubleshooting',
        'operations/faq',
      ],
    },
    {
      type: 'category',
      label: 'Project',
      items: [
        'project/roadmap',
        'project/development',
        'project/license',
      ],
    },
  ],
};

export default sidebars;
