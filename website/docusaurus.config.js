// @ts-check
// AETHON documentation site — Docusaurus config.
// Runs in Node.js — no client-side/browser APIs here.

import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'AETHON',
  tagline: 'Self-hosted, provider-agnostic personal AI assistant',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  // Production URL + base path for GitHub Pages (https://mertozbas.github.io/aethon/).
  url: 'https://mertozbas.github.io',
  baseUrl: '/aethon/',

  organizationName: 'mertozbas',
  projectName: 'aethon',
  trailingSlash: false,

  onBrokenLinks: 'warn',
  onBrokenAnchors: 'warn',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'tr'],
    localeConfigs: {
      en: {label: 'English'},
      tr: {label: 'Türkçe'},
    },
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/mertozbas/aethon/tree/main/website/',
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
        sitemap: {
          changefreq: 'weekly',
          priority: 0.5,
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/docusaurus-social-card.jpg',
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      docs: {
        sidebar: {
          hideable: true,
          autoCollapseCategories: true,
        },
      },
      navbar: {
        title: 'AETHON',
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'handbook',
            position: 'left',
            label: 'Handbook',
          },
          {
            type: 'localeDropdown',
            position: 'right',
          },
          {
            href: 'https://github.com/mertozbas/aethon',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Handbook',
            items: [
              {label: 'Introduction', to: '/docs/intro'},
              {label: 'Installation', to: '/docs/getting-started/installation'},
              {label: 'Configuration', to: '/docs/getting-started/configuration'},
              {label: 'Model Backends', to: '/docs/getting-started/model-backends'},
            ],
          },
          {
            title: 'Reference',
            items: [
              {label: 'CLI', to: '/docs/reference/cli'},
              {label: 'Configuration', to: '/docs/reference/configuration'},
              {label: 'HTTP API', to: '/docs/reference/api'},
              {label: 'Architecture', to: '/docs/reference/architecture'},
            ],
          },
          {
            title: 'Project',
            items: [
              {label: 'GitHub', href: 'https://github.com/mertozbas/aethon'},
              {label: 'PyPI', href: 'https://pypi.org/project/aethon-ai/'},
              {label: 'Roadmap', to: '/docs/project/roadmap'},
              {label: 'License', to: '/docs/project/license'},
            ],
          },
        ],
        copyright: `Built by Mert Özbaş · AETHON is source-available under PolyForm Noncommercial 1.0.0.`,
      },
      prism: {
        theme: prismThemes.oneLight,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'yaml', 'json', 'python', 'docker'],
      },
    }),
};

export default config;
