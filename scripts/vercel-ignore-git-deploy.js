const gitTriggered = Boolean(process.env.VERCEL_GIT_PROVIDER);

if (gitTriggered) {
  console.log('Skipping direct Vercel Git deployment. Production deploys are released only after the GitHub Local Verification Gate succeeds.');
  process.exit(0);
}

console.log('Non-Git Vercel build detected; allowing CI-controlled deployment.');
process.exit(1);
