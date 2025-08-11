/* eslint-env node */
module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/strict',
    'prettier',
  ],
  ignorePatterns: ['**/.eslintrc.cjs'],
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'off'
  },
};

