import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Sentinela do Fogo',
  tagline: 'Wildfire monitoring and early warning for Brazil',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  // GitHub Pages (works for public repos, or private repos on paid plans).
  url: 'https://ettorecsenatore.github.io',
  baseUrl: '/sentinela-fogo/',
  organizationName: 'EttoreCSenatore',
  projectName: 'sentinela-fogo',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'pt-BR'],
    localeConfigs: {
      en: {label: 'English', htmlLang: 'en'},
      'pt-BR': {label: 'Português (Brasil)', htmlLang: 'pt-BR'},
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/', // docs-only site
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/EttoreCSenatore/sentinela-fogo/tree/main/website/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Sentinela do Fogo',
      logo: {
        alt: 'Sentinela do Fogo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Documentation',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
        {
          href: 'https://github.com/EttoreCSenatore/sentinela-fogo',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Data',
          items: [
            {label: 'INPE BDQueimadas', href: 'https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/'},
            {label: 'Open-Meteo', href: 'https://open-meteo.com/'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'GitHub', href: 'https://github.com/EttoreCSenatore/sentinela-fogo'},
          ],
        },
      ],
      copyright: `Sentinela do Fogo · ${new Date().getFullYear()}`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'cpp'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
