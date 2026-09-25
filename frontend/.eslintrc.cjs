module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "prettier",
  ],
  ignorePatterns: ["dist", ".eslintrc.cjs", "node_modules"],
  parser: "@typescript-eslint/parser",
  plugins: ["react-refresh"],
  rules: {
    "react-refresh/only-export-components": [
      "warn",
      {
        allowConstantExport: true,
        // Non-component exports that belong next to their components.
        allowExportNames: ["toast", "sonner", "useToast", "badgeVariants", "buttonVariants"],
      },
    ],
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/consistent-type-imports": "off",
    "no-console": ["warn", { allow: ["warn", "error"] }],
  },
};
