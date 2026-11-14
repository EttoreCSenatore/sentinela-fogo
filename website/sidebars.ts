import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    'intro',
    'getting-started',
    {
      type: 'category',
      label: 'System',
      collapsed: false,
      items: ['architecture', 'risk-model', 'data-sources', 'pilot-sites', 'alerts'],
    },
    {
      type: 'category',
      label: 'Operations',
      items: ['deployment', 'hardware'],
    },
    {
      type: 'category',
      label: 'Project',
      items: ['roadmap', 'decisions/self-hosted-stack'],
    },
  ],
};

export default sidebars;
