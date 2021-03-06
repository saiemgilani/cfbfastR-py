/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */

 module.exports = {
  // By default, Docusaurus generates a sidebar from the docs folder structure
  tutorialSidebar: [{type: 'autogenerated', dirName: '.'}],
  docs: [
    { type: 'doc', id: 'intro' },
    {
      type: 'category',
      label: 'CFB',
      items: [
        'CFB/load_cfb_pbp',
        'CFB/load_cfb_rosters',
        'CFB/load_cfb_schedule',
        'CFB/load_cfb_team_info',
        'CFB/cfb_teams',
        'CFB/cfb_calendar',
      ],
    },
    {
      type: 'category',
      label: 'NFL',
      items: [
        'NFL/load_nfl_pbp',
        'NFL/load_nfl_player_stats',
        'NFL/load_nfl_rosters',
        'NFL/load_nfl_schedule',
        'NFL/nfl_teams',
      ],
    },
  ],
  // But you can create a sidebar manually
  /*
  tutorialSidebar: [
    {
      type: 'category',
      label: 'Tutorial',
      items: ['hello'],
    },
  ],
   */
};
