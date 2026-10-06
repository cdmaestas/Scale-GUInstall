# Clean terminal installation overview — narration

Instructional reenactment with assumed prerequisites and explicit verification.

Generated from the matching JSON in `docs/walkthroughs/_build/sources/`. Edit that source, then rebuild.

Pace: 135 words/minute + 2 seconds per chapter. Total: 3:01.11.

## 0:00.00 — Clean terminal overview

This is a concise instructional reenactment of the installation sequence. It assumes the toolkit, SSH access, RPC bind, reserved protocol addresses, and S3 media are ready. Those prerequisites still need checking in a real environment. Here we focus on configuration, installation, deployment, and verification.

Source: `techzone-runbook-walkthrough-clean.cast` 0.6–21.45 seconds. Hold 21.56s.

## 0:21.56 — 1. Start the toolkit setup service

First, start the toolkit setup service on the installer node. Use the address assigned to that installer in your environment. Once the service is ready, the next steps define the nodes and storage that the toolkit will manage.

Source: `techzone-runbook-walkthrough-clean.cast` 21.45–32.66 seconds. Hold 18.89s.

## 0:40.45 — 2. Configure seven nodes

Add the seven nodes with their intended roles. Two storage servers provide NSDs, quorum, and management. A GUI node also provides administration and quorum. Two protocol nodes serve the protocols, and two nodes remain clients. Review the resulting configuration before continuing.

Source: `techzone-runbook-walkthrough-clean.cast` 32.66–56.51 seconds. Hold 20.22s.

## 1:00.67 — 3. Define NSDs and filesystem placement

Inspect the disks and define the NSDs. This layout places one disk from each server in the shared root and the remaining disks in the main filesystem. Failure groups distinguish the servers. Verify filesystem replication separately; the placement shown here is not itself evidence of mirroring.

Source: `techzone-runbook-walkthrough-clean.cast` 56.51–77.24 seconds. Hold 22.44s.

## 1:23.11 — 4. Precheck and install

Resolve the cluster settings before running the installation precheck. In the source example, callhome is disabled and the port range is set. Once the precheck passes, installation creates the cluster and its configured storage. The long-running output is summarized rather than replayed in full.

Source: `techzone-runbook-walkthrough-clean.cast` 77.24–103.93 seconds. Hold 21.56s.

## 1:44.67 — 5. Verify the installation

Run the installation postcheck as a separate verification step. It checks GPFS, the NSDs, performance monitoring, and the GUI. Reviewing those results gives a clearer basis for continuing than relying on the installation command’s completion alone.

Source: `techzone-runbook-walkthrough-clean.cast` 103.93–126.38 seconds. Hold 18.00s.

## 2:02.67 — 6. Configure and precheck the protocols

Now configure the protocol shared root, mountpoint, network interface, and reserved floating addresses. Enable NFS, SMB, and S3, then run the deployment precheck. Review each protocol’s result and address any missing prerequisites before starting the actual deployment.

Source: `techzone-runbook-walkthrough-clean.cast` 126.38–154.16 seconds. Hold 18.44s.

## 2:21.11 — 7. Deploy the services

Deployment installs and starts the selected protocol services. In this illustrated successful path, the filesystem, Cluster Export Services, NFS, SMB, S3, monitoring, and GUI all become active. Check both the task results and the final service health before considering this stage complete.

Source: `techzone-runbook-walkthrough-clean.cast` 154.16–177.01 seconds. Hold 20.67s.

## 2:41.78 — 8. Verify the final state

Finish with the deployment postcheck. It independently checks the components that deployment brought up. This overview shows the order and verification points; the current runbook supplies the prerequisite details and environment-specific commands needed to carry out a real installation.

Source: `techzone-runbook-walkthrough-clean.cast` 177.01–214.241 seconds. Hold 19.33s.
