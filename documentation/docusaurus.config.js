// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const { themes } = require('prism-react-renderer');
const lightCodeTheme = themes.github;
const darkCodeTheme = themes.dracula;

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Django RLS',
  tagline: 'PostgreSQL Row Level Security for Django',
  favicon: 'img/favicon.svg',

  // Set the production url of your site here
  url: 'https://django-rls.com',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'kdpisda', // Usually your GitHub org/user name.
  projectName: 'django-rls', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        gtag: {
          trackingID: 'G-9JBJM92Q46',
          anonymizeIP: true,
        },
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          routeBasePath: 'docs',
          editUrl:
            'https://github.com/kdpisda/django-rls/tree/main/documentation/',
          lastVersion: '1.0.0',
          versions: {
            current: {
              label: 'Next',
              path: 'next',
            },
            '1.0.0': {
              label: '1.0',
              path: '1.0',
            },
            '0.4.1': {
              label: '0.4',
              path: '0.4',
              banner: 'unmaintained',
            },
          },
        },
        blog: false,
        sitemap: {
          lastmod: 'date',
          changefreq: 'weekly',
          priority: 0.5,
          ignorePatterns: ['/docs/next/**'],
          filename: 'sitemap.xml',
          createSitemapItems: async (params) => {
            const { defaultCreateSitemapItems, ...rest } = params;
            const items = await defaultCreateSitemapItems(rest);
            return items.map((item) => {
              if (item.url.includes('/docs/1.0/')) {
                return { ...item, priority: 0.8 };
              }
              if (item.url.includes('/docs/0.4/')) {
                return { ...item, priority: 0.3 };
              }
              return item;
            });
          },
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/docusaurus-social-card.jpg',
      navbar: {
        title: 'Django RLS',
        logo: {
          alt: 'Django RLS Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            type: 'docsVersionDropdown',
            position: 'right',
            dropdownActiveClassDisabled: true,
          },
          {
            href: 'https://forum.django-rls.com',
            label: 'Forum',
            position: 'right',
          },
          {
            href: 'https://github.com/kdpisda/django-rls',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'Introduction',
                to: '/docs/1.0/intro',
              },
              {
                label: 'Installation',
                to: '/docs/1.0/installation',
              },
              {
                label: 'Quick Start',
                to: '/docs/1.0/quick-start',
              },
              {
                label: 'API Reference',
                to: '/docs/1.0/api-reference',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/kdpisda/django-rls',
              },
              {
                label: 'Forum',
                href: 'https://forum.django-rls.com',
              },
              {
                label: 'Issues',
                href: 'https://github.com/kdpisda/django-rls/issues',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'PyPI Package',
                href: 'https://pypi.org/project/django-rls/',
              },
              {
                html: `
                  <a href="https://kdpisda.in" target="_blank" rel="dofollow" class="footer__link-item">
                    Created by Kuldeep Pisda
                  </a>
                `,
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Django RLS. Built with <a href="https://docusaurus.io" target="_blank" rel="noopener noreferrer">Docusaurus</a>. Created by <a href="https://kdpisda.in" target="_blank" rel="dofollow">Kuldeep Pisda</a>.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['python', 'bash'],
      },
    }),
};

module.exports = config;
