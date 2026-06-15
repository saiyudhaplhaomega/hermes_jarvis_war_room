import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // React 19's compiler-oriented rules are useful, but this dashboard
      // intentionally loads API state inside effects. Keep the signal visible
      // without making routine data-fetch effects block production builds.
      'react-hooks/set-state-in-effect': 'warn',
      // Context modules export both Provider and hook by design.
      'react-refresh/only-export-components': 'warn',
      // Existing dashboard/API payloads still have dynamic shapes in a few
      // places. Treat this as cleanup debt, not a release blocker.
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    files: ['src/**/*.test.{ts,tsx}', 'src/test/**/*.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
])
