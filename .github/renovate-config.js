// Global (self-hosted) Renovate configuration, used by the
// .github/workflows/renovate.yml GitHub Action.
// Repository-level configuration is in renovate.json.
module.exports = {
  platform: "github",
  onboarding: false,
  requireConfig: "optional",
  branchPrefix: "renovate/",
};
