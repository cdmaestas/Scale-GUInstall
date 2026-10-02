# MCP installation and diagnostic repair — narration

An edited historical installation followed by its diagnostic debugging epilogue.

Generated from the matching JSON in `recordings/sources/`. Edit that source, then rebuild.

Pace: 135 words/minute + 2 seconds per chapter. Total: 6:46.67.

## 0:00.00 — A cluster install, then a diagnostic fix

This is an edited account of one cluster installation and the debugging session that followed it. The calls and results come from the project’s capture record. Some operator requests are reconstructed.

Source: `mcp-nlp-live-install.cast` 0–24.8 seconds. Hold 15.78s.

## 0:15.78 — 1. Check the installer

We start by checking the installer. The backend is reachable, the toolkit is present, and no other operation is running. The agent checks Ansible, locale, and the existing configuration.

Source: `mcp-nlp-live-install.cast` 24.8–46.8 seconds. Hold 14.89s.

## 0:30.67 — 2. Inspect nodes and disks

Next, the agent inspects the machines and their disks. Each storage server has three unused hundred-gigabyte disks. A connection-test tool reports an error, but disk discovery reaches the same nodes successfully. The installation proceeds using that working path; the misleading diagnostic is investigated afterward.

Source: `mcp-nlp-live-install.cast` 46.8–76.8 seconds. Hold 21.56s.

## 0:52.23 — 3. Read the environment details

The operator supplies the hosts file and confirms that S3 media is present. The agent identifies the reserved protocol addresses and their network interface, separate from the nodes’ own addresses.

Source: `mcp-nlp-live-install.cast` 76.8–102 seconds. Hold 15.33s.

## 1:07.56 — 4. Start the toolkit service

The toolkit setup begins with a dry run, so the operator can review the intended action before execution. The agent then starts the setup service on the bastion installer. The recorded result is successful, with the package distribution service ready for the remaining configuration.

Source: `mcp-nlp-live-install.cast` 102–116.4 seconds. Hold 21.56s.

## 1:29.12 — 5. Assign the seven node roles

Now the seven nodes receive their roles. The two storage servers also provide quorum and management. The GUI node provides administration and quorum, while two protocol nodes serve clients. The agent reviews the dry run and confirms that all seven nodes appear in the configuration.

Source: `mcp-nlp-live-install.cast` 116.4–142 seconds. Hold 22.00s.

## 1:51.12 — 6. Define the storage

The storage request becomes six NSD definitions. One disk on each server is assigned to the protocol shared root, and the other disks to the main filesystem. Separate failure groups describe placement. Verify replication separately before claiming mirroring.

Source: `mcp-nlp-live-install.cast` 142–164.4 seconds. Hold 18.89s.

## 2:10.01 — 7. Recover from configuration errors

Two configuration mistakes are left visible in this account. The toolkit rejects a profile spelling and an unsupported monitoring argument. The agent reads those errors, removes the arguments, and retries successfully. The unsupported parameter has since been removed from the MCP interface; this is historical recovery, not current usage.

Source: `mcp-nlp-live-install.cast` 164.4–194.4 seconds. Hold 23.78s.

## 2:33.79 — 8. Configure the protocols

Protocol configuration uses the web interface’s backend. One request sets the shared root, mountpoint, interface, and floating addresses. A second enables NFS, SMB, and S3. Both succeed. We’re showing a summary of those requests here; the separate GUI tour shows the interface itself.

Source: `mcp-nlp-live-install.cast` 194.4–215.6 seconds. Hold 21.11s.

## 2:54.90 — 9. Install and verify

The installation precheck passes, and the installation takes about twenty-six minutes in the recorded run. The agent examines the log and completion status. A separate postcheck confirms GPFS, storage, monitoring, and the GUI. The protocol precheck then passes before deployment begins.

Source: `mcp-nlp-live-install.cast` 215.6–256.4 seconds. Hold 20.22s.

## 3:15.12 — 10. Deploy and check the outcome

Deployment takes about seventeen and a half minutes. One log line says async failed, so the agent checks its context rather than judging the whole run from that line. The final recap reports no failed or unreachable nodes, and the service checks confirm the intended components are active.

Source: `mcp-nlp-live-install.cast` 256.4–280 seconds. Hold 23.33s.

## 3:38.45 — 11. Confirm, then investigate

A final postcheck independently confirms the deployment. All services are running. Only now do we turn to the earlier connection-test problem. Keeping this order matters: the debugging evidence that follows comes from an installed, active cluster, not from the empty machines at the beginning.

Source: `mcp-nlp-live-install.cast` 280–287.2 seconds. Hold 21.56s.

## 4:00.01 — 12. Reproduce the misleading error

The operator asks for the connection test to be fixed. The agent reproduces the error and compares it with the tool that already works. Because the cluster is now active, the investigation can separate a real access problem from an inaccurate diagnosis by the tool.

Source: `mcp-nlp-troubleshooting.cast` 21.6–45.6 seconds. Hold 22.00s.

## 4:22.01 — 13. Compare the tools

Reading the code reveals two differences. The working tool lets SSH choose its configured user and port. The old connection test overrides both. It also treats any failure of the remote GPFS command as an SSH failure.

Source: `mcp-nlp-troubleshooting.cast` 45.6–67.2 seconds. Hold 18.44s.

## 4:40.45 — 14. Check the operator’s evidence

The operator supplies a successful manual check. Its output shows all seven nodes active, and the SSH message identifies port twenty-two twenty-three. That explains why forcing port twenty-two is wrong for this environment.

Source: `mcp-nlp-troubleshooting.cast` 67.2–87.2 seconds. Hold 16.67s.

## 4:57.12 — 15. Separate two kinds of failure

With the correct port, the check works. With a different user, the remote GPFS command reports permission denied, yet the old tool still calls it an SSH failure. That second experiment confirms the classification bug: reaching a host and successfully running a privileged command are different checks.

Source: `mcp-nlp-troubleshooting.cast` 87.2–113.2 seconds. Hold 22.89s.

## 5:20.01 — 16. Fix the diagnostic

The fix makes user and port optional, allowing the installer’s SSH configuration to supply them. It checks reachability first and GPFS state second. A failing GPFS command can now be reported accurately without claiming SSH failed.

Source: `mcp-nlp-troubleshooting.cast` 113.2–141.6 seconds. Hold 18.00s.

## 5:38.01 — 17. Explain the incomplete redeploy

After the backend is redeployed, the new reachability step appears, but the request still carries the old user and port defaults. Explicitly clearing those values makes the check work. This narrows the remaining problem to the tool definition loaded by the MCP client, rather than the updated backend.

Source: `mcp-nlp-troubleshooting.cast` 141.6–167.6 seconds. Hold 23.33s.

## 6:01.34 — 18. Restart and confirm

After the MCP server is restarted, a call with only the node name works. SSH uses the configured settings, and the GPFS check reports the active cluster. The installation and the diagnostic repair are now both verified, with the client and backend using the same behavior.

Source: `mcp-nlp-troubleshooting.cast` 167.6–181.6 seconds. Hold 22.44s.

## 6:23.78 — Closing

The useful lesson is to verify outcomes at each boundary: installation, deployment, remote access, and tool behavior. This recording keeps the successful checks and the mistakes that explain the repair. The capture log preserves the provenance, while the current runbook remains the reference for a new installation.

Source: `mcp-nlp-troubleshooting.cast` 181.6–195.6 seconds. Hold 22.89s.
