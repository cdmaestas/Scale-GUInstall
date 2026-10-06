# CLI walkthrough: a real installation, command by command, with real timing — narration

The spectrumscale commands the backend ran during one real installation on 2026-10-06, with lines and timestamps quoted from the toolkit's own logs. Playback pacing is generated; the +m:ss times on screen are real.

Generated from the matching JSON in `docs/walkthroughs/_build/sources/`. Edit that source, then rebuild.

Pace: 135 words/minute + 2 seconds per chapter. Total: 8:13.33.

## 0:00.00 — A real run, command by command

This is the command line behind one real installation. Each screen shows the spectrumscale commands the backend ran on the installer node, with lines quoted from the toolkit's own logs. Where you see a plus sign and a time, that is the real time from the toolkit's log. Nobody typed these here: they were issued through the MCP tools and the GUI. The playback pacing is generated, but the commands, output and log times are real.

Source: capture `2026-10-06-run`, phases . Hold 35.78s.

## 0:35.78 — 1. Start the installation service

First the toolkit installs its installation service on the installer node. The command is spectrumscale setup with the installer's address. It finished in under three seconds. The backend did not keep the output of this step in this run, so only the command and its timing are shown.

Source: capture `2026-10-06-run`, phases setup. Hold 23.33s.

## 0:59.11 — 2. Define the seven nodes

Next the seven nodes are defined, one node delete and one node add each. The FATAL line is expected on a first run, because the delete finds nothing to remove. The warning about hosts file ordering is also expected; the runbook notes both. The info lines show the roles each node receives.

Source: capture `2026-10-06-run`, phases node-config. Hold 25.11s.

## 1:24.22 — 3. Read back the node table

The node list shows the result. Two nodes are NSD, manager and quorum; the GUI node is admin, quorum and GUI; the two protocol nodes are managers and protocol nodes; the two clients have no roles. This listing was read after the protocols were applied, so its protocol block already shows S3, SMB and NFS enabled.

Source: capture `2026-10-06-run`, phases node-list. Hold 26.89s.

## 1:51.11 — 4. Define the storage

Six NSDs are defined from the three free disks on each storage server: one for the CES shared root filesystem and two for fs1, with failure groups one and two. Two of the six add commands are shown, and the table below is the toolkit's own listing. The dataOnly disks join a pool named data.

Source: capture `2026-10-06-run`, phases nsd-add, nsd-list. Hold 26.44s.

## 2:17.55 — 5. Call home and cluster settings

Call home is on by default, and without settings the precheck fails, so it is disabled here. The cluster settings set the ephemeral port range to 60000 through 61000 and leave performance monitoring on.

Source: capture `2026-10-06-run`, phases callhome, cluster-config. Hold 17.11s.

## 2:34.66 — 6. Configure and enable the protocols

The CES settings name the shared root filesystem, its mount point, the network interface and two export addresses. These two commands were run from the GUI's Apply Protocols panel, which prints the same command and output. The warning about CIDR notation only means the toolkit stays in legacy mode. Then NFS, SMB and S3 are enabled.

Source: capture `2026-10-06-run`, phases protocols. Hold 26.89s.

## 3:01.55 — 7. Precheck the install

The install precheck validates the configuration without changing anything. It reports warnings: the NSDs may not be load balanced, there is one GUI server, and each NSD has a single server. The runbook treats these as expected for a small lab with node-local disks. The network checks pass and every node reports failed equals zero. It took about a minute and a half.

Source: capture `2026-10-06-run`, phases precheck-install. Hold 30.00s.

## 3:31.55 — 8. Run the install

The install itself is one command and took about twenty-four and a half minutes; the toolkit reports twenty-four minutes thirty-two seconds. The times on screen are from the toolkit's log. The cluster is created about seven and a half minutes in, the NSDs and filesystems follow, and the recap shows failed equals zero on every host. The log also shows retry lines while the toolkit waits for the GPFS daemon on the first server and for the GUI service; the waits ended and the run continued. It finishes with seven GPFS nodes active.

Source: capture `2026-10-06-run`, phases install. Hold 43.33s.

## 4:14.88 — Install: where the time went

This is where the install time went, read from the log. The longest gaps between task lines are package work on the nodes and starting the GPFS daemons, which took a little over two minutes. Tasks run in parallel across nodes, so this is spacing in the log, not the cost on one node. One more thing the timestamps show: the retry lines are all stamped at the same instant, because the toolkit writes them when the task returns. They tell you retries happened, but not when.

Source: capture `2026-10-06-run`, phases install, install-slow-tasks. Hold 40.67s.

## 4:55.55 — 9. Check the install

The install postcheck verifies the result. GPFS is active on all nodes, the NSDs are active, performance monitoring and the GUI are active, and it ends with success and all services running. It also reports the licenses enabled on the cluster, which you should check against what you own.

Source: capture `2026-10-06-run`, phases postcheck-install. Hold 23.78s.

## 5:19.33 — 10. Precheck the deploy

The deploy precheck now covers the protocols. The NSDs are in a valid state, the protocol, S3, SMB and NFS prechecks all pass, and so does the network check between protocol nodes. This precheck took about two and a half minutes here.

Source: capture `2026-10-06-run`, phases precheck-deploy. Hold 20.67s.

## 5:40.00 — 11. Deploy the protocols

Deploy creates the filesystems and brings up Cluster Export Services with NFS, SMB and S3. It took about seventeen and a half minutes. One line in the log, four minutes forty-two seconds in, says ASYNC FAILED for a background Ansible job on the first server. The play carried on, every host in both recaps shows failed equals zero, and the postcheck passes. The log has no error text for that job, so the cause is still not known. The toolkit ends by reporting protocols installed and configured on two protocol nodes.

Source: capture `2026-10-06-run`, phases deploy. Hold 42.44s.

## 6:22.44 — Deploy: where the time went

The same view for deploy. Package installation dominates again: the performance monitoring and GUI packages, and the S3 packages, each take a minute or two. Configuring SMB took about forty-seven seconds. As before, this is spacing between task lines in the log.

Source: capture `2026-10-06-run`, phases deploy, deploy-slow-tasks. Hold 20.67s.

## 6:43.11 — 12. Check the deploy

The deploy postcheck confirms the filesystems were created, and that Cluster Export Services, S3, SMB and NFS are all active.

Source: capture `2026-10-06-run`, phases postcheck-deploy. Hold 10.89s.

## 6:54.00 — 13. Verify the export addresses

The last real check is outside the toolkit. The mmces command shows both export addresses assigned, one to each protocol node, and all three services running on both. An export address left unassigned is the failure the runbook warns about, and it did not happen here.

Source: capture `2026-10-06-run`, phases ces-verify. Hold 22.44s.

## 7:16.44 — 14. The SMB TIPS status

Health shows a TIPS status for SMB. The events say the SMB performance sensors are not configured, which affects performance statistics only. The service events below are healthy: the CTDB state is healthy and the SMB daemon is running. The runbook records this as expected and leaves the sensors alone. A later look, about fifty minutes after the deploy, showed those sensors active and SMB healthy with nothing changed, so the TIPS cleared by itself. The verification recording shows it.

Source: capture `2026-10-06-run`, phases mmhealth-smb. Hold 37.56s.

## 7:54.00 — What the run took

Altogether the operations listed took a little under forty-seven minutes, almost all of it the install and the deploy. Defining nodes and storage took seconds. The waiting between phases in the original session is not included in these timings.

Source: capture `2026-10-06-run`, phases setup, nsd-add, cluster-config, precheck-install, install, postcheck-install, precheck-deploy, deploy, postcheck-deploy. Hold 19.33s.
