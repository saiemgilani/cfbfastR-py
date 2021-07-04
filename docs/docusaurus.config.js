const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').DocusaurusConfig} */
module.exports = {
  title: 'cfbfastR-py',
  tagline: "The SportsDataverse's Python Package for College Football Data.",
  url: 'https://cfbfastr-py.sportsdataverse.org',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',
  organizationName: 'sportsdataverse', // Usually your GitHub org/user name.
  projectName: 'docusaurus', // Usually your repo name.
  themeConfig: {
    hideableSidebar: true,
    sidebarCollapsible: false,
    colorMode: {
      defaultMode: 'light',
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
    image: 'img/cfbfastR-py-gh.png',
    navbar: {
      hideOnScroll: true,
      // title: 'cfbfastR-py',
      logo: {
        alt: 'cfbfastR Logo',
        src: 'img/logo.ico',
      },
      items: [
        {
          type: 'doc',
          docId: 'intro',
          position: 'left',
          label: 'Docs',
        },
        {
          label: 'News',
          to: 'CHANGELOG',
          position: 'left',
        },
        {
          label: 'SDV',
          position: 'left',
          items: [
            {
              to: 'https://sportsdataverse.org',
              label: 'SportsDataverse',
            },
            {
              label: 'Python Packages',
            },
            {
              label: 'hoopR-py',
              to: 'https://hoopR-py.sportsdataverse.org/',
            },
            {
              label: 'wehoop-py',
              to: 'https://wehoop-py.sportsdataverse.org/',
            },
            {
              label: 'R Packages',
            },
            {
              label: 'cfbfastR',
              to: 'https://saiemgilani.github.io/cfbfastR/',
            },
            {
              label: 'hoopR',
              to: 'https://saiemgilani.github.io/hoopR/',
            },
            {
              label: 'wehoop',
              to: 'https://saiemgilani.github.io/wehoop/',
            },
            {
              label: 'recruitR',
              to: 'https://saiemgilani.github.io/recruitR/',
            },
            {
              label: 'puntr',
              to: 'https://puntalytics.github.io/puntr/',
            },
            {
              label: 'gamezoneR',
              to: 'https://jacklich10.github.io/gamezoneR/',
            },
          ],
        },
        {
          href: 'https://github.com/saiemgilani/cfbfastR-py',
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
              label: 'Docs',
              to: '/docs/intro',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'Twitter',
              href: 'https://twitter.com/saiemgilani',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/saiemgilani/cfbfastR-py',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} <strong>cfbfastR-py</strong>, developed by <a href='https://twitter.com/saiemgilani'>Saiem Gilani</a>, part of the <a href='https://sportsdataverse.org'>SportsDataverse</a>.`,
    },
    prism: {
      theme: lightCodeTheme,
      darkTheme: darkCodeTheme,
    },
  },
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          // Please change this to your repo.
          editUrl:
            'https://github.com/saiemgilani/hoopR/edit/master/website/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
};
