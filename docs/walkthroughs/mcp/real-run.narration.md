# MCP walkthrough: a real installation driven in plain language — narration

The scale-guinstall MCP calls made during one real installation on 2026-10-06, copied from the session transcripts; the operator's own words are verbatim. Playback pacing is generated.

Generated from the matching JSON in `docs/walkthroughs/_build/sources/`. Edit that source, then rebuild.

Pace: 135 words/minute + 2 seconds per chapter. Total: 5:10.46.

## 0:00.00 — A real MCP run, 2026-10-06

This is the same installation as the command-line and GUI walkthroughs, seen from the MCP side. Every call you see was made by Claude Code against the scale-guinstall MCP server, copied from the session transcript, with the results shortened. Lines marked USER are the operator's own words, verbatim. The agent's replies and reasoning are not shown, and the playback pacing is generated.

Source: capture `2026-10-06-mcp-run`, phases . Hold 29.56s.

## 0:29.56 — 1. Is the environment ready?

The operator said the new environment, tunnel and server were up. The agent checked: the backend answers ping, the toolkit is version 6.0.1.1, ansible-core 2.14.18 is compatible, the installer's address is 10.249.129.192, and no operation is running.

Source: capture `2026-10-06-mcp-run`, phases ready. Hold 18.44s.

## 0:48.00 — 2. Look at the disks

Next the agent listed the block devices on both storage servers. Each has ten devices and three free 100 gigabyte disks: vdd, vde and vdf. Those become the NSDs.

Source: capture `2026-10-06-mcp-run`, phases disks. Hold 14.89s.

## 1:02.89 — 3. Start the installation service

Setup ran first as a dry run, which only validates and prints the command, and then for real. Operations return as soon as they start, so the agent polls check_operation; setup finished in two and a half seconds.

Source: capture `2026-10-06-mcp-run`, phases setup. Hold 18.89s.

## 1:21.78 — 4. Define the seven nodes

One call defines all seven nodes and their roles; the backend turns it into a delete and an add per node. While it runs, the agent polls spectrumscale_running about every two seconds, because the toolkit allows only one command at a time. It finished in thirty-four seconds.

Source: capture `2026-10-06-mcp-run`, phases nodes. Hold 22.89s.

## 1:44.67 — 5. Read the nodes back

Reading the node list back shows the toolkit expanded each short name to its full host name and kept the roles exactly as requested.

Source: capture `2026-10-06-mcp-run`, phases nodes-readback. Hold 12.67s.

## 1:57.34 — 6. Define the storage

One call adds all six NSDs: the first two disks on each server for data and metadata, the third for data only in a pool named data, with failure groups one and two. The agent then listed them back, six in all.

Source: capture `2026-10-06-mcp-run`, phases nsds. Hold 20.67s.

## 2:18.01 — 7. Call home and cluster settings

Call home is disabled, and the cluster settings set the ephemeral port range to 60000 through 61000. The results are the commands the backend ran.

Source: capture `2026-10-06-mcp-run`, phases settings. Hold 13.11s.

## 2:31.12 — 8. The protocols were applied in the GUI

One step in this run did not go through MCP. The protocols were configured and enabled from the GUI's Apply Protocols panel, while the screenshots for the GUI walkthrough were being taken.

Source: capture `2026-10-06-mcp-run`, phases . Hold 16.22s.

## 2:47.34 — 9. Precheck and install

The install precheck ran, and then the operator said go ahead with install. The install takes about twenty-five minutes, so the agent checked in only now and then. When it asked for the result, the tool returned an error: the output was over a hundred and twenty thousand characters, too big for one result. The output had been saved to a file, which the agent read from there. That is a limit of the tool, not a failure of the install.

Source: capture `2026-10-06-mcp-run`, phases precheck-install, install. Hold 38.00s.

## 3:25.34 — 10. Check the install

The install postcheck ran next. Its result is in the command-line walkthrough, which shows every phase with its real timing.

Source: capture `2026-10-06-mcp-run`, phases postcheck-install. Hold 10.89s.

## 3:36.23 — 11. A new session picks up

The session was then cleared, and a new one started from a short hand-off note the operator pasted. Before doing anything, the agent checked that the backend still answered and that nothing was running. The operator's reply to the plan was go for it.

Source: capture `2026-10-06-mcp-run`, phases continue. Hold 21.56s.

## 3:57.79 — 12. A wrong argument, caught by a dry run

The first deploy precheck call was a dry run, and it failed: the toolkit argument must be the spectrumscale file, not the folder that holds it. Because it was a dry run, nothing was executed, and the corrected call validated. This is a real mistake, left in.

Source: capture `2026-10-06-mcp-run`, phases deploy-mistake. Hold 22.89s.

## 4:20.68 — 13. Precheck, deploy and postcheck

The deploy precheck took about two and a half minutes. The deploy ran for seventeen and a half minutes while the agent waited with SSH checks from the operator's Mac. Asking for its result hit the same size limit as the install, so the output was read from the saved file. The postcheck then finished in under ten seconds.

Source: capture `2026-10-06-mcp-run`, phases deploy. Hold 28.22s.

## 4:48.90 — 14. Read it back, then record

A last read of the node list shows seven nodes with S3, SMB and NFS enabled. The operator then asked to record, and the build. The verification commands were recorded live from the operator's Mac, and the walkthroughs were rebuilt from the real data.

Source: capture `2026-10-06-mcp-run`, phases readback-after, user-record. Hold 21.56s.
