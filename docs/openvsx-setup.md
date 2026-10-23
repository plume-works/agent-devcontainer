# Open VSX setup for `plume-works/vscode-expo-bridge`

Open VSX publishes in two phases:

- **Now:** publish with an access token, because trusted publishing can only be
  registered for an extension that already has a version.
- **After the first pre-release:** switch to trusted publishing, which uses the
  workflow's GitHub sign-in token, and revoke the access token.

Pin the CLI: `bunx ovsx@1.3.0 …`. This is the latest version as of
2026-10-23, and it will match the version pinned in the repo's `devDependencies`.

## Phase 1 — before the first pre-release (plan Task 21c)

### 1. Eclipse account

1. Register at https://accounts.eclipse.org/user/register.
2. Fill in the **GitHub Username** field with the same GitHub account you
   will use to sign in to open-vsx.org.

### 2. Open VSX account and Publisher Agreement

1. Go to https://open-vsx.org and sign in with GitHub.
2. Open your profile (avatar → **Profile**) and click **Log in with Eclipse**. Sign in
   with the account from step 1.
3. Click **Show Publisher Agreement**, read it, and agree.

### 3. Access token

1. In open-vsx.org, go to **Settings → Access Tokens → Generate New Token**.
2. Use the description `vscode-expo-bridge release (GitHub Actions)`.
3. Copy the value right away; it is never shown again.

### 4. Namespace

The namespace must match `publisher` in the three `package.json` files exactly,
including case: `plume-works`.

```bash
bunx ovsx@1.3.0 create-namespace plume-works -p <token>
```

Creating the namespace does not make you its verified owner. That comes in
Phase 2.

### 5. GitHub secret

1. Go to https://github.com/plume-works/vscode-expo-bridge/settings/environments.
2. Open **release**, then **Environment secrets → Add environment secret**.
3. Set **Name** to `OVSX_PAT` and **Value** to the token from step 3.

Store it on the `release` environment, not at the repository level, so that only
the approved publish job can read it.

## Phase 2 — after Task 23 has published the first pre-release (trusted publishing plan, Tasks 1–2)

### 6. Claim namespace ownership

1. Go to https://github.com/EclipseFdn/open-vsx.org/issues/new/choose, sign in to
   open-vsx.org first, and open a namespace-ownership claim for `plume-works`.
   Link https://github.com/plume-works as proof you control the publisher.
2. The claim is public. Wait until the Eclipse team grants it. Your namespace
   then shows as verified, and you can manage trusted publishers.

### 7. Register a trusted publisher for each extension

Each extension takes one registration, so do this three times: for
`vscode-expo-bridge`, `vscode-expo-bridge-host`, and
`vscode-expo-bridge-workspace`.

1. Go to https://open-vsx.org/user-settings/trusted-publishers.
2. Choose namespace `plume-works`, then the extension, then **GitHub Actions**.
3. Fill in the fields:
   - **Owner:** `plume-works`
   - **Repository:** `vscode-expo-bridge`
   - **Workflow filename:** `release.yml`
   - **Environment:** `release`

   The registration is not tied to a branch or tag. The `release` environment's
   tag-only rule and required reviewer are what restrict it.

If **GitHub Actions** is not offered as a provider, open-vsx.org has not enabled
trusted publishing. Tell Claude; the plan then keeps `OVSX_PAT`.

### 8. Workflow switch (trusted publishing plan, Task 3, done by Claude)

The publish job changes to run `ovsx publish --trusted-publishing` and stops
passing the token. A token always overrides trusted publishing, so leaving it in
the job would quietly keep the job on the token.

## Phase 3 — after a release has published through trusted publishing (trusted publishing plan, Task 5)

### 9. Retire the token

1. In open-vsx.org, go to **Settings → Access Tokens** and delete the token from step 3.
2. In GitHub, go to **release → Environment secrets** and delete `OVSX_PAT`.

## References

- Publishing: https://github.com/eclipse/openvsx/wiki/Publishing-Extensions
- Namespace ownership: https://github.com/eclipse/openvsx/wiki/Namespace-Access
- Trusted publishing: https://github.com/eclipse/openvsx/wiki/Trusted-Publishing
