# CES and NFS: from failed health checks to confirmation — narration

A condensed two-environment historical troubleshooting case.

Generated from the matching JSON in `recordings/sources/`. Edit that source, then rebuild.

Pace: 135 words/minute + 2 seconds per chapter. Total: 2:52.90.

## 0:00.00 — Why CES and NFS stayed inactive

This case follows a failed protocol deployment through diagnosis and confirmation in a fresh environment. It is an edited historical account. The successful run at the end covers NFS and SMB; it is separate from the three-protocol installation shown elsewhere.

Source: `techzone-runbook-walkthrough-2.cast` 0.6–30.25 seconds. Hold 19.78s.

## 0:19.78 — 1. Task success was not service health

The deployment tasks complete, but the service checks tell a different story. SMB is active while CES and NFS are not. The distinction matters: a clean task recap does not establish that every service is usable. The investigation follows the failing health checks.

Source: `techzone-runbook-walkthrough-2.cast` 30.25–52.66 seconds. Hold 21.11s.

## 0:40.89 — 2. Address assignment remains blocked

The addresses remain unassigned in this run. A manual assignment is refused, and suspending and resuming the nodes clears the failure flag only briefly. That points away from treating the flag itself as the cause. Something is continuing to make the protocol nodes unhealthy.

Source: `techzone-runbook-walkthrough-2.cast` 52.66–105.41 seconds. Hold 21.56s.

## 1:02.45 — 3. Inspect the services

Direct service checks reveal a masked RPC bind service and socket, alongside inactive NFS-Ganesha. Masking prevents the dependency from starting normally. This is the concrete fault found in the session. The next step is to check the same condition in a fresh environment.

Source: `techzone-runbook-walkthrough-2.cast` 105.41–151.84 seconds. Hold 21.11s.

## 1:23.56 — 4. Confirm and fix in a fresh environment

The fresh environment has the same masked service and socket. They are unmasked, enabled, and started before installation. Both protocol nodes are checked for active status. This preserves the important distinction between identifying a cause in one environment and confirming the correction in another.

Source: `techzone-runbook-walkthrough-2.cast` 151.84–187.06 seconds. Hold 21.56s.

## 1:45.12 — 5. Install, then verify directly

The repeated setup and installation steps are summarized here. Near the end, the log stream loses visibility, so the operator checks the cluster directly. The cluster exists, all seven nodes are active, and the filesystems are present. Lost output is not treated as proof of failed work.

Source: `techzone-runbook-walkthrough-2.cast` 187.06–268.61 seconds. Hold 22.89s.

## 2:08.01 — 6. Prepare protocol deployment

Protocol configuration uses the environment’s reserved CES addresses. The historical recording also showed a ping timeout, but that alone does not establish an unused address. Confirm allocation before use. With the shared root, interface, and pool configured, NFS and SMB are enabled and the deployment precheck passes.

Source: `techzone-runbook-walkthrough-2.cast` 268.61–296.97 seconds. Hold 22.89s.

## 2:30.90 — 7. Confirm the new deployment

In the new environment, deployment completes in about twelve and a half minutes. CES, NFS, SMB, the filesystem, monitoring, and the GUI are active. That result supports the correction in this case. It does not make service masking the explanation for every future NFS failure.

Source: `techzone-runbook-walkthrough-2.cast` 296.97–334.523 seconds. Hold 22.00s.
