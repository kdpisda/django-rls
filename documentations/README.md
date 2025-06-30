# Django RLS Documentation

This directory contains the documentation source for Django RLS, built with [Docusaurus](https://docusaurus.io/).

## 🌐 Live Documentation

Visit [django-rls.com](https://django-rls.com) to view the live documentation.

## 🚀 Development

### Prerequisites

- Node.js 18.0 or higher
- npm 9.0 or higher

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# The site will be available at http://localhost:3000
```

### Building

```bash
# Build the static site
npm run build

# Test the production build locally
npm run serve
```

## 📁 Structure

```
documentations/
├── docs/               # Markdown documentation files
│   ├── intro.md       # Introduction
│   ├── installation.md # Installation guide
│   ├── quick-start.md  # Quick start guide
│   ├── guides/        # In-depth guides
│   ├── examples/      # Real-world examples
│   └── api-reference.md # API documentation
├── src/               # React components
│   ├── pages/        # Custom pages
│   └── components/   # Reusable components
├── static/           # Static assets
│   └── CNAME        # Custom domain configuration
└── docusaurus.config.js # Docusaurus configuration
```

## 🚢 Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

### Automatic Deployment

The GitHub Actions workflow (`.github/workflows/deploy-docs.yml`) handles:
- Detecting changes in the `documentations/` directory
- Calculating checksums to avoid unnecessary rebuilds
- Building and deploying to GitHub Pages
- Setting up the custom domain (django-rls.com)

### Manual Deployment

You can trigger a manual deployment:
1. Go to the [Actions tab](https://github.com/kdpisda/django-rls/actions)
2. Select "Deploy Documentation"
3. Click "Run workflow"

Or use the deployment script:
```bash
./scripts/deploy-docs.sh
```

## 🎨 Customization

### Theme Colors

Edit `src/css/custom.css` to customize the theme colors:

```css
:root {
  --ifm-color-primary: #2e8555;
  --ifm-color-primary-dark: #29784c;
  /* ... other color variables */
}
```

### Navigation

Edit `docusaurus.config.js` to modify:
- Navigation bar items
- Footer links
- Site metadata

### Sidebar

Edit `sidebars.js` to reorganize the documentation structure.

## 📝 Writing Documentation

### Creating New Pages

1. Add a new `.md` file in the appropriate directory under `docs/`
2. Add front matter:
   ```markdown
   ---
   sidebar_position: 1
   title: Your Page Title
   ---
   ```
3. Write your content using Markdown
4. The page will automatically appear in the sidebar

### Using MDX

You can use React components in documentation files by using `.mdx` extension:

```mdx
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
  <TabItem value="python" label="Python">
    ```python
    # Python code
    ```
  </TabItem>
  <TabItem value="shell" label="Shell">
    ```bash
    # Shell commands
    ```
  </TabItem>
</Tabs>
```

## 🐛 Troubleshooting

### Build Errors

If you encounter build errors:
1. Clear the cache: `npm run clear`
2. Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
3. Check for broken links in markdown files

### Deployment Issues

If deployment fails:
1. Check the [GitHub Actions logs](https://github.com/kdpisda/django-rls/actions)
2. Verify the CNAME file exists in `static/`
3. Ensure GitHub Pages is enabled in repository settings

## 📚 Resources

- [Docusaurus Documentation](https://docusaurus.io/docs)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Custom Domain Setup](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)